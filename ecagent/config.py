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

import random
import socket

from time import sleep
from platform import node
from configobj import ConfigObj

# Twisted imports
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage

# Local
import ecagent.twlogging as log

_URL_METADATA_TIMEOUT = 2
_URL_METADATA_INSTANCE_ID = 'http://169.254.169.254/latest/meta-data/instance-id'

_ECMANAGED_AUTH_URL = 'https://app.ecmanaged.com/agent/meta-data/uuid'
_ECMANAGED_AUTH_URL_ALT = 'https://app.ecmanaged.com/agent/meta-data/uuid'


class SMConfigObj(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the MAC and try to
    reconfigure if it has changed before launching the agent.
    """
    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    @inlineCallbacks
    def check_uuid(self):
        mac = self._get_mac()

        # Always generate a new password if not is set
        if not self['XMPP']['password']:
            self['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]

        if mac:
            if str(mac) == str(self._get_stored_mac()):
                log.debug("MAC has not changed. Skip UUID check")

            else:
                # Try to get uuid (one hour and a half loop: 360x15)
                uuid = None
                for i in range(360):
                    try:
                        uuid = yield self._get_uuid()
                        if uuid:
                            break

                    except Exception:
                        pass
                    sleep(15)

                if not uuid:
                    log.error("ERROR: Could not obtain UUID. please set up XMPP manually in %s" % self.filename)
                    raise Exception('Could not obtain UUID')

                if str(uuid) == str(self._get_stored_uuid()):
                    log.debug("UUID has not changed.")
                    self['XMPP']['mac'] = mac
                    self.write()

                else:
                    log.info("UUID has changed, reconfiguring XMPP user/pass")
                    self['XMPP']['user'] = '@'.join((uuid, self['XMPP']['host']))
                    self['XMPP']['mac'] = mac
                    self.write()

            returnValue(True)

        else:
            log.error("ERROR: Could not obtain MAC. please set up XMPP manually in %s" % self.filename)
            raise Exception('Could not obtain UUID')

    def _get_uuid(self):
        if self['XMPP'].as_bool('manual'):
            log.info("Skipping UUID auto configuration as manual flag is set.")
            return self['XMPP']['user'].split('@')[0]

        else:
            # Try to get from preconfigured
            log.info("try to get UUID via preconfiguration")
            uuid = self._get_uuid_pre_configured()

            if not uuid:
                # Try to configure via URL (ECM meta-data)
                log.info("try to get UUID via URL (ecagent meta-data)")
                uuid = self._get_uuid_via_web()

            return uuid

    @inlineCallbacks
    def _get_uuid_via_web(self):
        hostname = ''
        address = ''
        mac = ''
        try:
            hostname = self._get_hostname()
            address = self._get_ip()
            mac = self._get_mac()
        except Exception:
            pass

        auth_url = _ECMANAGED_AUTH_URL + "/?ipaddress=%s&hostname=%s&mac=%s" % (address, hostname, mac)
        auth_url_alt = _ECMANAGED_AUTH_URL_ALT + "/?ipaddress=%s&hostname=%s&mac=%s" % (address, hostname, mac)

        auth_content = yield getPage(auth_url)

        if not auth_content:
            auth_content = yield getPage(auth_url_alt)

        for line in auth_content.splitlines():
            if line and line.startswith('uuid:'):
                returnValue(line.split(':')[1])

        returnValue('')

    def _get_stored_uuid(self):
        return self['XMPP']['user'].split('@')[0]

    def _get_stored_mac(self):
        return self['XMPP']['mac']

    @staticmethod
    def _get_uuid_pre_configured():
        from os import remove
        from os.path import dirname, abspath, join, exists

        uuid_file = join(dirname(__file__), './config/_uuid.cfg')
        if exists(uuid_file):
            f = open(uuid_file, 'r')
            for line in f:
                if line.startswith('uuid:'):
                    return line.split(':')[1]
            f.close()
            remove(uuid_file)

        return None

    @staticmethod
    def _get_ip():
        """Create dummy socket to get address"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('app.ecmanaged.com', 0))
        return s.getsockname()[0]

    @staticmethod
    def _get_hostname():
        return node()

    @staticmethod
    def _get_mac():
        """
        Try to get a unique identified, Some providers may change mac on stop/start
        Use a low timeout to speed up agent start when no meta-data url
        """
        uuid = None
        try:
            import urllib
            # Get info from meta-data
            socket.setdefaulttimeout(_URL_METADATA_TIMEOUT)
            urlopen = urllib.urlopen(_URL_METADATA_INSTANCE_ID)
            socket.setdefaulttimeout(10)

            for line in urlopen.readlines():
                if "i-" in line:
                    uuid = hex(line)
            urlopen.close()

        except Exception:
            pass

        if not uuid:
            # Use network mac address
            from uuid import getnode
            from re import findall
            uuid = ':'.join(findall('..', '%012x' % getnode()))

        return uuid
