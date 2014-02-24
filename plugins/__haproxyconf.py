"""
Copyright (C) 2013 - Aybuke Ozdemir <aybuke.147@gmail.com>

this file is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

this file is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>

"""
# -*- coding: utf-8 -*-

from __haproxy import HAProxyConfig, Option
import simplejson as json
import warnings

from os import path
from tempfile import mktemp

HAPROXY_BIN = '/usr/sbin/haproxy'

TEMPLATE_FILE = '/etc/haproxy/haproxy.tpl'
TEMPLATE_CONFIG = """
global
    maxconn 4096
    user haproxy
    group haproxy
    daemon

defaults
    retries 3
    option redispatch
    option http-server-close
    option forwardfor if-none
    timeout connect 5000
    timeout client 50000
    timeout server 50000
    timeout check 5000
    balance leastconn
"""


class ECMHAConfig:
    def __init__(self, ecm_hash, template=TEMPLATE_FILE, as_json=False):
        if as_json:
            ecm_hash = json.loads(ecm_hash)

        if not self._check(ecm_hash):
            raise Exception('Invalid hash received')

        if not path.isfile(template):
            warnings.warn("Template file not found, using default config")
            template = mktemp()
            f = open(template, 'w')
            f.write(TEMPLATE_CONFIG)
            f.close()

        self.template = template
        self.ecm_hash = ecm_hash
        self.config = HAProxyConfig(template)
        self._loads()

    def show(self, as_json=False):
        config_to_show = self.config.createHash()
        if as_json:
            config_to_show = json.dumps(config_to_show)
        print config_to_show

    def read(self, read_file, as_json=True):
        f = open(read_file, 'r')
        first_line = f.readline()
        f.close()

        if first_line.startswith('#'):
            json_config = first_line.split('#')[1]

            if not as_json:
                json_config = json.loads(json_config)
            return json_config

        return False

    def valid(self):
        config = self.config.getConfig()
        return is_valid(config)

    def write(self, write_file):
        if write_file == self.template:
            raise Exception("Can't use template as final file")

        config = self.config.getConfig()
        f = open(write_file, 'w')
        f.write("#" + json.dumps(self.ecm_hash) + "\n")
        f.write(config)
        f.close()

    def _check(self, ecm_hash):
        if ecm_hash.get('health', None) is None:
            return False
        if ecm_hash.get('listeners', None) is None:
            return False
        if ecm_hash.get('backends', None) is None:
            return False

        return True

    # private functions

    def _loads(self):
        health_timeout = self.ecm_hash['health']['timeout']
        health_threshold = self.ecm_hash['health']['threshold']
        health_interval = self.ecm_hash['health']['threshold']
        health_check = self.ecm_hash['health']['check']

        listeners = False

        # Get check data
        (hproto, hport, hpath) = health_check.split('::')

        for listener in self.ecm_hash['listeners']:
            listeners = True
            (fproto, fport, bproto, bport) = listener.split('::')
            self.config.addListen(name="front-%s" % fport, port=fport, mode=self._protocol_dic(fproto))
            listen = self.config.getListen("front-%s" % fport)

            # Add check timeout configuration
            listen.addOption(Option('timeout', ('check %i' % (health_timeout*1000),)))
            
            if self._protocol_dic(fproto) == 'http':
                listen.addOption(Option('cookie', ('ECDN-HA-ID insert indirect nocache maxidle 30m maxlife 8h',)))

            	if hpath:
                	check = 'httpchk HEAD %s' % hpath
                	listen.addOption(Option('option', (check,)))

            for backend in self.ecm_hash['backends']:
                uuid = backend.keys()[0]
                server = '%s %s:%s check inter %i rise %i fall %i' % (uuid, backend[uuid], fport, health_interval*1000,
                                                                      health_threshold, health_threshold)
		if self._protocol_dic(fproto) == 'http':
			server += ' cookie %s' % uuid

                listen.addOption(Option('server', (server,)))
	    

        if not listeners:
            # Add default listener
            self.config.addListen(name="empty", port=80, mode='http')

    @staticmethod
    def _protocol_dic(proto):
        retval = 'tcp'
        if proto.lower() == 'http':
            retval = 'http'

        return retval


def is_valid(config):
    import subprocess

    tmp_file = mktemp()
    f = open(tmp_file, 'w')
    f.write(config)
    f.close()

    p = subprocess.Popen([HAPROXY_BIN, "-c", "-f", tmp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    if p.returncode == 0:
        return True

    warnings.warn("Invalid configuration file: %s" % err)
    return False

