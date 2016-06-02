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

from message import AGENT_VERSION_PROTOCOL

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
        # Simulate a received task
        message = ECMessage('989b3c79caf30c9b0df05083d47809f381fe9e83::VMOsVbQxj1Tml0kJotr76Q', 'info', 'system.info', {'timeout': '30'})

        #log.info("system.info")
        log.info('loaded commands: %s' %self.command_runner._commands)

        flush_callback = self._flush
        #message.command_name = message.command.replace('.', '_')

        #log.info("command: %s" %message.command_name)

        d = self.command_runner.run_command(message, flush_callback)

        # Clean message
        #message.command_args = {}

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


    def _main(self):
        '''
        send periodic health info to the backend
        :return:
        '''
        # Simulate a received task
        message = ECMessage('989b3c79caf30c9b0df05083d47809f381fe9e83::VMOsVbQxj1Tml0kJotr76Q', 'main', 'monitor.get', {'config': 'eyJfX2Jhc2VfXyI6eyJuYW1lIjoiU1lTVEVNIEhFQUxUSCIsImNvbmZpZyI6e30sImlkIjoiX19iYXNlX18iLCJpbnRlcnZhbCI6NjB9fQ==', 'timeout': '30'})

        try:
            self._new_task(message)
        except Exception, e:
            log.info('error: %s' %str(e))


    def _new_task(self, msg):
        """
        A new IQ message has been received and we should process it.
        """
        log.debug('_new_task')

        # check if message is TASK
        log.debug("Message type: %s" % msg['type'])

        self._processCommand(msg)

    def _processCommand(self, message):
        flush_callback = self._flush
        #message.command_name = message.command.replace('.', '_')

        #log.info("command: %s" %message.command_name)

        d = self.command_runner.run_command(message, flush_callback)

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
        self._send(result, message)
        log.debug('command finished %s' %message.command_name)

    def _onCallFailed(self, failure, *argv, **kwargs):
        log.error("onCallFailed")
        log.info(failure)

        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            self._onCallFinished(result, message)

    def _flush(self, result, message):
        log.debug('Flush Message')
        self._send(result, message)

    def _send(self, result, message):
        log.debug('Send Response')
        import urllib
        import urllib2
        import json

        if message.type == 'main':
            url = 'http://localhost:5000/todos'
            data = {}
            data['result']= result

            #log.info('posting data %s' %data)

            try:
                req = urllib2.Request(url, urllib.urlencode(data))
                urlopen = urllib2.urlopen(req)
                content = ''.join(urlopen.readlines())
                content = json.loads(content)
                #content = urlopen.readlines()
                for task in content:
                    task = content[task]
                    #log.info('task %s %s %s %s' %(task['id'], task['type'], task['command'], task['command_args']))
                    #log.info('task %s %s %s %s' %(type(task['id']), type(task['type']), type(task['command']), type(task['command_args'])))

                    message = ECMessage(task['id'], task['type'], task['command'], task['command_args'])
                    #log.info('after converting to message:   %s %s %s %s ' %(message.id, message.type, message.command, message.command_args))

                    flush_callback = self._flush

                    d = self.command_runner.run_command(message, flush_callback)

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

            except Exception, e:
                log.info('post error: %s' %str(e))
        else:
            log.info('send result for %s %s: %s' %(message.type, message.command, result))
            #log.info('send result for %s %s' %(message.type, message.command))
        #log.info("Simulate received task")

        # Simulate a received tastaskk
        #task = ECMessage('989b3c79caf30c9b0df05083d47809f381fe9e83::VMOsVbQxj1Tml0kJotr76Q', 'set', 'sysmtem.info', {'timeout': '30'} )
        #self._new_task(task)

    # def _check_memory(self, num_running_commands):
    #     rss = mem_clean('periodic memory clean')
    #     if not num_running_commands and rss > _CHECK_RAM_MAX_RSS_MB:
    #         log.critical("Max allowed RSS memory exceeded: %s MB, exiting."
    #                      % _CHECK_RAM_MAX_RSS_MB)
    #         reactor.stop()
    #     del rss
