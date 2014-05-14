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


from base64 import b64decode
from __ecmhaproxy import ECMHAConfig, ECMHASocket

HAPROXY_CONFIG = '/etc/haproxy/haproxy.cfg'
HAPROXY_INIT = '/etc/init.d/haproxy'

# Local
from __plugin import ECMPlugin
import __helper as ecm


class ECMHaproxy(ECMPlugin):
    def cmd_haproxy_config_get(self, *argv, **kwargs):
        """
        haproxy.config_get[]
        """
        f = open(HAPROXY_CONFIG, 'r')
        first_line = f.readline()
        f.close()

        if first_line.startswith('#'):
            json_config = first_line.split('#')[1].rstrip('\n')
            return json_config

        raise Exception("Unable to get config")

    def cmd_haproxy_config_set(self, *argv, **kwargs):
        """
        haproxy.config_set[config=base64_balancer_config]
        """
        config = kwargs.get('config', None)
        if not config:
            raise ecm.InvalidParameters(self.cmd_haproxy_config_set.__doc__)

        try:
            config = b64decode(config)
        except Exception:
            raise ecm.InvalidParameters('Invalid base64 configuration')

        ha_config = ECMHAConfig(config, as_json=True)
        if ha_config.valid():
            ha_config.write(HAPROXY_CONFIG)
            self._restart()
            return self.cmd_haproxy_config_get()
            
        else:
            raise Exception('Invalid configuration')

    def cmd_haproxy_status(self, *argv, **kwargs):
        """
        haproxy.status[]
        """
        status_array = {}
        ha = ECMHASocket()
        for line in ha.get_server_stats():
            status_array.setdefault(line['pxname'], {})[line['svname']] = line['status']
        return status_array

    def cmd_haproxy_stats(self, *argv, **kwargs):
        """
        haproxy.stats[]
        """
        json_array = {}
        return json_array

    @staticmethod
    def _restart():
        import subprocess
        p = subprocess.Popen([HAPROXY_INIT, 'reload'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        if p.returncode == 0:
            return True

        raise Exception("Error restarting service: %s" % err)

ECMHaproxy().run()

