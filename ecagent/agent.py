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

import os
import sys
import zlib
import base64
import simplejson as json
from time import time

# Twisted imports
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessTerminated, ProcessDone
from twisted.words.xish.domish import Element

# Local
from ecagent.client import Client
import ecagent.twlogging as log

## RSA Verify
try:
    from Crypto import PublicKey
    import Crypto.PublicKey.RSA
    from Crypto.Util import number
    from Crypto.Hash import SHA
except:
    pass

_CERTIFICATE_FILE = '../config/xmpp_cert.pub'

_E_RUNNING_COMMAND = 253
_E_COMMAND_NOT_DEFINED = 252
_E_UNVERIFIED_COMMAND = 251

_FINAL_OUTPUT_STRING = '[__response__]'

AGENT_VERSION_CORE = 2
AGENT_VERSION_PROTOCOL = 1

FLUSH_MIN_LENGTH = 5
FLUSH_TIME = 5

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
        self.config = config

        log.info("Setting up certificate")
        self.public_key = None
        try:
            if Crypto.version_info[:2] >= (2, 2):
                _public_key = self._read_pub_key()
                if _public_key:
                    key = PublicKey.RSA.importKey(_public_key)
                    self.public_key = key.publickey()
        except:
            pass

        if not self.public_key:
            log.warn('PyCrypto not available or version is < 2.2: Please upgrade: http://www.pycrypto.org/')

        log.info("Loading commands...")
        self.command_runner = CommandRunner(config['Plugins'])

        log.debug("Loading XMPP...")
        Client.__init__(
            self,
            self.config['XMPP'],
            [('/iq', self.__onIq), ],
            resource='ecm_agent-%d' % AGENT_VERSION_PROTOCOL)

    def __onIq(self, msg):
        """
        A new IQ message has been received and we should process it.
        """
        log.debug('__onIq')
        message_type = msg['type']

        log.debug("q Message received: \n%s" % msg.toXml())
        log.debug("Message type: %s" % message_type)

        if message_type == 'set':
            #Parse and check message format
            message = IqMessage(msg)

            if hasattr(message, 'command') and hasattr(message, 'from_'):
                log.debug('online contacts: %s' % self._online_contacts)

                if message.from_ not in self._online_contacts:
                    log.warn('IQ sender not in roster (%s), dropping message'
                           % message.from_)
                else:
                    self._processCommand(message)
            else:
                log.warn('Unknown ecm_message received: "%s" Full XML:\n%s'
                       % (message_type, msg.toXml()))
        else:
            log.warn('Unknown IQ type received: "%s" Full XML:\n%s'
                   % (message_type, msg.toXml()))

    def _processCommand(self, message):
        log.debug('Process Command')

        if self.public_key:
            if not self._verify_message(message):
                log.critical('[RSA CHECK: Failed] Command from %s has bad signature (Ignored)' % message.from_)
                result = (_E_UNVERIFIED_COMMAND, '', 'Bad signature', 0)
                self._onCallFinished(result, message)
                return
        else:
            # No public key, RSA functions are not available on this system
            log.warn('[RSA CHECK: No available] WARNING: Running unverified Command from %s' % message.from_)

        flush_callback = self._Flush
        message.command_replaced = message.command.replace('.', '_')
        d = self.command_runner.run_command(message.command_replaced, message.command_args, flush_callback, message)

        if d:
            d.addCallbacks(self._onCallFinished, self._onCallFailed,
                           callbackKeywords={'message': message},
                           errbackKeywords={'message': message},
            )
            return d

        else:
            log.info("Command Ignored: Unknown command: %s" % message.command)
            result = (_E_RUNNING_COMMAND, '', "Unknown command: %s" % message.command, 0)
            self._onCallFinished(result, message)

        return

    def _onCallFinished(self, result, message):
        log.debug('Call Finished')
        self._send(result, message)

    def _Flush(self, result, message):
        log.debug('Flush Message')
        self._send(result, message)

    def _onCallFailed(self, failure, *argv, **kwargs):
        log.error("onCallFailed")
        log.debug(failure)
        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            self._onCallFinished(result, message)

    def _send(self, result, message):
        log.debug('Send Response')
        message.toResult(*result)
        self.send(message.toEtree())

    def _read_pub_key(self):
        log.debug('Reading public certificate')
        public_key = None
        try:
            cert_file = os.path.join(os.path.dirname(__file__), _CERTIFICATE_FILE)
            if os.path.isfile(cert_file):
                f = open(cert_file, 'r')
                public_key = f.read()
                f.close()
        except:
            log.critical("Unable to read certificate file")

        return public_key

    def _verify_message(self, message):
        args_encoded = ''
        for arg in sorted(message.command_args.keys()):
            args_encoded += arg + ':' + message.command_args[arg] + ':'

        text = message.from_.split('/')[0] + '::' + \
               message.to.split('/')[0] + '::' + \
               message.command + '::' + \
               args_encoded

        return self._rsa_verify(text, message.signature, message.command, message.from_)

    def _rsa_verify(self, text, signature, command, sender):
        def _emsa_pkcs1_v1_5_encode(M, emLen):
            # for PKCS1_V1_5 signing:
            SHA1DER = '\x30\x21\x30\x09\x06\x05\x2b\x0e\x03\x02\x1a\x05\x00\x04\x14'
            SHA1DERLEN = len(SHA1DER) + 0x14

            H = SHA.new(M).digest()
            T = SHA1DER + H
            if emLen < (SHA1DERLEN + 11):
                log.error('[RSA CHECK: Error] intended encoded message length too short (%s)' % emLen)
                return
            ps = '\xff' * (emLen - SHA1DERLEN - 3)
            if len(ps) < 8:
                log.error('[RSA CHECK: Error] ps length too short')
                return
            return '\x00\x01' + ps + '\x00' + T

        signature = base64.b64decode(signature)
        em = _emsa_pkcs1_v1_5_encode(text, len(signature))

        if em:
            signature = number.bytes_to_long(signature)
            if self.public_key.verify(em, (signature,)):
                log.info("[RSA CHECK: OK] command: %s - from: %s" % (command, sender))
                return True

        log.error("[RSA CHECK: Error] %s - from: %s" % (command, sender))
        return False


