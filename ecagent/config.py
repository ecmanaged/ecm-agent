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

import urllib
import urllib2
import json

from configobj import ConfigObj

# Twisted imports
from twisted.internet.defer import inlineCallbacks, returnValue

class SMConfigObj(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the UNIQUE_ID and try to
    reconfigure if it has changed before launching the agent.
    """

    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    def check_config(self):
        username = self._get_stored_username()
        password = self.get_stored_password()

        if not username and not password:
            auth_url = 'http://127.0.0.1:5000/agent/register'
            data = {}
            data['result'] = ' '
            headers = {}
            headers["Content-Type"] = "application/json"
            content = None

            try:
                req = urllib2.Request(auth_url, urllib.urlencode(data), headers)
                urlopen = urllib2.urlopen(req)
                content = ''.join(urlopen.readlines())
                content_dict = json.loads(content)
            except Exception, e:
                raise Exception('registration failed')

            username = self['USER']['username'] = content_dict['user-id']
            password = self['USER']['password'] = content_dict['password']
            token = self['USER']['token'] = content_dict['token']
            self.write()
	return username, password

    def _get_stored_username(self):
        return self['USER'].get('username', '')

    def get_stored_password(self):
        return self['USER'].get('password', '')
