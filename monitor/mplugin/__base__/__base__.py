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

TIMEOUT_DEFAULT = 55
VERSION = 1

import sys

sys.path.append('../../../plugins')

from __mplugin import MPlugin
from __mplugin import OK, CRITICAL

import psutil

from os import getloadavg
from time import time


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
            'cputimes': self._get_cpu_times(),
            'process': self._get_processes(),
            'swap': self._get_swap(),
            'user': self._get_users()
        }
        
        if data['cpu'] and data['mem']:
            self.exit(OK, data)

        self.exit(CRITICAL)

    def _get_mem(self):
        retval = {}
        try:
            if hasattr(psutil, 'virtual_memory'):
                mem = psutil.virtual_memory()

            else:
                mem = psutil.phymem_usage()

            retval = {
                'total': self._to_gb(mem.total),
                'used': self._to_gb(mem.used),
                'free': self._to_gb(mem.free),
                'percent': mem.percent
            }

            # psutil v2
            if hasattr(mem, 'active'):
                retval['active'] = self._to_gb(mem.active)
            if hasattr(mem, 'inactive'):
                retval['inactive'] = self._to_gb(mem.inactive)
            if hasattr(mem, 'buffers'):
                retval['buffers'] = self._to_gb(mem.buffers)
            if hasattr(mem, 'cached'):
                retval['cached'] = self._to_gb(mem.cached)
            if hasattr(mem, 'shared'):
                retval['shared'] = self._to_gb(mem.shared)

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
                        tmp['total'] = self._to_gb(usage.total)
                    if hasattr(usage, 'used'):
                        tmp['used'] = self._to_gb(usage.used)
                    if hasattr(usage, 'free'):
                        tmp['free'] = self._to_gb(usage.free)
                    if hasattr(usage, 'percent'):
                        tmp['percent'] = usage.percent

                    retval[part.mountpoint] = tmp

                except:
                    pass

        except:
            pass

        return retval

    def _get_disk_io(self):
        return self._counters(self._to_data(psutil.disk_io_counters(perdisk=True)),'disk_io')

    def _get_cpu(self):
        retval = {}

        try:
            data = psutil.cpu_percent(interval=2, percpu=True)
            sum = 0
            for cpu in data:
                sum += cpu

            retval = {
                'percent': int(sum / len(data)),
                'number': len(data),
                'cpus': data
            }

        except:
            pass

        return retval

    def _get_cpu_times(self):
        retval = {}

        try:
            retval = self._counters(self._to_dict(psutil.cpu_times(percpu=False)),'cpu_times')
        except:
            pass

        return retval

    def _get_network(self):
        return self._counters(self._to_data(psutil.network_io_counters(pernic=True)),'network')
        
    def _get_netstat(self):
        try:
            return self._to_data(psutil.net_connections(kind='inet'))
        except:
            return {}

    def _get_processes(self):
        procs = []
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
                procs.append(p)

            except:
                pass

        return self._process_parser(procs)

    def _process_parser(self, procs):
        retval = []
        for p in procs:
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
                
            if p.dict['cpu_percent'] is None:
                p.dict['cpu_percent'] = ''

            username = ''
            if p.dict['username']:
                username = p.dict['username'][:8]

            retval.append((p.pid,
                           username,
                           self._to_mb(getattr(p.dict['memory_info'], 'vms', 0)),
                           self._to_mb(getattr(p.dict['memory_info'], 'rss', 0)),
                           p.dict['cpu_percent'],
                           p.dict['memory_percent'],
                           p.dict['name'] or '',
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
            swap = psutil.swap_memory()
            retval = (
                swap.percent,
                self._to_gb(swap.used),
                self._to_gb(swap.total)
            )
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
        # Old psutil versions
        try:
            return psutil.BOOT_TIME
        except:
            pass

        # psutil v2 versions
        try:
            return psutil.boot_time()
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

    @staticmethod
    def _get_load():
        m1, m5, m15 = getloadavg()
        return {
            '1m': m1,
            '5m': m5,
            '15m': m15
        }

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

mplugin = BaseMPlugin()
mplugin.run()