class CommandRunner():
    def __init__(self, config):
        if sys.platform.startswith("win32"):
            self._python_runner = config['python_interpreter_windows']
            self.command_paths = [
                os.path.join(os.path.dirname(__file__), '../../..')]  # Built-in commands (on root dir)
            tools_path = config.get('tools_path_windows')

        else:
            self._python_runner = config['python_interpreter_linux']
            self.command_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'plugins')]  # Built-in commands (absolute path)
            tools_path = config.get('tools_path_linux')

        self.timeout = int(config['timeout'])
        self.timeout_dc = None

        self.env = os.environ
        self.env['DEBIAN_FRONTEND'] = 'noninteractive'
        self.env['PYTHONPATH'] = os.path.dirname(__file__)
        self.env['LANG'] = 'en_US.utf8'
        self.env['PWD'] = '/root/'

        if tools_path:
            self.env["PATH"] += os.pathsep + tools_path

        log.debug("ENV: %s" % self.env)
        #reactor.callLater(0, self._loadCommands)
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

                        log.debug("  Queuing plugin %s for process." % filename)
                        full_filename = os.path.join(path, filename)
                        d = self._run_process(full_filename, '', [])
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
            log.error('Error adding commands from %s: %s'
                    % (kwargs['filename'], data))

    def run_command(self, command, command_args, flush_callback=None, message=None):
        if command in self._commands:
            log.debug("executing %s with args: %s" % (command, command_args))
            return self._run_process(self._commands[command], command, command_args, flush_callback, message)
        return

    def _run_process(self, filename, command_name, command_args, flush_callback=None, message=None):
        ext = os.path.splitext(filename)[1]
        if ext in ('.py', '.pyw', '.pyc'):
            command = self._python_runner

            # -u: sets unbuffered output
            args = [command, '-u', '-W ignore::DeprecationWarning', filename, command_name]

        else:
            command = filename
            args = [command, command_name]

        # Set timeout from command
        cmd_timeout = self.timeout
        if 'timeout' in command_args:
            cmd_timeout = int(command_args['timeout'])

        if command_name:
            log.info("Running %s from %s (timeout: %i)" % (command_name, filename, cmd_timeout))

        else:
            log.info("[INIT] Loading commands from %s" % filename)

        crp = CommandRunnerProcess(cmd_timeout, command_args, flush_callback, message)
        d = crp.getDeferredResult()
        reactor.spawnProcess(crp, command, args, env=self.env)

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

    def connectionMade(self):
        log.debug("Process started.")
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

        self._flush()

    def errReceived(self, data):
        log.debug("Err made: %s" % data)
        self.stderr += data
        self._flush()

    def _flush(self):
        if not self.flush_callback: return
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

    def _cancel_flush(self, flush_reactor):
        if flush_reactor:
            try:
                flush_reactor.cancel()

            except:
                pass

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


