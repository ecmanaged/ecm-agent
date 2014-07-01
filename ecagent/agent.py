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

# Local
from ecagent.client import Client
from ecagent.runner import CommandRunner
from ecagent.message import IqMessage

import ecagent.twlogging as log
from ecagent.verify import ECVerify
from ecagent.functions import mem_clean

from message import AGENT_VERSION_PROTOCOL

_E_RUNNING_COMMAND = 253
_E_UNVERIFIED_COMMAND = 251


class SMAgent:
    def __init__(self, config):
        reactor.callWhenRunning(self._check_config)
        self.config = config

    def _check_config(self):
        d = self.config.check_uuid()
        d.addCallback(self._on_config_checked)
        d.addErrback(self._on_config_failed)

    def _on_config_checked(self, success):
        # Ok, now everything should be correctly configured,
        # let's start the party.
        if success:
            SMAgentXMPP(self.config)

    def _on_config_failed(self, failure):
        log.critical("Configuration check failed with: %s, exiting." % failure)
        log.critical("Please try configuring the XMPP subsystem manually.")
        reactor.stop()


class SMAgentXMPP(Client):
    def __init__(self, config):
        """
        XMPP agent class.
        """
        log.info("Starting agent...")
        
        log.info("Loading commands...")
        self.command_runner = CommandRunner(config['Plugins'])

        log.info("Setting up certificate")
        self.verify = ECVerify()

        log.debug("Loading XMPP...")
        Client.__init__(
            self,
            config['XMPP'],
            [('/iq', self.__onIq), ],
            resource='ecm_agent-%d' % AGENT_VERSION_PROTOCOL)
            
    def __onIq(self, msg):
        """
        A new IQ message has been received and we should process it.
        """
        log.debug('__onIq')
        mem_clean('__onIq [start]')

        log.debug("q Message received: \n%s" % msg.toXml())
        log.debug("Message type: %s" % msg['type'])

        if msg['type'] == 'set':
            message = IqMessage(msg)

            if hasattr(message, 'command') and hasattr(message, 'from_'):
                log.debug('online contacts: %s' % self._online_contacts)

                if message.from_ not in self._online_contacts:
                    log.warn('IQ sender not in roster (%s), dropping message' % message.from_)
                else:
                    self._processCommand(message)
            else:
                log.warn('Unknown ecm_message received: Full XML:\n%s' % (msg.toXml()))
                
            del message
            
        else:
            log.warn('Unknown IQ type received: Full XML:\n%s' % (msg.toXml()))

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

    def _onCallFailed(self, failure, *argv, **kwargs):
        log.error("onCallFailed")
        log.debug(failure)
        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            self._onCallFinished(result, message)

    def _flush(self, result, message):
        log.debug('Flush Message')
        self._send(result, message)

    def _send(self, result, message):
        log.debug('Send Response')
        mem_clean('agent._send')
        message.toResult(*result)
        mem_clean('agent._send')
        self.send(message.toEtree())
