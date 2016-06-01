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

from agent import AGENT_VERSION
from message import AGENT_VERSION_PROTOCOL

import __helper as ecm
import platform

class ECMInfo():
    def __init(self):
        pass

    def system_info(self, *argv, **kwargs):
            """Syntax: system_info"""
            retval = {
                'os': str(platform.system()),
                'machine': str(platform.machine()),
                'uptime': self._boot_time(),
                'hostname': platform.node(),
                'public_ip': self._get_ip(),
                'agent_version': AGENT_VERSION,
                'agent_protocol': AGENT_VERSION_PROTOCOL,
                'sudo': int(ecm.check_sudo())
            }
            (retval['os_distrib'], retval['os_version']) = ecm.get_distribution()

            return retval

