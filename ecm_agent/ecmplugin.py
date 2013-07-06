# -*- coding:utf-8 -*-

import sys
import inspect
import simplejson as json

from ecmcommon import ECMCommon
from base64 import b64decode

E_RUNNING_COMMAND = 253
E_COMMAND_NOT_DEFINED = 252
STDOUT_FINAL_OUTPUT_STR = '[__ecagent::response__]'

sys.stdout.flush()
sys.stderr.flush()

class ECMPlugin(ECMCommon):
    def _listCommands(self):
        for member in inspect.getmembers(self):
            #Retrieve method names starting with "cmd_" (commands)
            if member[0].startswith('cmd_') and inspect.ismethod(member[1]):
                command_name = member[0][4:]
                command_args = inspect.getargspec(member[1])[0][1:]
                print command_name, command_args

    def _runCommand(self, command_name):
        try:
            command = getattr(self, 'cmd_' + command_name)
        except:
            sys.stderr.write("Command not defined (%s)" % command_name)
            sys.exit(E_COMMAND_NOT_DEFINED)

        # Read command's arguments from stdin in json format (b64).
        lines = []
        for line in sys.stdin: lines.append(line)
        command_args = json.loads(b64decode('\n'.join(lines)))

        try:
            # convert returned data to json
            data = command(**command_args)
            sys.stdout.write("\n" + STDOUT_FINAL_OUTPUT_STR + "\n" + json.dumps(data))
            return

        except Exception:
            exctype, value = sys.exc_info()[:2]
            data = {
                'stdout': '',
                'stderr': "%s: %s" % (exctype,value),
                'out':    E_RUNNING_COMMAND
            }
            sys.stdout.write("\n" + STDOUT_FINAL_OUTPUT_STR + "\n" + json.dumps(data))
            return E_RUNNING_COMMAND

    def run(self):
        if len(sys.argv) == 1 or sys.argv[1] == '':
            #Show a list of available commands if no command selected
            return self._listCommands()
        else:
            command_name = sys.argv[1]
            sys.exit(self._runCommand(command_name))
