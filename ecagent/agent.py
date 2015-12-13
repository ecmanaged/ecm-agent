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

import resource
from time import time

# Twisted imports
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

# Local
from ecagent.client import Client
from ecagent.runner import CommandRunner
from ecagent.message import IqMessage

import ecagent.twlogging as log
from ecagent.verify import ECVerify
from ecagent.functions import mem_clean, mem_usage

from message import AGENT_VERSION_PROTOCOL

_E_RUNNING_COMMAND = 253
_E_UNVERIFIED_COMMAND = 251

_CHECK_RAM_MAX_RSS_MB = 125
_CHECK_RAM_INTERVAL = 60

KEEPALIVED_TIMEOUT = 120

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
            SMAgentXMPP(self.config)

    @staticmethod
    def _on_config_failed(failure):
        log.critical("Configuration check failed with: %s, exiting." % failure)
        log.critical("Please try configuring the XMPP subsystem manually.")
        reactor.stop()


class SMAgentXMPP(Client):
    def __init__(self, config):
        """
        XMPP agent class.
        """
        log.info("Starting Agent...")

        log.info("Loading Commands...")
        self.command_runner = CommandRunner(config['Plugins'])

        log.info("Setting up Certificate")
        self.verify = ECVerify()

        log.info("Setting up Memory checker")

        self.running_commands = {}
        self.num_running_commands = 0

        self.memory_checker = LoopingCall(self._check_memory, self.running_commands)
        self.memory_checker.start(_CHECK_RAM_INTERVAL)
        
        self.keepalive = LoopingCall(self._reconnect)

        log.debug("Loading XMPP...")
        Client.__init__(
            self,
            config['XMPP'],
            [("/iq[@type='set']", self.__onIq), ],
            resource='ecm_agent-%d' % AGENT_VERSION_PROTOCOL)

    def _reconnect(self):
        """ 
        Disconnect the current reactor to try to connect again
        """
	log.info("No data received in %ss: Trying to reconnect" % KEEPALIVED_TIMEOUT)
        reactor.disconnectAll()	
            
    def __onIq(self, msg):
        """
        A new IQ message has been received and we should process it.
        """
        log.debug('__onIq')
        mem_clean('__onIq [start]')

        log.debug("q Message received: \n%s" % msg.toXml())
        log.debug("Message type: %s" % msg['type'])

        if self.keepalive.running:
            log.debug("Stop keepalived")
            self.keepalive.stop()
        
        log.debug("Starting keepalived")
        self.keepalive.start(KEEPALIVED_TIMEOUT, now=False)

        message = IqMessage(msg)
        recv_command = message.command.replace('.', '_')

        if recv_command in self.running_commands:
            if time() > self.running_commands[recv_command]:
                del self.running_commands[recv_command]
                self.num_running_commands -= 1
                log.debug("Deleted %s from running_commands dict as should have been completed" % (recv_command))

        if recv_command not in self.running_commands:
            log.debug('recieved new command: %s with message: %s' % (message.command, message))

            if hasattr(message, 'command') and hasattr(message, 'from_'):
                log.debug('online contacts: %s' % self._online_contacts)

                if message.from_ not in self._online_contacts:
                    log.warn('IQ sender not in roster (%s), dropping message' % message.from_)
                else:
                    self.running_commands[recv_command] = time() + int(message.command_args['timeout'])
                    self.num_running_commands += 1
                    log.debug("Running commands: names: %s numbers: %i" % (self.running_commands, self.num_running_commands))
                    self._processCommand(message)

            else:
                log.warn('Unknown ecm_message received: Full XML:\n%s' % (msg.toXml()))

            del message
        else:
            log.debug("already running given command %s" %recv_command)
            result = (_E_RUNNING_COMMAND, '', 'another command is running', 0)
            self._send(result, message)

        del msg
        mem_clean('__onIq [end]')

    def _processCommand(self, message):
        if not self.verify.signature(message):
            result = (_E_UNVERIFIED_COMMAND, '', 'Bad signature', 0)
            self._onCallFinished(result, message)
            return

        flush_callback = self._flush
        message.command_name = message.command.replace('.', '_')

        mem_clean('run_command [start]')
        d = self.command_runner.run_command(message, flush_callback)
        
        # Clean message
        message.command_args = {}

        if d:
            d.addCallbacks(self._onCallFinished, self._onCallFailed,
                           callbackKeywords={'message': message},
                           errbackKeywords={'message': message},
            )
            del message
            mem_clean('run_command [end]')
            return d

        else:
            log.info("Command Ignored: Unknown command: %s" % message.command)
            result = (_E_RUNNING_COMMAND, '', "Unknown command: %s" % message.command, 0)
            self._onCallFinished(result, message)

        del message
        mem_clean('run_command [end]')
        return
        
    def _onCallFinished(self, result, message):
        mem_clean('agent._onCallFinished')
        log.debug('Call Finished')
        self._send(result, message)
        del self.running_commands[message.command_name]
        self.num_running_commands -= 1
        log.debug('command finished %s' %message.command_name)

    def _onCallFailed(self, failure, *argv, **kwargs):
        log.error("onCallFailed")
        log.info(failure)

        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            del self.running_commands[message.command_name]
            self.num_running_commands -= 1
            self._onCallFinished(result, message)

    def _flush(self, result, message):
        log.debug('Flush Message')
        self._send(result, message)

    def _send(self, result, message):
        log.debug('Send Response')
        mem_clean('agent._send')
        message.toResult(*result)

        del result

        mem_clean('agent._send')
        self.send(message.toEtree())

    def _check_memory(self, num_running_commands):
        rss, vms = mem_usage()
        log.info("Current Memory usage: rss=%sMB | vms=%sMB" % (rss, vms))
        if not num_running_commands and rss > _CHECK_RAM_MAX_RSS_MB:
            log.critical("Max allowed RSS memory exceeded: %s MB, exiting."
                         % _CHECK_RAM_MAX_RSS_MB)
            reactor.stop()
