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

AGENT_VERSION_CORE = 4
AGENT_VERSION_PROTOCOL = 1

DEFAULT_TIMEOUT = 300
MESSAGE_TYPE_RESPONSE = 'response'

import base64
import simplejson as json
import time

import core.logging as log

class ECMMessage(object):
    def __init__(self, message_id, message_type, command, params=None, response=None, timeout=DEFAULT_TIMEOUT):
        self.id = message_id
        self.type = message_type
        self.command = command
        self.command_name = command.replace('.', '_')
        self.localtime = time.time()
        self.response = response
        self.timeout = timeout
        self.version = AGENT_VERSION_CORE
        self.protocol = AGENT_VERSION_PROTOCOL
        self.params = {}

        # Params always is json encoded and b64
        if params and params.strip():
            args = base64.b64decode(params)
            self.params = json.loads(args)

        log.debug('MESSAGE - id: %s, type: %s, command: %s, params: %s' % (self.id, self.type, self.command, self.params))

    def to_result(self, result):
        return {
            'id':   self.id,
            'type': MESSAGE_TYPE_RESPONSE,
            'command': self.command,
            'result': result,
            'duration': time.time() - self.localtime
        }

    def __getitem__(self, key):
            return {}
