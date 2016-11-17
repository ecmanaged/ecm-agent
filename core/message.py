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
import base64
import simplejson as json
import time
from datetime import datetime
import core.logging as log

AGENT_VERSION_CORE = 4
AGENT_VERSION_PROTOCOL = 1
DEFAULT_TIMEOUT = 300
MESSAGE_TYPE_RESPONSE = 'response'

class ECMMessage():
    def __init__(self, task):
        self.id = task['id']
        self.type = task['type']
        self.command = task['command']
        self.command_name = self.command.replace('.', '_')
        self.localtime = time.time()
        self.timeout = task.get("timeout", None)
        self.version = AGENT_VERSION_CORE
        self.protocol = AGENT_VERSION_PROTOCOL
        self.repeated_task = task.get("repeat", True)
        self.delete_task = task.get("delete", False)
        self.params = task.get("params", {})

        # Params always is json encoded and b64
        if self.params and self.params.strip():
            args = base64.b64decode(self.params)
            self.params = json.loads(args)

        log.debug('MESSAGE - id: %s, type: %s, command: %s, params: %s' % (self.id, self.type, self.command, self.params))

    def to_json(self, result, token, unique_id, groups):
        return json.dumps({
            'unique_uuid': unique_id, 
            'task_id': self.id,
            'type': self.type,
            'groups': groups,
            'command': self.command,
            'result': result,
            'token': token,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        })
    
    def __getitem__(self, key):
            return {}
