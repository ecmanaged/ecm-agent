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
import core.logging as log

URL_METADATA_TIMEOUT = 2
URL_METADATA_INSTANCE_ID = {
    'aws': 'http://169.254.169.254/latest/meta-data/instance-id',
    'gce': 'http://metadata/computeMetadata/v1/instance/id',
    'do': 'http://169.254.169.254/metadata/v1/id'
}

ECMANAGED_REGISTRY_URL = 'http://my-devel1.ecmanaged.com/agent/meta-data/v3/id'
#ECMANAGED_REGISTRY_URL = 'http://my-devel1.ecmanaged.com/api/v1/agent/auth'
# http://127.0.0.1:5000/api/v1/agent/register


class ECMConfig(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the unique_id and try to
    reconfigure if it has changed before launching the agent.
    """

    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    @inlineCallbacks
    def register(self):
        uuid = self._get_stored_uuid()
        account_id = self.get_stored_account()

        if not uuid and not account_id:
            # Is not an update and no account is set
            log.error('Please configure agent with ./configure --account=XXXXX')
            raise Exception('Please configure agent with ./configure --account=XXXXX')

        unique_id = self._get_unique_id()

        if not unique_id:
            log.error('Could not obtain unique_id. Please set up Auth manually')
            raise Exception('Could not obtain unique_id. Please set up Auth manually')

        # Check all data valid for v3
        if uuid and not '@' in uuid and account_id and self.is_unique_id_same(unique_id):
            log.debug('unique_id has not changed. Skip uuid check')

        else:
            # Try to get uuid (one hour and a half loop: 360x15)
            json_data = None

            for i in range(360):
                log.info("Trying to get UUID via URL (meta-data v2)")
                json_data = yield self._register(unique_id)
                if json_data:
                    break

                sleep(15)

            # Decode metadata
            meta_data = self.parse_meta_data(json_data)

            if not meta_data:
                log.error('Could not obtain UUID. Please set up Auth manually')
                raise Exception('Could not obtain UUID. Please set up Auth manually')

            # Updates from v2 to v3 write account info
            if not account_id and meta_data.get('account'):
                self['Auth']['account'] = meta_data.get('account')

            self['Auth']['uuid'] = meta_data['uuid']
            self['Auth']['unique_id'] = unique_id
            self['Auth']['token'] = meta_data['token']
            self.write()

        returnValue(True)

    def _register(self, unique_id):
        return self._register2(unique_id)

    @inlineCallbacks
    def _register2(self, unique_id):

        headers = {
            'Content-Type': 'application/json; charset=utf-8'
        }
        data = {
            'uuid': self._get_stored_uuid(),
            'ipaddress': self._get_ip(),
            'hostname': self._get_hostname(),
            'account': self.get_stored_account(),
            'unique_id': unique_id,
            'groups': self._get_groups()
        }

        result = None

        try:
            result = yield getPage(ECMANAGED_REGISTRY_URL, method='POST',
                                   postdata=json.dumps(data),
                                   headers=headers)
        except Exception as e:
            log.debug("getPage failed: %s" %e)
            pass

        # Try urllib if doesn't work
        if not result:
            try:
                req = urllib2.Request(ECMANAGED_REGISTRY_URL, json.dumps(data), headers)
                result = urllib2.urlopen(req).read()

            except Exception as e:
                log.debug("urllib2 failed: %s" %e)
                pass

        if result:
            log.debug(result)
            for line in result.splitlines():
                if line:
                    returnValue(line)

        returnValue('')

    def is_unique_id_same(self, unique_id):
        return str(unique_id) == str(self._get_stored_unique_id())

    def _get_stored_uuid(self):
        return self['Auth'].get('uuid', '').split('@')[0]

    def _get_stored_unique_id(self):
        return self['Auth'].get('unique_id', '')

    def _get_groups(self):
        return self['Groups'].get('groups', '')

    def get_stored_account(self):
        return self['Auth'].get('account', '')

    def parse_meta_data(self, json_data):
        try:
            meta_data = json.loads(json_data)
            if meta_data.get('error'):
                log.error('Invalid configuration received: %s' % meta_data['message'])
                return None

        except:
            log.error('Invalid configuration received, will try later')
            return None

        return meta_data

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
        Try to get a unique identified, Some providers may change unique_id on stop/start
        Use a low timeout to speed up agent start when no meta-data url
        """
        log.info("Trying to get unique_id...")
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
