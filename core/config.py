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


class ECMConfig(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the unique_id and try to
    reconfigure if it has changed before launching the agent.
    """
    def __init__(self, filename):
        ConfigObj.__init__(self, filename)
    
    def register(self):
        account_id = self.get_stored_account()

        if not account_id:
            # Is not an update and no account is set
            log.error('Please configure agent with ./configure --account=XXXXX')
            raise Exception('Please configure agent with ./configure --account=XXXXX')

        unique_uuid = self._get_unique_uuid()
        if not unique_uuid:
            log.error('Could not obtain unique_uuid. Please set up Auth manually')
            raise Exception('Could not obtain server_id. Please set up Auth manually')
        
        return unique_uuid

    def get_stored_account(self):
        return self['Auth'].get('account', '')

    @staticmethod
    def _get_unique_uuid():
        """
        Try to get a unique identified, Some providers may change unique_id on stop/start
        Use a low timeout to speed up agent start when no meta-data url
        """
        log.info("Trying to get unique_id...")
        unique_uuid = None

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
                    unique_uuid = metadata_type + '::' + instance_id
                    break
        except:
            pass
        finally:
            # Set default timeout again
            socket.setdefaulttimeout(10)

        if not unique_uuid:
            # Use network mac address
            from uuid import getnode
            from re import findall
            unique_uuid = 'mac::' + ':'.join(findall('..', '%012x' % getnode()))
        return unique_uuid
