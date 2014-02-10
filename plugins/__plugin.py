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


_PLUGIN_VERSION = 1.1
_ALLOW_PLUGIN_UPDATES = 1

_E_RUNNING_COMMAND = 253
_E_COMMAND_NOT_DEFINED = 252

_FINAL_OUTPUT_STRING = '[__response__]'

PROTECTED_FILES = [
    '/etc/shadow',
]

import os
import sys
import inspect
from base64 import b64decode

import simplejson as json

import __helper as ecm


sys.stdout.flush()
sys.stderr.flush()


class ECMPlugin:
    def __init__(self, *argv, **kwargs):
        pass

    def run(self):
        if len(sys.argv) == 1 or sys.argv[1] == '':
            return self._list_commands()

        else:
            command_name = sys.argv[1]
            sys.exit(self._run_command(command_name))

    def cmd_plugin_version(self, *argv, **kwargs):
        """
        Just return plugin version information
        cmd_plugin_version[]
        """
        return _PLUGIN_VERSION

    def cmd_plugin_update(self, *argv, **kwargs):
        """
        Updates a plugin file from server
        cmd_plugin_update[file,content]
        """
        plugin = kwargs.get('plugin', None)
        content = kwargs.get('content', None)

        if not _ALLOW_PLUGIN_UPDATES:
            raise ecm.NotAllowed("Plugin update is disabled")

        if not plugin or not content:
            raise ecm.InvalidParameters(self.cmd_plugin_update.__doc__)

        # Get plugin path using my path
        plugin_file = os.path.join(
            os.path.dirname(__file__),
            os.path.basename(plugin)
        )

        try:
            # Only update exiting plugins
            if os.path.isfile(plugin_file):
                ecm.file_write(plugin_file, b64decode(content))
                return True
        except:
            pass

        return False

    def _list_commands(self):
        for member in inspect.getmembers(self):
            #Retrieve method names starting with "cmd_" (commands)
            if member[0].startswith('cmd_') and inspect.ismethod(member[1]):
                command_name = member[0][4:]
                command_args = inspect.getargspec(member[1])[0][1:]
                print command_name, command_args

    def _run_command(self, command_name):
        try:
            command = getattr(self, 'cmd_' + command_name)

        except:
            sys.stderr.write("Command not defined (%s)" % command_name)
            sys.exit(_E_COMMAND_NOT_DEFINED)

        # Read command's arguments from stdin in json format (b64).
        lines = []
        for line in sys.stdin: lines.append(line)
        command_args = json.loads(b64decode('\n'.join(lines)))

        try:
            # convert returned data to json
            data = command(**command_args)
            sys.stdout.write("\n" + _FINAL_OUTPUT_STRING + "\n" + json.dumps(data))
            return

        except Exception:
            exctype, value = sys.exc_info()[:2]
            data = {
                'stdout': '',
                'stderr': "ERROR: %s" % value,
                'out': _E_RUNNING_COMMAND,
                'exception': 1
            }
            sys.stdout.write("\n" + _FINAL_OUTPUT_STRING + "\n" + json.dumps(data))
            return _E_RUNNING_COMMAND

    def _update_plugins(self):
        pass

