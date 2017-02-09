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
from time import time
from time import sleep
from configobj import ConfigObj
import platform

# Twisted imports
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import getPage

# Local
import core.logging as log
import plugins.__helper as ecm
from plugins.__helper import AGENT_VERSION
import psutil

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

    @inlineCallbacks
    def check_register(self):
        log.info("registering agent...")
        info = {'info': {
            'os': str(platform.system()),
            'machine': str(platform.machine()),
            'uptime': self._boot_time(),
            'hostname': platform.node(),
            'public_ip': self._get_ip(),
            'agent_version': AGENT_VERSION,
            'localtime': time()
        }}

        admin_api = self['API'].get('admin', '')

        if not admin_api:
            log.error('Could not obtain admin api.')
            raise Exception('Could not obtain admin api.')

        account_id = self.get_stored_account()
        unique_uuid = self._obtain_unique_uuid()

        registration_url = '{}/{}/{}'.format(admin_api, account_id, unique_uuid)
        log.info('registration_url: %s' %registration_url)
        log.info('info: %s' %str(info))

        for iter in range(5):
            try:
                req = urllib2.Request(registration_url, json.dumps(info))
                req.add_header('Content-Type', 'application/json')
                urlopen = yield urllib2.urlopen(req)
                result = urlopen.read()
                result_dict = json.loads(result)
                log.info('api response: %s' %str(result_dict))
                if urlopen.getcode() == 200:
                    log.info("agent has successfully registered")
                    returnValue(True)
            except urllib2.HTTPError:
                log.info('exception HTTPERROR while sending result')
            except urllib2.URLError:
                log.info('exception URLERROR while sending result')
        raise Exception('failed to register agent')

    def get_unique_uuid(self):
        account_id = self.get_stored_account()

        unique_uuid = self._obtain_unique_uuid()
        if not unique_uuid:
            log.error('Could not obtain unique_uuid. Please set up Auth manually')
            raise Exception('Could not obtain server_id. Please set up Auth manually')

        return unique_uuid

    def get_stored_account(self):
        account = self['Auth'].get('account', '')
        if not account:
            log.error('Please configure agent with ./configure --account=XXXXX')
            raise Exception('Please configure agent with ./configure --account=XXXXX')
        return account

    @staticmethod
    def _obtain_unique_uuid():
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

    def _boot_time(self):
        """ Returns server boot time """
        if ecm.is_win():
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
