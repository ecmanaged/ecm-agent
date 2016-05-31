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

class ECMessage(object):
    def __init__(self, id = '', type= '', command = '', command_args= '', data = '', timeout = '' ):
        self.id = id
        self.type = type
        self.command = command
        self.command_name = command.replace('.', '_')
        if isinstance(command_args, unicode):
            self.command_args = ast.literal_eval(command_args)
        else:
            self.command_args = command_args
        self.data = data
        self.timeout = timeout
        self.version = AGENT_VERSION_CORE
        self.protocol = AGENT_VERSION_PROTOCOL

    def __getitem__(self, key):
            return {}
