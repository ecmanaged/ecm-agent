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

from os.path import dirname, join
from configobj import ConfigObj

# Local
from __plugin import ECMPlugin
import __helper as ecm

# Needs to read config to get available nagios commands
PATH_TO_CONFIG = '../config/ecagent.cfg'


class ECMNagios(ECMPlugin):
    def __init__(self, *argv, **kwargs):
        config_filename = join(dirname(__file__), PATH_TO_CONFIG)

        try:
            config = ConfigObj(config_filename)
            self.commands = self._get_commands(config)

        except Exception:
            raise Exception("Unable to read config at %s" % config_filename)

    def cmd_nagios_command(self, *argv, **kwargs):
        """
        Syntax: nagios.command[command,args]
        """
        command = kwargs.get('command', None)
        params = kwargs.get('params', None)

        if not command:
            raise ecm.InvalidParameters(self.cmd_nagios_command.__doc__)

        if command not in self.commands.keys():
            raise Exception("Command %s is not available" % command)

        return ecm.run_command(self.commands[command], params)

    def cmd_nagios_get_commands(self, *argv, **kwargs):
        """
        Syntax: nagios.get_commands[]
        """
        return self.commands

    @staticmethod
    def _get_commands(config):
        retval = {}
        if config.get('nagios', None) is not None:
            for command in config['nagios'].keys():
                retval[command] = config['nagios'][command]

        return retval

ECMNagios().run()