class IqMessage:
    """
    Received IQs parser and validator.
    Error parsing the message (or unsupported version number)
    Will raise an Exception.

    MESSAGE FORMAT EXAMPLE:
    <iq xmlns='jabber:client' to='ecagent@ejabberd/ecagent-1'
    from='tester@ejabberd/test_send' id='s2c1' type='set'>
        <ecm_message version="1">
            <command name="command1" time="123131231" signature="XXXX">
                <args name1="value1" name2="value2" />
            </command>
        </ecm_message>
    </iq>

    """

    def __init__(self, elem=None):
        if elem:
            try:
                if elem.name != 'iq':
                    raise Exception("Message is not an IQ")

                el_ecm_message = elem.firstChildElement()
                self.version = el_ecm_message['version']

                if int(self.version) > AGENT_VERSION_PROTOCOL:
                    raise Exception(
                        "Message format (%s) is greater than supported version (%s)" % (self.version, AGENT_VERSION_PROTOCOL))

                self.type = elem['type']
                self.id = elem['id']
                self.to = elem['to']
                self.from_ = elem['from']
                self.resource = elem['to'].split("/")

                if len(self.resource) > 1:
                    self.resource = self.resource[-1]

                else:
                    self.resource = None

                el_command = el_ecm_message.firstChildElement()
                self.command = el_command['name']

                el_args = el_command.firstChildElement()
                self.command_args = el_args.attributes

                self.signature = el_command['signature']

            except Exception as e:
                log.error("Error parsing IQ message: %s" % elem.toXml())
                pass

        else:
            self.type = ''
            self.id = ''
            self.from_ = ''
            self.to = ''
            self.resource = ''

    def toEtree(self):
        msg = Element(('jabber:client', 'iq'))
        msg['type'] = self.type
        msg['id'] = self.id
        msg['from'] = self.from_
        msg['to'] = self.to

        if self.type == 'result':
            ecm_message = msg.addElement('ecm_message')
            ecm_message['version'] = str(AGENT_VERSION_PROTOCOL)
            ecm_message['core'] = str(AGENT_VERSION_CORE)
            ecm_message['command'] = self.command
            ecm_message['signature'] = self.signature

            result = ecm_message.addElement('result')
            result['retvalue'] = self.retvalue
            result['timed_out'] = self.timed_out
            result['partial'] = self.partial

            # compress out
            result.addElement('gzip_stdout').addContent(base64.b64encode(zlib.compress(self.stdout)))
            result.addElement('gzip_stderr').addContent(base64.b64encode(zlib.compress(self.stderr)))

        return msg

    def toXml(self):
        return self.toEtree().toXml()

    def toResult(self, retvalue, stdout, stderr, timed_out, partial=0):
        """ Converts a query message to a result message. """
        # Don't switch to/from if already is a result
        if self.type != 'result':
            self.from_, self.to = self.to, self.from_
            self.type = 'result'

        self.retvalue = str(retvalue)
        self.stdout = str(stdout)
        self.stderr = str(stderr)
        self.timed_out = str(timed_out)
        self.partial = str(partial)
