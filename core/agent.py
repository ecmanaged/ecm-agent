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
import base64
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from StringIO import StringIO

from twisted.web.client import FileBodyProducer
#from twisted.web.client import readBody

# Local
from core.runner import CommandRunner
from core.message import ECMessage

import core.logging as log

import urllib
import urllib2
import json

from core.functions import mem_clean

from message import AGENT_VERSION_PROTOCOL

_E_RUNNING_COMMAND = 253
_E_UNVERIFIED_COMMAND = 251

_CHECK_RAM_MAX_RSS_MB = 125
_CHECK_RAM_INTERVAL = 60

KEEPALIVED_TIMEOUT = 180

MAIN_LOOP_TIME = 15
SYSTEM_LOOP_TIME = 15

ECMANAGED_URL_TASK = 'http://my-devel1.ecmanaged.com/agent/meta-data/task'
ECMANAGED_URL_RESULT = 'http://my-devel1.ecmanaged.com/agent/meta-data/result'
#url = 'http://localhost:5000/agent/' + self.uuid + '/tasks'

class ECMAuth:
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
        XMPP agent class.
        """
        self.ecAgent = Agent(reactor)
        self.uuid = config['Auth']['uuid']
        self.token = config['Auth']['token']

        log.info("Loading Commands...")
        self.command_runner = CommandRunner()

        log.info("Setting up Memory checker")
        self.memory_checker = LoopingCall(self._check_memory)
        self.memory_checker.start(_CHECK_RAM_INTERVAL)

        log.info("Starting main loop")
        self.periodic_info = LoopingCall(self._main)
        self.periodic_info.start(MAIN_LOOP_TIME, now=True)

    def _main(self):
        '''
        send periodic health info to the backend
        :return:
        '''

        content = self._url_post(ECMANAGED_URL_TASK + '/' + self.uuid)
        log.debug("received: %s" % content)

        for task in content:
            #log.info('task %s %s %s %s' %(task['id'], task['type'], task['command'], task['command_args']))
            #log.info('task %s %s %s %s' %(type(task['id']), type(task['type']), type(task['command']), type(task['command_args'])))
            try:
                message = ECMessage(task['id'], task['type'], task['command'], task['command_args'])

            except Exception, e:
                log.info('error in main loop while generating message for task : %s' %str(e))
            #log.info('after converting to message:   %s %s %s %s ' %(message.id, message.type, message.command, message.command_args))

            try:
                self._run_task(message)
                
            except Exception, e:
                log.info('error in main loop while running task : %s' % str(e))
                
    def _url_post(self, url, post_data={}):
        content = []
        headers = {
            'Content-Type': 'application/json', 
            'x-ecmanaged-token': 'Basic %s' % self.token,
            }

        try:
            req = urllib2.Request(url, json.dumps(post_data), headers)
            urlopen = urllib2.urlopen(req)
            content = ''.join(urlopen.readlines())
            content = json.loads(content)
            
        except Exception, e:
            log.info('_url_post failed %s' % str(e))

        return content

    def _run_task(self, message):
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
        log.info('send result for %s %s' %(message.type, message.command))

        url = 'http://localhost:5000/agent/'+self.username+'/result'
        data = {}
        data['result']= result
        authString = base64.encodestring('%s:%s' % (self.username, self.password))
        headers = {"Content-Type": "application/json", "Authorization":"Basic %s" % authString}

        #log.info('posting data %s' %data)

        try:
            req = urllib2.Request(url, urllib.urlencode(data), headers)
            urlopen = urllib2.urlopen(req)
            content = ''.join(urlopen.readlines())
            log.info(' %s' %str(content))
        except Exception, e:
            log.info('error in while sending result %s' % str(e))

    def _check_memory(self):
        rss = mem_clean('periodic memory clean')
        if rss > _CHECK_RAM_MAX_RSS_MB:
            log.critical("Max allowed RSS memory exceeded: %s MB, exiting."
                         % _CHECK_RAM_MAX_RSS_MB)
            reactor.stop()
        del rss
