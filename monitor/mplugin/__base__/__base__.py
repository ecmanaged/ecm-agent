#!/usr/bin/env python

# -*- coding:utf-8 -*-

# Copyright (C) 2012 Juan Carlos Moreno <juancarlos.moreno at ecmanaged.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# Base monitor for agent please do not modify it

import psutil
import os
import sys

from os import getpid
from time import time, sleep

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'plugins'))

from __mplugin import MPlugin
from __mplugin import OK, CRITICAL

CPU_INTERVAL = 5
TIMEOUT_DEFAULT = 55
VERSION = 1


class BaseMPlugin(MPlugin):
    def run(self):
        mytime = int(time())
        boottime = self._get_uptime()
        uptime = int(mytime - boottime)


        data = {
            'version': VERSION,
            'time': mytime,
            'loadavg': self._get_load(),
            'uptime': uptime,
            'boottime': boottime,
            'cpu': self._get_cpu(),
            'mem': self._get_mem(),
            'disk': self._get_disk(),
            'net': self._get_network(),
            'netstat': self._get_netstat(),
            'disk_io': self._get_disk_io(),
            'inodes' : self._get_inodes(),
            'cputimes': self._get_cpu_times(),
            'process': self._get_processes(),
            'swap': self._get_swap(),
            'user': self._get_users()
            'docker_info': self.get_docker_info()
        }
        
        if data['cpu'] and data['mem']:
            self.exit(OK, data)

        self.exit(CRITICAL)

    def _get_mem(self):
        retval = {}
        try:
            if hasattr(psutil, 'virtual_memory'):
                mem = psutil.virtual_memory()
                
                if hasattr(mem, 'active'):
                    retval['active'] = self.to_gb(mem.active)
                if hasattr(mem, 'inactive'):
                    retval['inactive'] = self.to_gb(mem.inactive)
                if hasattr(mem, 'buffers'):
                    retval['buffers'] = self.to_gb(mem.buffers)
                if hasattr(mem, 'cached'):
                    retval['cached'] = self.to_gb(mem.cached)
                if hasattr(mem, 'shared'):
                    retval['shared'] = self.to_gb(mem.shared)

            else:
                mem = psutil.phymem_usage()
                retval['cached'] = self.to_gb(psutil.cached_phymem())
                retval['buffers'] = self.to_gb(psutil.phymem_buffers())
                
                if not self.is_win():
                    try:
                        f = open('/proc/meminfo', 'r')
                        for line in f:
                            if line.startswith('Active:'):
                                retval['active'] = self.to_gb(int(line.split()[1]) * 1024)
                            if line.startswith('Inactive:'):
                                retval['inactive'] = self.to_gb(int(line.split()[1]) * 1024)
                            if line.startswith('Buffers:'):
                                retval['buffers'] = self.to_gb(int(line.split()[1]) * 1024)
                            if line.startswith('Cached:'):
                                retval['cached'] = self.to_gb(int(line.split()[1]) * 1024)
                            if line.startswith('Shared:'):
                                retval['shared'] = self.to_gb(int(line.split()[1]) * 1024)
                        f.close()
                        
                    except:
                        pass
                
            retval['total'] = self.to_gb(mem.total)
            retval['used'] = self.to_gb(mem.used)
            retval['free'] = self.to_gb(mem.free)
            retval['percent'] = mem.percent
            
        except:
            pass

        return retval

    def _get_disk(self):
        retval = {}

        try:
            for part in psutil.disk_partitions(all=False):
                # Ignore error on specific devices (CD-ROM)
                try:
                    tmp = {}
                    usage = psutil.disk_usage(part.mountpoint)
                    if hasattr(part, 'device'):
                        tmp['device'] = part.device
                    if hasattr(usage, 'total'):
                        tmp['total'] = self.to_gb(usage.total)
                    if hasattr(usage, 'used'):
                        tmp['used'] = self.to_gb(usage.used)
                    if hasattr(usage, 'free'):
                        tmp['free'] = self.to_gb(usage.free)
                    if hasattr(usage, 'percent'):
                        tmp['percent'] = (float(usage.total - usage.free) / float(usage.total)) * 100

                    retval[part.mountpoint] = tmp

                except:
                    pass

        except:
            pass

        return retval

    def _get_disk_io(self):
        retval = {}
        from os.path import basename

        try:
            device_names = []
            disk_part = psutil.disk_partitions(all=False)

            for part in disk_part:
                device_names.append(basename(part.device))

            disk_io = psutil.disk_io_counters(perdisk=True)
            res = {}

            for device in device_names:
                if not disk_io.get(device):
                    continue
                res[device] = disk_io[device]

            retval = self.counters(self._to_data(res), 'disk_io')
        except:
            pass
            
        return retval

    @staticmethod
    def _get_cpu():
        retval = {}

        try:
            data = psutil.cpu_percent(interval=CPU_INTERVAL, percpu=True)
            total = 0
            for cpu in data:
                total += cpu

            retval = {
                'percent': int(total / len(data)),
                'number': len(data),
                'cpus': data
            }

        except:
            pass

        return retval

    def _get_cpu_times(self):
        retval = {}

        try:
            retval = self.counters(self._to_dict(psutil.cpu_times(percpu=False)), 'cpu_times')
        except:
            pass

        return retval

    def _get_network(self):
        retval = {}

        try:
            data = self._to_data(psutil.network_io_counters(pernic=True))

            if not data.get('errin') and not self.is_win():
                # Get manualy errors
                try: 
                    f = open("/proc/net/dev", "r")
                    lines = f.readlines()
                    for line in lines[2:]:
                        colon = line.find(':')
                        assert colon > 0, line
                        name = line[:colon].strip()
                        fields = line[colon+1:].strip().split()
                        
                        # Do not set counter or gauge for this values
                        data[name]['errir'] = int(fields[2])
                        data[name]['errout'] = int(fields[10])
                    
                    f.close()

                except:
                    pass
                    
            retval = self.counters(data, 'network')
                    
        except:
            pass        

        return retval

    def _get_inodes(self):
        """
        runs df -i
        Filesystem               Inodes  IUsed   IFree IUse% Mounted on
        /dev/mapper/fedora-root 2436448 335632 2100816   14% /
        /dev/mapper/fedora-home 1310720  49938 1260782    4% /home

        and returns output as list of dictionaries

        [   {   'Filesystem': '/dev/mapper/fedora-root',
                'IFree': '2100817',
                'IUse%': '14%',
                'IUsed': '335631',
                'Inodes': '2436448',
                'Mounted on': '/'},
            {   'Filesystem': '/dev/mapper/fedora-home',
                'IFree': '1260404',
                'IUse%': '4%',
                'IUsed': '50316',
                'Inodes': '1310720',
                'Mounted on': '/home'}]
        """
        if self.is_win():
            return []

        from commands import getstatusoutput

        retcode, inodes = getstatusoutput('df -i')

        inodes = inodes.split()
        inode = inodes[7:]

        partitions_list = []

        for part in psutil.disk_partitions(all=False):
            partitions_list.append(part.mountpoint)

        inode_list = []
        i = 0

        while i < len(inode):
            try:
                if str(inode[i + 2]) == 'bindfs':
                    i += 6
                    continue

                if inode[i + 5] in partitions_list:
                    inode_list.append({'Filesystem': inode[i], 'Inodes': inode[i + 1], 'IUsed': inode[i + 2],
                                       'IFree': inode[i + 3], 'IUse%': inode[i + 4], 'Mounted on': inode[i + 5]})
            except Exception as e:
                pass
            i += 6

        return inode_list
                
    def _get_netstat(self):
        try:
            # Only psutil > v2
            conns = []
            for conn in psutil.net_connections(kind='all'):
                if conn.status not in ('ESTABLISHED','NONE'): continue
                conns.append(self._to_dict(conn))

            return conns
        except:
            return {}

    def _get_processes(self):
        processes = []

        # Ask CPU counters
        try:
            for p in psutil.process_iter():
                if psutil.version_info[:2] >= (2, 0):
                    p.as_dict(['cpu_percent'])

                else:
                    p.as_dict(['get_cpu_percent'])
        except:
            pass

        # Wait to get correct cpu data
        sleep(2)

        for p in psutil.process_iter():
            try:
                if psutil.version_info[:2] >= (2, 0):
                    p.dict = p.as_dict(['username', 'nice', 'memory_info',
                                        'memory_percent', 'cpu_percent',
                                        'name', 'status'])
                else:
                    p.dict = p.as_dict(['username', 'nice', 'get_memory_info',
                                        'get_memory_percent', 'get_cpu_percent',
                                        'name', 'status'])
                processes.append(p)

            except:
                pass

        return self._process_parser(processes)

    def _process_parser(self, processes):
        retval = []

        # Get CPU count
        cpu_count = 1
        data = psutil.cpu_percent(percpu=True)

        if data:
            cpu_count = len(data)
            
        skip_pids = [1, getpid()]

        for p in processes:
            if p.pid in skip_pids:
                continue
            
            # Translate
            if 'get_memory_info' in p.dict:
                p.dict['memory_info'] = p.dict['get_memory_info']
                
            if 'get_memory_percent' in p.dict:
                p.dict['memory_percent'] = p.dict['get_memory_percent']
                
            if 'get_cpu_percent' in p.dict:
                p.dict['cpu_percent'] = p.dict['get_cpu_percent']

            if p.dict['memory_percent'] is not None:
                p.dict['memory_percent'] = round(p.dict['memory_percent'], 1)
                
            else:
                p.dict['memory_percent'] = ''

            if not p.dict['cpu_percent']:
                p.dict['cpu_percent'] = 0

            else:
                p.dict['cpu_percent'] /= cpu_count

            username = ''
            if p.dict['username']:
                username = p.dict['username'][:8]

            status = str(p.dict['status'])

            retval.append((p.pid,
                           username,
                           self.to_mb(getattr(p.dict['memory_info'], 'vms', 0)),
                           self.to_mb(getattr(p.dict['memory_info'], 'rss', 0)),
                           p.dict['cpu_percent'],
                           p.dict['memory_percent'],
                           p.dict['name'] or '',
                           status
            ))
        return retval

    @staticmethod
    def _get_users():
        retval = {}
        try:
            tmp = psutil.users() if hasattr(psutil, 'users') else psutil.get_users()
            for session in tmp:
                # Count logged in users
                retval[session.name] = retval.get(session.name, 0) + 1

        except:
            pass

        return retval

    def _get_uptime(self):
        from sys import platform

        if platform.startswith("win32"):
            return self._boot_time_windows()

        return self._boot_time_linux()

    def _get_swap(self):
        retval = {}
        try:
            # Only for psutil >= 2
            if hasattr(psutil, 'swap_memory'):
                swap = psutil.swap_memory()
                
            else:     
                swap = psutil.virtmem_usage()
            
            retval = {
                'percent': swap.percent,
                'used': self.to_gb(swap.used),
                'total': self.to_gb(swap.total),
                'free': self.to_gb(swap.free)
            }
        except:
            pass

        return retval

    # Helper functions
    def _to_data(self, element):
        retval = {}
        for value in element:
            retval[value] = self._to_dict(element[value])

        return retval

    @staticmethod
    def _boot_time_linux():
        try:
            return psutil.boot_time()
        except:
            pass

        # Old psutil versions
        try:
            return psutil.BOOT_TIME
        except:
            pass

        # Get info from proc
        try:
            f = open('/proc/stat', 'r')
            for line in f:
                if line.startswith('btime'):
                    f.close()
                    return float(line.strip().split()[1])
            f.close()
            return 0
        except:
            pass

        raise Exception("Cannot get uptime")

    @staticmethod
    def _boot_time_windows():
        try:
            from time import time
            import uptime

            return int(time() - uptime.uptime())
        except:
            return

    def _get_load(self):
        if not self.is_win():
            from os import getloadavg
            m1, m5, m15 = getloadavg()
            return {
                '1m': m1,
                '5m': m5,
                '15m': m15
            }

        return 0

    @staticmethod
    def _to_dict(obj):
        retval = {}
        for name in dir(obj):
            if name == 'index':
                continue
            if name == 'count':
                continue
            if not name.startswith('_'):
                retval[name] = getattr(obj, name)

        return retval

    def get_docker_info(self):
        if self.is_win():
            return []

        try:
            import requests_unixsocket
            import json
        except:
            return []

        base = "http+unix://%2Fvar%2Frun%2Fdocker.sock"
        url = "/containers/json"

        session = requests_unixsocket.Session()
        try:
            resp = session.get(base + url)
        except:
            return []

        respj = resp.json()
        retval = []

        for container in respj:
            container_info = {}
            id = container['Id']
            container_url = "/containers/%s/json" % id
            try:
                stat = session.get(base + container_url)
                statj = stat.json()
                container_info['info'] = statj
            except:
                pass
            if container['Status'].startswith('Up'):
                stat_url = "/containers/%s/stats?stream=0" % id
                try:
                    stat = session.get(base + stat_url)
                    statj = stat.json()
                    container_info['stat'] = statj
                except:
                    pass
            stdout_url = "/containers/%s/logs?stdout=1" % id
            try:
                stat = session.get(base + stdout_url)
                container_info['stdout'] = stat.text
            except:
                pass
            stderr_url = "/containers/%s/logs?stderr=1" % id
            try:
                stat = session.get(base + stderr_url)
                container_info['stderr'] = stat.test
            except:
                pass
            process_url = "/containers/%s/top" % id
            try:
                stat = session.get(base + process_url)
                statj = stat.json()
                container_info['process'] = statj
            except:
                pass
            retval.append(container_info)
        return retval


mplugin = BaseMPlugin()
mplugin.run()
