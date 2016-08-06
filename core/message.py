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

AGENT_VERSION_CORE = 3
AGENT_VERSION_PROTOCOL = 1

TIMEOUT_DEFAULT = 300

import ast
import base64
import json
import time

import core.logging as log

class ECMMessage(object):
    def __init__(self, message_id, message_type, command, params=None, response=None, timeout=TIMEOUT_DEFAULT):
        self.id = message_id
        self.type = message_type
        self.command = command
        self.command_name = command.replace('.', '_')
        self.time = time.time()

        if params and params.strip():
            if isinstance(params, unicode):
                if self.command_name == 'monitor_plugin_install':
                    self.params = ast.literal_eval(params)

                else:
                    args = base64.b64decode(params)
                    self.params = ast.literal_eval(args)

            elif isinstance(params, str):
                self.params = json.loads(params)

            else:
                self.params = params
        else:
            self.params = {}

        if not isinstance(self.params, dict):
            raise Exception('command arg should be a dictionary')
        
        self.response = response
        self.timeout = timeout
        self.version = AGENT_VERSION_CORE
        self.protocol = AGENT_VERSION_PROTOCOL

    def to_result(self, result):
        return {
            'id':   self.id,
            'type': self.type,
            'command': self.command,
            'result': result,
            'duration': time.time() - self.time
        }

    def __getitem__(self, key):
            return {}
