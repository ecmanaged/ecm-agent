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

import ast
import base64
import json

class ECMessage(object):
    def __init__(self, id = '', type= '', command = '', command_args= '', data = '', timeout = '' ):
        self.id = id
        self.type = type
        self.command = command
        self.command_name = command.replace('.', '_')
        self.command_args = command_args
        if self.command_args.strip():
            if isinstance(command_args, unicode):
                if self.command_name == 'monitor_plugin_install':
                    self.command_args = ast.literal_eval(command_args)
                else:
                    args = base64.b64decode(command_args)
                    self.command_args = ast.literal_eval(args)
            elif isinstance(command_args, str):
                self.command_args = json.loads(command_args)
            else:
                self.command_args = command_args
        else:
            self.command_args = {}

        if not isinstance(self.command_args, dict):
            raise Exception('command arg should be a dictionary')
        self.data = data
        self.timeout = timeout
        self.version = AGENT_VERSION_CORE
        self.protocol = AGENT_VERSION_PROTOCOL

    def __getitem__(self, key):
            return {}
