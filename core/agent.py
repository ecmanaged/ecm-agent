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

# Local
import core.exceptions as exceptions
import core.logging as log

from core.runner import CommandRunner
from core.message import ECMMessage
from core.functions import mem_clean, read_url


_CHECK_RAM_MAX_RSS_MB = 125
_CHECK_RAM_INTERVAL = 300
_MAIN_LOOP_INTERVAL = 60
_E_UNKNOWN_COMMAND = 253
_E_INVALID_MESSAGE = 252
KEEPALIVED_TIMEOUT = 180
SOCKET_TIMEOUT = 30


class ECMAgent():
    def __init__(self, config):
        """
        Main agent class.
        """
        self.config = config
        self.account = self.config['Auth']['account']
        self.unique_uuid = self.config.register()

        self.ECMANAGED_URL_INPUT = 'http://localhost:8000/v1/agent/ecagent/input?api_key={0}'.format(self.account)

        self.tasks = {}
        system_health = {"__base__":
                             {
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

        reactor.callLater(5, self._run_info)
        reactor.callLater(10, self._run)

    def _run_info(self):
        info_task = {
            "data": u"",
            "command": "system_info",
            "timeout": "30",
            "type": "info",
            "id": "system_info"
        }
        message = ECMMessage(info_task)
        self._run_task(message)

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

    def _write_result(self, result):
        log.debug('_write_result::start: %s' % self.ECMANAGED_URL_INPUT)
        log.info('_write_result::data: %s' % result)

        try:
            req = urllib2.Request(self.ECMANAGED_URL_INPUT, result)
            req.add_header('Content-Type', 'application/json')
            urlopen = urllib2.urlopen(req)
            result = urlopen.read()
            result_dict = json.loads(result)
            log.debug('api response: %s' %str(result_dict))
        except urllib2.HTTPError:
            log.info('exception HTTPERROR while sending result')
        except urllib2.URLError:
            log.info('exception URLERROR while sending result')
            reactor.disconnectAll()

    def _run_task(self, message):
        log.debug("_run_task::command: %s" % message.command)
        flush_callback = self._flush

        d = self.command_runner.run_command(message, flush_callback)

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
        self._send(result, message)
        log.debug('command finished %s' % message.command_name)

    def _on_call_failed(self, failure, *argv, **kwargs):
        log.error("onCallFailed")
        log.info(failure)

        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            self._on_call_finished(result, message)

    def _flush(self, result, message):
        log.debug('Flush Message')
        self._send(result, message)

    def _send(self, result, message):
        log.debug('send result for %s %s' % (message.type, message.command))
        groups = self.config['Groups']['groups']
        self._write_result(message.to_json(result, self.account, self.unique_uuid, groups))

    def _memory_checker(self):
        rss = mem_clean('periodic memory clean')

        if rss > _CHECK_RAM_MAX_RSS_MB:
            log.critical("Max allowed RSS memory exceeded: %s MB, exiting."
                         % _CHECK_RAM_MAX_RSS_MB)
            reactor.stop()
