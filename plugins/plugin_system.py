# -*- coding:utf-8 -*-

# Copyright (C) 2012 Juan Carlos Moreno <juancarlos.moreno at ecmanaged.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import sys
import os

_DEFAULT_CPU_INTERVAL = 0.5

# Local
from __plugin import ECMPlugin
from __helper import AGENT_VERSION
import __helper as ecm

root_dir = os.path.join(os.path.sep, 'opt','ecmanaged','ecagent')
if root_dir not in sys.path:
    sys.path.append(root_dir)

print sys.path

from ecagent.config import SMConfigObj

import psutil



class ECMSystem(ECMPlugin):
    def cmd_agent_ping(self, *argv, **kwargs):
        """ Is this agent available? """
        return True

    def cmd_set_info(self, *argv, **kwargs):
        """
        Set ECManaged facts and environment variables
        Syntax: set.info[metadata]
        """
        metadata = kwargs.get('metadata', None)
        metadata_stack = kwargs.get('metadata_stack', None)
        metadata_cloud = kwargs.get('metadata_cloud', None)
        metadata_platform = kwargs.get('metadata_platform', None)

        if not metadata:
            raise ecm.InvalidParameters(self.cmd_set_info.__doc__)

        # Write other metadata if available
        ecm.write_metadata_stack(metadata_b64=metadata_stack)
        ecm.write_metadata_cloud(metadata_b64=metadata_cloud)
        ecm.write_metadata_platform(metadata_b64=metadata_platform)

        if ecm.write_metadata(metadata_b64=metadata):
            return True

        raise Exception('Unable to write environment file')

    def cmd_system_info(self, *argv, **kwargs):
        """Syntax: system_info"""
        import platform

        config_file_temp = os.path.join(os.path.sep, 'opt','ecmanaged','ecagent', 'config', 'ecagent.cfg')
        config_temp = SMConfigObj(config_file_temp)

        retval = {
            'os': str(platform.system()),
            'machine': str(platform.machine()),
            'uptime': self._boot_time(),
            'hostname': platform.node(),
            'public_ip': self._get_ip(),
            'agent_version': AGENT_VERSION,
            'account_id': config_temp.get_stored_account_id(),
            'server_group_id': config_temp.get_stored_server_group_id()
        }
        (retval['os_distrib'], retval['os_version']) = ecm.get_distribution()

        return retval

    def _boot_time(self):
        """ Returns server boot time """
        if ecm.is_windows():
            return self._boot_time_windows()

        return self._boot_time_linux()

    @staticmethod
    def _boot_time_linux():
        # Old psutil versions
        try: return psutil.BOOT_TIME
        except: pass

        # psutil v2 versions
        try: return psutil.boot_time()
        except: pass

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
            return 0

    @staticmethod
    def _get_ip():
        import socket
        """ Create dummy socket to get address """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('app.ecmanaged.com', 0))
        return s.getsockname()[0]

    @staticmethod
    def aux_convert_bytes(n):
        if n == 0:
            return "0B"

        symbols = ('k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10
        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)


ECMSystem().run()