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
from datetime import datetime

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
        data = {
            # 'loadavg': self._get_load(),
            'cpu': self._get_cpu(),
            'mem': self._get_mem(),
            # 'disk': self._get_disk(),
            # 'net': self._get_network(),
            # 'netstat': self._get_netstat(),
            'disk_io': self._get_disk_io(),
            # 'inodes' : self._get_inodes(),
            # 'cputimes': self._get_cpu_times(),
            # 'cpustats': self._get_cpu_stats(),
            # 'process': self._get_processes(),
            # 'swap': self._get_swap(),
            # 'user': self._get_users(),
            # 'docker_info': self.get_docker_info()
        }
        if data['cpu'] and data['mem']:
            self.exit(OK, data)

        self.exit(CRITICAL)

    def _get_mem(self):
        retval = {
            'measurement': 'memory',
            'tags': {
                'unit': 'GB'
            },
            'fields': {

            }
        }

        try:
            if hasattr(psutil, 'virtual_memory'):
                mem = psutil.virtual_memory()

                if hasattr(mem, 'active'):
                    retval['fields']['active'] = self.to_gb(mem.active)
                if hasattr(mem, 'inactive'):
                    retval['fields']['inactive'] = self.to_gb(mem.inactive)
                if hasattr(mem, 'buffers'):
                    retval['fields']['buffers'] = self.to_gb(mem.buffers)
                if hasattr(mem, 'cached'):
                    retval['fields']['cached'] = self.to_gb(mem.cached)
                if hasattr(mem, 'shared'):
                    retval['fields']['shared'] = self.to_gb(mem.shared)

            else:
                mem = psutil.phymem_usage()
                retval['fields']['cached'] = self.to_gb(psutil.cached_phymem())
                retval['fields']['buffers'] = self.to_gb(psutil.phymem_buffers())

                if not self.is_win():
                    try:
                        f = open('/proc/meminfo', 'r')
                        for line in f:
                            if line.startswith('Active:'):
                                retval['fields']['active'] = self.to_gb(
                                    int(line.split()[1]) * 1024)
                            if line.startswith('Inactive:'):
                                retval['fields']['inactive'] = self.to_gb(
                                    int(line.split()[1]) * 1024)
                            if line.startswith('Buffers:'):
                                retval['fields']['buffers'] = self.to_gb(
                                    int(line.split()[1]) * 1024)
                            if line.startswith('Cached:'):
                                retval['fields']['cached'] = self.to_gb(
                                    int(line.split()[1]) * 1024)
                            if line.startswith('Shared:'):
                                retval['fields']['shared'] = self.to_gb(
                                    int(line.split()[1]) * 1024)
                        f.close()

                    except:
                        pass

            retval['fields']['total'] = self.to_gb(mem.total)
            retval['fields']['used'] = self.to_gb(mem.used)
            retval['fields']['free'] = self.to_gb(mem.free)
            retval['fields']['percent'] = mem.percent

        except:
            pass

        return [retval]

    def _get_disk(self):
        retval = []

        try:
            for part in psutil.disk_partitions(all=False):
                # Ignore error on specific devices (CD-ROM)
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    tmp = {
                        'measurement': 'disk',
                        'tags': {
                            'unit': 'GB',
                            'mountpoint': part.mountpoint
                        },
                        'fields': {
                        }
                    }

                    if hasattr(part, 'device'):
                        tmp['tags']['device'] = part.device
                    if hasattr(usage, 'total'):
                        tmp['fields']['total'] = self.to_gb(usage.total)
                    if hasattr(usage, 'used'):
                        tmp['fields']['used'] = self.to_gb(usage.used)
                    if hasattr(usage, 'free'):
                        tmp['fields']['free'] = self.to_gb(usage.free)
                    if hasattr(usage, 'percent'):
                        tmp['fields']['percent'] = (
                            float(usage.total - usage.free) / float(usage.total)
                            ) * 100

                    retval.append(tmp)

                except:
                    pass
        except:
            pass

        return retval

    def _get_disk_io(self):
        retval = []

        try:
            disk_io = psutil.disk_io_counters(perdisk=True)
            for device, metric in disk_io.items():
                res = {
                    'measurement': 'disk_io',
                    'tags': {
                        'device': device
                    },
                    'fields': {}
                }
                raw = self._to_dict(metric)
                res['fields'] = self.counters(raw, 'disk_io'+str(device))
                retval.append(res)

        except:
            pass

        return retval

    def _get_cpu(self):
        retval = []
        try:
            data = psutil.cpu_percent(interval=CPU_INTERVAL, percpu=True)

            for i in range(len(data)):
                res = {
                    'measurement': 'cpu',
                    'fields': {
                        'percent': data[i]
                    },
                    'tags': {
                        'cpu': 'cpu'+str(i)
                    }
                }
                retval.append(res)
        except:
            pass

        return retval

    def _get_cpu_stats(self):
        try:
            retval = {
                'measurement': 'cpu_stats',
                'fields': {},
                'tags': {}
                }
            retval['fields'] = self.counters(self._to_dict(psutil.cpu_stats()), 'cpu_stats')
            return [retval]
        except Exception as exp:
            pass
        return []

    def _get_cpu_times(self):
        try:
            retval = {
                'measurement': 'cpu_times',
                'fields': {},
                'tags': {}
            }
            retval['fields'] = self.counters(
                self._to_dict(psutil.cpu_times(percpu=False)), 'cpu_times'
                )
            return [retval]
        except Exception as exp:
            pass
        return []

    def _get_network(self):
        retval = {}
        retval = self._get_network_from_psutil()
        if not retval:
            retval = self._get_network_from_file()
        return retval

    def _get_network_from_psutil(self):
        if psutil.version_info[:2] >= (1, 0, 0):
            from psutil import net_io_counters as network_io_counters
        else:
            from psutil import network_io_counters

        retval = []
        try:
            data = network_io_counters(pernic=True)

            for key in data.keys():
                res = {
                    'measurement': 'network',
                    'tags': {
                        'interface': key
                    },
                    'fields': {}
                }
                raw = self._to_dict(data[key])
                res['fields'] = self.counters(raw, 'network'+str(key))
                retval.append(res)
        except Exception:
            pass
        return retval

    def _get_network_from_file(self):
        retval = []

        if self.is_win():
            return retval
        try:
            f = open("/proc/net/dev", "r")
            lines = f.readlines()
            lines = lines[2:]
            for line in lines:
                colon = line.find(':')
                assert colon > 0, line
                name = line[:colon].strip()
                fields = line[colon+1:].strip().split()
                res = {
                    'measurement': 'network',
                    'tags': {
                        'interface': name
                    },
                    'fields': {}
                }

                data = {
                    'bytes_sent': fields[7],
                    'bytes_recv': fields[0],
                    'packets_sent': fields[8],
                    'packets_recv': fields[1],
                    'errin': fields[2],
                    'errout': fields[9],
                    'dropin': fields[3],
                    'dropout': fields[10]
                }
                res['fields'] = self.counters(data, 'network')
                retval.append(res)
            f.close()

        except:
            pass
        return retval

    def _get_inodes(self):
        if self.is_win():
            return []

        inode_list = []
        for part in psutil.disk_partitions(all=False):
            try:
                data = os.statvfs(part.mountpoint)
                iused = data.f_files - data.f_ffree
                iused_p = int(iused * 100 / data.f_files)
                res = {
                    'measurement': 'inodes',
                    'tags': {
                        'filesystem': part.device,
                        'mountpoint': part.mountpoint,
                    },
                    'fields': {
                        'Inodes': data.f_files,
                        'IUsed': iused,
                        'IFree': data.f_ffree,
                        'IUse%': iused_p,
                    }
                }
                inode_list.append(res)
            except:
                pass

        return inode_list

    def _get_netstat(self):
        try:
            # Only psutil > v2
            conns = []
            for conn in psutil.net_connections(kind='all'):
                if conn.status not in ('ESTABLISHED', 'NONE'):
                    continue
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
            res = {
                'measurement': 'processes',
                'tags': {
                    'username': username,
                    'status': status,
                    'name': p.dict['name'] or '',
                    'unit': 'MB'
                },
                'fields': {
                    'cpu_percent': p.dict['cpu_percent'],
                    'memory_percent': p.dict['memory_percent'],
                    'vms': self.to_mb(getattr(p.dict['memory_info'], 'vms', 0)),
                    'rss': self.to_mb(getattr(p.dict['memory_info'], 'rss', 0)),
                }
            }

            retval.append(res)
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
        try:
            # Only for psutil >= 2
            if hasattr(psutil, 'swap_memory'):
                swap = psutil.swap_memory()

            else:
                swap = psutil.virtmem_usage()

            retval = {
                'measurement': 'swap',
                'fields': {
                    'percent': swap.percent,
                    'used': self.to_gb(swap.used),
                    'total': self.to_gb(swap.total),
                    'free': self.to_gb(swap.free)
                },
                'tags': {
                    'unit': 'GB'
                }
            }
            return [retval]
        except:
            pass

        return []

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
            with open('/proc/stat', 'r') as statfile:
                for line in statfile:
                    if line.startswith('btime'):
                        return float(line.strip().split()[1])
        except:
            pass

        raise Exception("Cannot get uptime")

    @staticmethod
    def _boot_time_windows():
        try:
            from time import time
            import uptime
        except:
            return

        return int(time() - uptime.uptime())

    def _get_load(self):
        if not self.is_win():
            from os import getloadavg
            m1, m5, m15 = getloadavg()
            return [{
                'measurement': 'loadaverage',
                'fields': {
                    '1m': m1,
                    '5m': m5,
                    '15m': m15
                },
                'tags': {},
            }]

        return []

    @staticmethod
    def _to_dict(obj):
        retval = {}
        for name in dir(obj):
            if name == 'index':
                continue
            if name == 'count':
                continue
            if not name.startswith('_'):
                value = getattr(obj, name)
                if isinstance(value, int):
                    retval[name] = float(value)
                else:
                    retval[name] = value

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
            respj = resp.json()
        except:
            return []

        retval = []

        for container in respj:
            container_info = {}
            id = container['Id']
            try:
                container_url = "/containers/%s/json" % id
                stat = session.get(base + container_url)
                statj = stat.json()
                container_info['info'] = statj
            except:
                pass
            if container['Status'].startswith('Up'):
                try:
                    stat_url = "/containers/%s/stats?stream=0" % id
                    stat = session.get(base + stat_url)
                    statj = stat.json()
                    container_info['stat'] = statj
                except:
                    pass
            try:
                stdout_url = "/containers/%s/logs?stdout=1" % id
                stat = session.get(base + stdout_url)
                container_info['stdout'] = stat.text
            except:
                pass
            try:
                stderr_url = "/containers/%s/logs?stderr=1" % id
                stat = session.get(base + stderr_url)
                container_info['stderr'] = stat.test
            except:
                pass
            try:
                process_url = "/containers/%s/top" % id
                stat = session.get(base + process_url)
                statj = stat.json()
                container_info['process'] = statj
            except:
                pass
            retval.append(container_info)
        return retval


mplugin = BaseMPlugin()
mplugin.run()

