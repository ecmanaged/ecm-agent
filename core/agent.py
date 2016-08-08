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

# Local
import core.logging as log

from core.runner import CommandRunner
from core.message import ECMMessage
from core.functions import mem_clean, read_url

_CHECK_RAM_MAX_RSS_MB = 125
_CHECK_RAM_INTERVAL = 300
_MAIN_LOOP_INTERVAL = 60

_E_UNKNOWN_COMMAND = 253
_E_INVALID_MESSAGE = 252

ECMANAGED_URL_TASK = 'http://my-devel1.ecmanaged.com/agent/meta-data/task'
ECMANAGED_URL_RESULT = 'http://my-devel1.ecmanaged.com/agent/meta-data/result'

# url = 'http://localhost:5000/agent/' + self.uuid + '/tasks'

class ECMConfig:
    def __init__(self, config):
        reactor.callWhenRunning(self._check_config)
        self.config = config

    def _check_config(self):
        d = self.config.check_config()
        d.addCallback(self._on_config_checked)
        d.addErrback(self._on_config_failed)

    def _on_config_checked(self, success):
        # Ok, now everything should be correctly configured,
        # let's start the party.
        if success:
            ECMAgent(self.config)

    @staticmethod
    def _on_config_failed(failure):
        log.critical("Configuration check failed with: %s, exiting." % failure)
        log.critical("Please try configuring the XMPP subsystem manually.")
        reactor.stop()


class ECMAgent():
    def __init__(self, config):
        """
        Main agent class.
        """
        self.uuid = config['Auth']['uuid']
        self.token = config['Auth']['token']

        log.info("Loading Commands...")
        self.command_runner = CommandRunner()

        # Give time to load commands
        reactor.callLater(3, self._run)

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

        log.info("Reading tasks...")

        for task in self._read_tasks():
            try:
                message = ECMMessage(task['id'], task['type'], task['command'], task['params'])
                self._run_task(message)

            except Exception, e:
                log.error('Error in main loop while generating message for task (%s): %s' % (task['command'], str(e)))

    def _write_result(self, result):
        headers = {
            'Content-Type': 'application/json',
            'x-ecmanaged-token': 'Basic %s' % self.token,
        }

        url = ECMANAGED_URL_RESULT + '/' + self.uuid + '/result'

        log.debug('_write_result::start: %s' % url)
        log.debug('_write_result::data: %s' % result)

        try:
            return read_url(url, result, headers)
        except Exception:
            reactor.disconnectAll()

    def _read_tasks(self):
        headers = {
            'Content-Type': 'application/json',
            'x-ecmanaged-token': 'Basic %s' % self.token
        }

        url = ECMANAGED_URL_TASK + '/' + self.uuid
        log.debug('_url_get::start: %s' %url)

        try:
            return read_url(url, headers=headers)
        except Exception:
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
        self._write_result(message.to_result(result))

    def _memory_checker(self):
        rss = mem_clean('periodic memory clean')

        if rss > _CHECK_RAM_MAX_RSS_MB:
            log.critical("Max allowed RSS memory exceeded: %s MB, exiting."
                         % _CHECK_RAM_MAX_RSS_MB)
            reactor.stop()
