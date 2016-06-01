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
from ecagent.runner import CommandRunner
from ecagent.message import ECMessage

import ecagent.twlogging as log
from ecagent.functions import mem_clean

from monitor import ECMMonitor
from system import ECMInfo

from message import AGENT_VERSION_PROTOCOL

AGENT_VERSION = 4

_E_RUNNING_COMMAND = 253
_E_UNVERIFIED_COMMAND = 251

_CHECK_RAM_MAX_RSS_MB = 125
_CHECK_RAM_INTERVAL = 60

KEEPALIVED_TIMEOUT = 180

MAIN_LOOP_TIME = 15
SYSTEM_LOOP_TIME = 15

class SMAgent:
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
            SMAgent(self.config)

    @staticmethod
    def _on_config_failed(failure):
        log.critical("Configuration check failed with: %s, exiting." % failure)
        log.critical("Please try configuring the XMPP subsystem manually.")
        reactor.stop()


class SMAgent():
    def __init__(self, config):
        """
        XMPP agent class.
        """
        log.info("Starting Agent...")

        log.info("Loading Commands...")
        self.command_runner = CommandRunner(config['Plugins'])

        try:
            #self._info()
            reactor.callLater(5, self._info)
        except Exception, e:
            log.info('error: %s' %str(e))

        #self.memory_checker = LoopingCall(self._check_memory, self.running_commands)
        #self.memory_checker.start(_CHECK_RAM_INTERVAL)


        self.periodic_info = LoopingCall(self._main)
        self.periodic_info.start(MAIN_LOOP_TIME, now=True)

    def _info(self):
        '''
        send periodic health info to the backend
        :return:
        '''
        message = ECMessage(type="info", data=ECMInfo.system_info())
        self._send(message)


    def _main(self):
        '''
        send periodic health info to the backend
        :return:
        '''
        message = ECMessage(type="monitor", data=ECMMonitor.monitor_get())
        self._send(message)

    def _processCommand(self, message):

        d = self.command_runner.run_command(message, self._send)

        # Clean message
        message.command_args = {}

        if d:
            d.addCallbacks(self._onCallFinished, self._onCallFailed,
                           callbackKeywords={'message': message},
                           errbackKeywords={'message': message},
            )
            del message
            return d

        else:
            log.info("Command Ignored: Unknown command: %s" % message.command)
            result = (_E_RUNNING_COMMAND, '', "Unknown command: %s" % message.command, 0)
            self._onCallFinished(result, message)

        del message
        return

    def _onCallFinished(self, result, message):
        log.debug('Call Finished')
        message.data = result

        self._send(message)
        log.debug('task finished %s' %message.id)

    def _onCallFailed(self, failure, *argv, **kwargs):
        log.error("onCallFailed")

        log.info(failure)

        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            log.debug('task failed %s' %message.id)
            self._onCallFinished(result, message)

    def _send(self, message):
        log.debug('Send Response')


        if message.type == 'monitor':
            url = 'http://localhost:5000/todos'
            log.info('send info for %s to %s: %s' %(message.type, url, message))

            try:
                content = self._tmp_post(url, message)
                #content = urlopen.readlines()

                for task in content:
                    task = content[task]
                    #log.info('task %s %s %s %s' %(task['id'], task['type'], task['command'], task['command_args']))
                    #log.info('task %s %s %s %s' %(type(task['id']), type(task['type']), type(task['command']), type(task['command_args'])))

                    message = ECMessage(task['id'], task['type'], task['command'], task['command_args'])
                    self._processCommand(message)
                    del message

            except Exception, e:
                log.info('post error: %s' %str(e))

        elif message.type == 'info':
            url = 'http://localhost:5000/info'
            log.info('send info for %s to %s: %s' %(message.type, url, message))
            content = self._tmp_post(url, message)

        elif message.type == 'result':
            url = 'http://localhost:5000/result'
            log.info('send result for %s to %s: %s' %(message.type, url, message))
            content = self._tmp_post(url, message)

    def _check_memory(self, num_running_commands):
        rss = mem_clean('periodic memory clean')
        if not num_running_commands and rss > _CHECK_RAM_MAX_RSS_MB:
            log.critical("Max allowed RSS memory exceeded: %s MB, exiting."
                          % _CHECK_RAM_MAX_RSS_MB)
            reactor.stop()
        del rss

    def _tmp_post(self, url, message):
        import urllib
        import urllib2
        import json

        req = urllib2.Request(url, urllib.urlencode(message.__dict__))
        urlopen = urllib2.urlopen(req)
        content = ''.join(urlopen.readlines())

        return json.loads(content)
