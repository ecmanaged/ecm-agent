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
import urllib2
import simplejson as json

from time import sleep
from platform import node
from configobj import ConfigObj

# Twisted imports
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage

# Local
import ecagent.twlogging as log

URL_METADATA_TIMEOUT = 2
URL_METADATA_INSTANCE_ID = {
    'aws': 'http://169.254.169.254/latest/meta-data/instance-id',
    'gce': 'http://metadata/computeMetadata/v1/instance/id',
    'do': 'http://169.254.169.254/metadata/v1/id'
}

#/ECMANAGED_AUTH_URL = 'https://app.ecmanaged.com/agent/meta-data/v2/id'
ECMANAGED_AUTH_URL = 'http://my-devel1.ecmanaged.com/agent/meta-data/v2/id'


class SMConfigObj(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the UNIQUE_ID and try to
    reconfigure if it has changed before launching the agent.
    """

    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    @inlineCallbacks
    def check_config(self):
        unique_id = self._get_unique_id()

        if not unique_id:
            log.error('ERROR: Could not obtain UNIQUE_ID. Please set up XMPP manually')
            raise Exception('Could not obtain UUID. Please set up XMPP manually')

        if not self.get_stored_account():
            data = None
            for i in range(360):
                log.info("Trying to get configuration via URL (ecagent meta-data v2)")
                data = yield self._get_config(unique_id)
                log.info('Config: %s' % data)
                if data:
                    log.info('Config: %s' % data)
                    break

                sleep(15)

            if not data:
                log.error('ERROR: Could not obtain UUID. Please set up XMPP manually')
                raise Exception('Could not obtain UUID. Please set up XMPP manually')

            try:
                get_config = json.loads(data)

            except:
                log.error('ERROR: Invalid configuration received, try later')
                raise Exception('Invalid configuration received, try later')

            self['XMPP']['account'] = get_config['account']
            self.write()


        if self._get_stored_uuid() and self.is_unique_id_same(unique_id):
            log.debug('UNIQUE ID has not changed. Skip UUID check')

            # Updates from v2 to v3 write account info
            self['XMPP']['user'] = self['XMPP']['user'].split('@')[0]

        else:
             # Try to get uuid (one hour and a half loop: 360x15)
            data = None
            for i in range(360):
                log.info("Trying to get configuration via URL (ecagent meta-data v2)")
                data = yield self._get_config(unique_id)
                log.info('Config: %s' % data)
                if data:
                    log.info('Config: %s' % data)
                    break

                sleep(15)

            if not data:
                log.error('ERROR: Could not obtain UUID. Please set up XMPP manually')
                raise Exception('Could not obtain UUID. Please set up XMPP manually')

            try:
                get_config = json.loads(data)

            except:
                log.error('ERROR: Invalid configuration received, try later')
                raise Exception('Invalid configuration received, try later')

            if not self['XMPP'].get('password'):
                self['XMPP']['password'] = hex(random.getrandbits(256))[2:-1]

            # Updates from v2 to v3 write account info
            if not self.get_stored_account() and get_config.get('account'):
                self['XMPP']['account'] = get_config.get('account')

            if self._get_stored_uuid() and str(get_config.get('uuid')) == str(self._get_stored_uuid()):
                log.debug('UUID has not changed.')
                self['XMPP']['unique_id'] = unique_id
                self.write()

            else:
                log.info('UUID has changed, reconfiguring XMPP user/pass')
                self['XMPP']['user'] = get_config['uuid']
                self['XMPP']['unique_id'] = unique_id
                self.write()

        returnValue(True)

    def _get_config(self, unique_id):
        _config = self._get_config2(unique_id)
        return _config

    @inlineCallbacks
    def _get_config2(self, unique_id):
        hostname = self._get_hostname()
        address = self._get_ip()
        uuid = self._get_stored_uuid()
        account = self.get_stored_account()

        params = "?uuid=%s&ipaddress=%s&hostname=%s&unique_id=%s&account=%s" \
                 % (uuid, address, hostname, unique_id, account)

        auth_url = ECMANAGED_AUTH_URL + '/' + params
        auth_content = yield getPage(auth_url)

        #////////////////////////////FIX FOR AMAZON AMI SSL HANDSHAKE ERROR///////////////
        if not auth_content:
            try:
                auth_content = urllib2.urlopen(auth_url).read()
            except:
                pass
        #///////////////////////////END OF FIX///////////////////////////////////////////

        if auth_content:
            for line in auth_content.splitlines():
                if line:
                    returnValue(line)

        returnValue('')

    def is_unique_id_same(self, unique_id):
        return str(unique_id) == str(self._get_stored_unique_id())

    def _get_stored_uuid(self):
        return self['XMPP'].get('user', '')

    def _get_stored_unique_id(self):
        return self['XMPP'].get('unique_id', '')

    def get_stored_account(self):
        return self['XMPP'].get('account', '')

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
        log.info("Trying to get UNIQUE ID")
        unique_id = None

        try:
            # Get info from meta-data
            socket.setdefaulttimeout(URL_METADATA_TIMEOUT)

            for metadata_type in URL_METADATA_INSTANCE_ID.keys():

                try:
                    request = urllib2.Request(URL_METADATA_INSTANCE_ID[metadata_type])

                    # Google needs header
                    if metadata_type == 'gce':
                        request.add_header('Metadata-Flavor', 'Google')

                    response = urllib2.urlopen(request)
                    instance_id = response.readlines()[0]
                    response.close()

                except urllib2.URLError:
                    continue

                if instance_id:
                    unique_id = metadata_type + '::' + instance_id
                    break

        except:
            pass
        finally:
            # Set default timeout again
            socket.setdefaulttimeout(10)

        if not unique_id:
            # Use network mac address
            from uuid import getnode
            from re import findall

            unique_id = 'mac::' + ':'.join(findall('..', '%012x' % getnode()))

        return unique_id
