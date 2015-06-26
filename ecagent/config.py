# -*- coding:utf-8 -*-

# Copyright (C) 2012 Juan Carlos Moreno <juancarlos.moreno at ecmanaged.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
_URL_METADATA_INSTANCE_ID = {
    'aws': 'http://169.254.169.254/latest/meta-data/instance-id',
    'gce': 'http://metadata/computeMetadata/v1/instance/id',
    'do': 'http://169.254.169.254/metadata/v1/id'
}

_ECMANAGED_AUTH_URL = 'https://app.ecmanaged.com/agent/meta-data/uuid'
_ECMANAGED_AUTH_URL_ALT = 'https://app.ecmanaged.com/agent/meta-data/uuid'


class SMConfigObj(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the UNIQUE_ID and try to
    reconfigure if it has changed before launching the agent.
    """

    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    @inlineCallbacks
    def check_uuid(self):
        unique_id = self._get_unique_id()

        if unique_id:
            if str(unique_id) == str(self._get_stored_unique_id()):
                log.debug("UNIQUE ID has not changed. Skip UUID check")

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
                    self['XMPP']['unique_id'] = unique_id
                    self.write()

                else:
                    log.info("UUID has changed, reconfiguring XMPP user/pass")
                    self['XMPP']['user'] = '@'.join((uuid, self['XMPP']['host']))
                    self['XMPP']['unique_id'] = unique_id
                    self.write()

            returnValue(True)

        else:
            log.error("ERROR: Could not obtain UNIQUE_ID. please set up XMPP manually in %s" % self.filename)
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
        unique_id = ''
        try:
            hostname = self._get_hostname()
            address = self._get_ip()
            unique_id = self._get_unique_id()
        except Exception:
            pass

        auth_url = _ECMANAGED_AUTH_URL + "/?ipaddress=%s&hostname=%s&unique_id=%s" % (address, hostname, unique_id)
        auth_url_alt = _ECMANAGED_AUTH_URL_ALT + "/?ipaddress=%s&hostname=%s&unique_id=%s" % (
            address, hostname, unique_id)

        auth_content = yield getPage(auth_url)

        if not auth_content:
            auth_content = yield getPage(auth_url_alt)

        for line in auth_content.splitlines():
            if line and line.startswith('uuid:'):
                returnValue(line.split(':')[1])

        returnValue('')

    def _get_stored_uuid(self):
        return self['XMPP'].get('user', '').split('@')[0]

    def _get_stored_unique_id(self):
        return self['XMPP'].get('unique_id', '')

    @staticmethod
    def _get_uuid_pre_configured():
        from os import remove
        from os.path import dirname, abspath, join, exists
        
        retval = None

        uuid_file = join(dirname(__file__), './config/_uuid.cfg')
        if exists(uuid_file):
            f = open(uuid_file, 'r')
            for line in f:
                if line.startswith('uuid:'):
                    retval = line.split(':')[1]
            f.close()
            remove(uuid_file)
            
        return retval

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
    def _get_unique_id():
        """
        Try to get a unique identified, Some providers may change UNIQUE_ID on stop/start
        Use a low timeout to speed up agent start when no meta-data url
        """
        uuid = None

        try:
            # Get info from meta-data
            import urllib2
            socket.setdefaulttimeout(_URL_METADATA_TIMEOUT)

            for metadata_type in _URL_METADATA_INSTANCE_ID:
                instance_id = None
                try:
                    request = urllib2.Request(_URL_METADATA_INSTANCE_ID[metadata_type])

                    # Google needs header
                    request.add_header('Metadata-Flavor', 'Google')

                    response = urllib2.urlopen(request)
                    instance_id = response.readlines()[0]
                    response.close()

                except urllib2.URLError, e:
                    continue

                if instance_id:
                    uuid = metadata_type + '::' + instance_id
                    break

        except:
            pass
        finally:
            # Set default timeout again
            socket.setdefaulttimeout(10)

        if not uuid:
            # Use network mac address
            from uuid import getnode
            from re import findall

            uuid = 'mac::' + ':'.join(findall('..', '%012x' % getnode()))

        return uuid

