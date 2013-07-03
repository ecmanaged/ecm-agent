# -*- coding:utf-8 -*-

from sys import argv, exit, exc_info, stdin, stdout, stderr

import inspect
import simplejson as json

from ecmcommon import ECMCommon
import base64

E_RUNNING_COMMAND = 253
E_COMMAND_NOT_DEFINED = 252

import sys
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
            print >> stderr, "Command not defined (%s)" % command_name
            exit(E_COMMAND_NOT_DEFINED)

        #Read command's arguments from stdin in json format.
        lines = []
        for line in stdin: lines.append(line)
        command_args = json.loads(base64.b64decode('\n'.join(lines)))

        try:
            # convert returned data to json
            data = command(**command_args)
            sys.stdout.write("\n**__ecagent__**\n" + json.dumps(data))
            return

        except Exception, e:
            et, ei, tb = exc_info()
            print >> stderr, "%s" %e
            return E_RUNNING_COMMAND

    def run(self):
        if len(argv) == 1 or argv[1] == '':
            #Show available commands if no command selected
            return self._listCommands()
        else:
            command_name = argv[1]
            exit(self._runCommand(command_name))

