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

# Local
from __plugin import ECMPlugin
import __helper as ecm

class ECMApache(ECMPlugin):
    def cmd_apache_stats(self, *argv, **kwargs):
        """
        apache.stats[]
        """
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', '80')
        path = kwargs.get('path', '/server-status')

        status = {}
        res = ecm.get_url('%s:%s%s' % (host, port, path))
        for line in res.strip().split('\n'):
            key, value = line.split(': ')
            try:
                status[key] = float(value)
            except ValueError:
                status[key] = value

        return status

ECMApache().run()

