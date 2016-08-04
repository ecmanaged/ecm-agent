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

_FINAL_OUTPUT_STRING = '[__response__]'

FLUSH_MIN_LENGTH = 5
FLUSH_TIME = 5

PYTHON_LINUX = '/usr/bin/python'
PYTHON_WINDOWS = '../python27/pythonw.exe'
TIMEOUT = 300

# System imports
import os
import sys
import base64
import simplejson as json
from time import time

# Twisted imports
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessTerminated, ProcessDone

import core.logging as log

class CommandRunner():
    def __init__(self):
        if sys.platform.startswith("win32"):
            self._python_runner = PYTHON_WINDOWS
            self.command_paths = [
                os.path.join(os.path.dirname(__file__), '../../..')]  # Built-in commands (on root dir)

        else:
            self._python_runner = PYTHON_LINUX
            self.command_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'plugins')]  # Built-in commands (absolute path)

        self.timeout_dc = None

        self.env = os.environ
        self.env['DEBIAN_FRONTEND'] = 'noninteractive'
        self.env['LANG'] = 'en_US.utf8'
        self.env['PWD'] = '/root/'

        log.debug("ENV: %s" % self.env)

        self._commands = {}
        reactor.callWhenRunning(self._load_commands)

    def _load_commands(self):
        for path in self.command_paths:
            log.debug("Processing dir: %s" % path)
            try:
                if os.path.isdir(path):
                    for filename in os.listdir(path):
                        if not filename.startswith('plugin_'):
                            continue

                        if os.path.splitext(filename)[1] not in ['.py','.exe']:
                            continue

                        log.debug("  Queuing plugin %s for process." % filename)
                        full_filename = os.path.join(path, filename)
                        d = self._run_process(full_filename, '', {})
                        d.addCallback(self._add_command, filename=full_filename)
            except:
                print sys.exc_info()

    def _add_command(self, data, **kwargs):
        (exit_code, stdout, stderr, timeout_called) = data

        if exit_code == 0:
            for line in stdout.splitlines():
                self._commands[line.split()[0]] = kwargs['filename']
                log.debug("Command %s added" % line.split()[0])

        else:
            log.error('Error adding commands from %s: %s' % (kwargs['filename'], data))

        del exit_code, stdout, stderr, timeout_called, data

    def run_command(self, message, flush_callback=None):
        if self._commands.get(message.command_name):
            log.debug("executing %s with args: %s" % (message.command_name, message.command_args))
            return self._run_process(self._commands[message.command_name], message.command_name, message.command_args, flush_callback, message)

        return

    def _run_process(self, filename, command_name, command_args, flush_callback=None, message=None):
        #log.info("filename: %s command_name: %s command_args: %s flush_callback: %s message: %s" % (filename, command_name, command_args, flush_callback, message))
        need_sudo = ['plugin_pip.py', 'plugin_service.py', 'plugin_update.py', 'plugin_haproxy.py', 'plugin_monitor.py', 'plugin_pip_extra.py', 'plugin_puppet.py', 'plugin_saltstack.py', 'plugin_proc.py']
        ext = os.path.splitext(filename)[1]
        if ext == '.py':
            from sys import platform
            if platform.startswith("win32") or os.path.split(filename)[1] not in need_sudo:
                command = self._python_runner
                args = [command, '-u', '-W ignore::DeprecationWarning', filename, command_name]

            else:
                command = 'sudo'
                # -u: sets unbuffered output
                args = [command, self._python_runner, '-u', '-W ignore::DeprecationWarning', filename, command_name]

        else:
            command = filename
            args = [command, command_name]

        # :TODO Set timeout from command
        #log.info('in the runner.py _run_process %s %s' %(command_args,type(command_args)))
        cmd_timeout = int(command_args.get('timeout',TIMEOUT))

        if command_name:
            log.info("Running %s from %s (timeout: %i)" % (command_name, filename, cmd_timeout))

        else:
            log.info("[INIT] Loading commands from %s" % filename)

        crp = CommandRunnerProcess(cmd_timeout, command_args, flush_callback, message)
        d = crp.getDeferredResult()
        reactor.spawnProcess(crp, command, args, env=self.env)

        del cmd_timeout, filename, command_name, command_args
        del flush_callback, message, args

        return d


class CommandRunnerProcess(ProcessProtocol):
    def __init__(self, timeout, command_args, flush_callback=None, message=None):
        self.stdout = ""
        self.stderr = ""
        self.deferreds = []
        self.timeout = timeout
        self.command_args = command_args

        self.last_send_data_size = 0
        self.last_send_data_time = time()
        self.flush_callback = flush_callback
        self.flush_later = None
        self.flush_later_forced = None
        self.message = message

        del timeout
        del command_args
        del flush_callback
        del message

    def connectionMade(self):
        log.debug("Process started.")
        self.pid = self.transport.pid
        self.timeout_dc = reactor.callLater(self.timeout, self.transport.signalProcess, 'KILL')

        # Pass the call arguments via stdin in json format
        self.transport.write(base64.b64encode(json.dumps(self.command_args)))

        # And close stdin to signal we are done writing args.
        self.transport.closeStdin()

    def outReceived(self, data):
        log.debug("Out made: %s" % data)

        if _FINAL_OUTPUT_STRING in data:
            for line in data.split("\n"):
                if _FINAL_OUTPUT_STRING in line:
                    # Skip this line and stop flush callback
                    self.stdout = self.stderr = ''
                    self.flush_callback = None

                else:
                    self.stdout += line
        else:
            self.stdout += data
        del data
        self._flush()

    def errReceived(self, data):
        log.debug("Err made: %s" % data)
        self.stderr += data
        del data
        self._flush()

    def _flush(self):
        if not self.flush_callback:
            return

        total_out = len(self.stdout) + len(self.stderr)

        if total_out - self.last_send_data_size > FLUSH_MIN_LENGTH:
            curr_time = time()
            if self.last_send_data_time + FLUSH_TIME < curr_time:
                self.last_send_data_size = total_out
                self.last_send_data_time = curr_time

                log.debug("Scheduling a flush response: %s" % self.stdout)
                self._cancel_flush(self.flush_later_forced)
                self.flush_later = reactor.callLater(1, self.flush_callback,
                                                     (None, self.stdout, self.stderr, 0, total_out), self.message)

        if not self.flush_later:
            self._cancel_flush(self.flush_later_forced)
            self.flush_later_forced = reactor.callLater(FLUSH_TIME, self.flush_callback,
                                                        (None, self.stdout, self.stderr, 0, total_out), self.message)

        del total_out

    def processEnded(self, status):
        log.debug("Process ended")
        self.flush_callback = None

        # Cancel flush callbacks
        self.flush_callback = None
        self._cancel_flush(self.flush_later)
        self._cancel_flush(self.flush_later_forced)

        # Get command retval
        t = type(status.value)
        if t is ProcessDone:
            exit_code = 0

        elif t is ProcessTerminated:
            exit_code = status.value.exitCode

        else:
            raise status

        if not self.timeout_dc.called:
            self.timeout_dc.cancel()

        for d in self.deferreds:
            d.callback((exit_code, self.stdout, self.stderr,
                        self.timeout_dc.called))

    def getDeferredResult(self):
        d = Deferred()
        self.deferreds.append(d)

        return d

    @staticmethod
    def _cancel_flush(flush_reactor):
        if flush_reactor:
            try:
                flush_reactor.cancel()

            except:
                pass
