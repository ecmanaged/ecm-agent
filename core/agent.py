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

# Twisted imports
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
import base64
import simplejson as json
import socket
import urllib2
from fcache.cache import FileCache

# Local
import core.exceptions as exceptions
import core.logging as log

from core.runner import CommandRunner
from core.message import ECMMessage
from core.functions import mem_clean, read_url

_CHECK_RAM_MAX_RSS_MB = 125
_CHECK_RAM_INTERVAL = 15
_MAIN_LOOP_INTERVAL = 10
_E_UNKNOWN_COMMAND = 253
_E_INVALID_MESSAGE = 252
KEEPALIVED_TIMEOUT = 180
SOCKET_TIMEOUT = 30

class SMAgent():
    def __init__(self, config):
        reactor.callWhenRunning(self._agent_register)
        self.config = config

    def _agent_register(self):
        d = self.config.check_register()
        d.addCallback(self._on_register_passed)
        d.addErrback(self._on_register_failed)

    def _on_register_passed(self, success):
        # Ok, now everything should be correctly configured,
        # let's start the party.
        log.info('registration successfull')
        if success:
            ECMAgent(self.config)

    def _on_register_failed(self, failure):
        log.critical("could not register agent: %s, exiting." % failure)
        log.critical("Please check if account is valid.")
        reactor.stop()



class ECMAgent():
    def __init__(self, config):
        """
        Main agent class.
        """
        self.config = config
        self.account = self.config['Auth']['account']
        self.admin_api = self.config['API']['admin']
        self.collector_api = self.config['API']['collector']

        self.unique_uuid = self.config.get_stored_unique_uuid()

        self.file_cache = FileCache('file_cache', flag='cs')
        self.metric_cache = list()

        if len(self.file_cache):
            log.info('loading data from file cache')
            self.metric_cache = self.file_cache['agent_metric']
            self.file_cache.clear()

        self.metric_url = "{}/{}/{}/metric".format(self.collector_api,
                                                   self.account,
                                                   self.unique_uuid)

        self.tasks = {}

        system_health = {
            "__base__": {
                "interval": 60,
                "config": {},
                "name": "SYSTEM HEALTH",
                "id": "__base__"
            }
        }

        self.tasks["system_health"] = {
            "data": u"",
            "command": "monitor_get",
            "timeout": "30",
            "params": base64.b64encode(json.dumps(system_health)),
            "type": "monitor",
            "id": "system_health"
        }

        log.info("Loading Commands...")

        self.command_runner = CommandRunner(self.config)

        reactor.callLater(10, self._run)

    def _run(self):
        log.info("Setting up Memory checker")
        self.memory_checker = LoopingCall(self._memory_checker)
        self.memory_checker.start(_CHECK_RAM_INTERVAL)

        log.info("Starting main loop")
        self.periodic_info = LoopingCall(self._main)
        self.periodic_info.start(_MAIN_LOOP_INTERVAL, now=True)

    def _main(self):
        """
        send periodic request to the backend
        :return:
        """
        if not self.tasks:
            return

        log.debug('tasks: %s' % self.tasks)

        for item in self.tasks.keys():
            try:
                task = self.tasks[item]
                message = ECMMessage(task)
                if message.delete_task or not message.repeated_task:
                    del self.tasks[item]
                self._run_task(message)

            except Exception as e:
                log.error('Error in main loop while generating message for task (%s): %s' % (task['command'], str(e)))

    def _write_result(self):
        while self.metric_cache:
            if len(self.file_cache):
                self.file_cache.clear()
            result = self.metric_cache.pop()
            try:
                req = urllib2.Request(self.metric_url, result)
                req.add_header('Content-Type', 'application/json')
                urlopen = urllib2.urlopen(req)
            except Exception:
                self.metric_cache.append(result)
                self.file_cache['agent_metric'] = self.metric_cache
                return

    def _run_task(self, message):
        log.debug("_run_task::command: %s" % message.command)
        #flush_callback = self._flush

        #d = self.command_runner.run_command(message, flush_callback)
        d = self.command_runner.run_command(message)

        if d:
            d.addCallbacks(self._on_call_finished, self._on_call_failed,
                           callbackKeywords={'message': message},
                           errbackKeywords={'message': message},
                          )
            del message
            return d

        else:
            log.info("Command Ignored: Unknown command: %s" % message.command)
            result = (_E_UNKNOWN_COMMAND, '', "Unknown command: %s" % message.command, 0)
            self._on_call_finished(result, message)

        del message

        return

    def _on_call_finished(self, result, message):
        log.debug('Call Finished')
        groups = self.config['Groups']['groups']
        data = message.to_json(result, self.account, self.unique_uuid, groups)
        self.metric_cache.append(data)

        # self._send(result, message)
        self._write_result()
        log.debug('command finished %s' % message.command_name)

    def _on_call_failed(self, failure, *argv, **kwargs):
        log.error("onCallFailed")
        log.info(failure)

        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            self._on_call_finished(result, message)

    def _memory_checker(self):
        rss = mem_clean('periodic memory clean')

        if rss > _CHECK_RAM_MAX_RSS_MB:
            log.critical("Max allowed RSS memory exceeded: %s MB, exiting."
                         % _CHECK_RAM_MAX_RSS_MB)
            reactor.stop()

