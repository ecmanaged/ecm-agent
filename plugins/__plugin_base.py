# -*- coding:utf-8 -*-

import sys
import inspect
from base64 import b64decode

import simplejson as json

# Include common tools
from __plugin_common import ECMcommon

_E_RUNNING_COMMAND = 253
_E_COMMAND_NOT_DEFINED = 252
_FINAL_OUTPUT_STRING = '[__response__]'

_PLUGIN_URL      = 'https://github.com/ecmanaged/ecm-agent-plugins'
_PLUGIN_URL_ALT  = 'https://bitbuket.com/ecmanaged/ecm-agent-plugins'

sys.stdout.flush()
sys.stderr.flush()

class ECMBase(ECMcommon):
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

    def run(self):
        if len(sys.argv) == 1 or sys.argv[1] == '':
            #Show a list of available commands if no command selected
            return self._list_commands()

        else:
            command_name = sys.argv[1]
            sys.exit(self._run_command(command_name))
