# -*- coding:utf-8 -*-

#Twisted
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessTerminated, ProcessDone
from twisted.words.xish.domish import Element

##Local
from ecm_agent.client import Client
import ecm_agent.twlogging as l

#Python
import os
import sys
from platform import system
import simplejson as json
import zlib, base64
from time import time

## RSA Verify
from Crypto import PublicKey
import Crypto.PublicKey.RSA
from Crypto.Util import number
from Crypto.Hash import SHA

E_RUNNING_COMMAND = 253
E_COMMAND_NOT_DEFINED = 252
E_UNVERIFIED_COMMAND = 251
STDOUT_FINAL_OUTPUT_STR = '[__ecagent::response__]'

PUB_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDYOveXRwvarfanocPyjMEdyP9v
WqPpBn/xmowk+Hwrp1rN5UCYESYbVQx8zUEXxK6euOl7ayW2x1X/GJkFsiRvW0Ev
+OvTm//m44JbLKz6ehPuuUzvlP8ujMLgo9ncTlsXO5/WL/Cy/EvE6dfDdRR4977M
IqlNJia2BUKKDa1EuQIDAQAB
-----END PUBLIC KEY-----"""

AGENT_VERSION = 1
FLUSH_MIN_LENGTH = 5
FLUSH_TIME = 5

class SMAgent:
    def __init__(self, config):
        reactor.callWhenRunning(self._checkConfig)
        self.config = config

    def _checkConfig(self):
        d = self.config.checkUUID()
        d.addCallback(self._onConfigChecked)
        d.addErrback(self._onConfigCheckFailed)

    def _onConfigChecked(self, success):
        #Ok, now everything should be correctly configured,
        #let's start the party.
        if success:
            SMAgentXMPP(self.config)

    def _onConfigCheckFailed(self, failure):
        l.critical("Configuration check failed with: %s, exiting." % failure)
        l.critical("Please try configuring the XMPP subsystem manually.")
        reactor.stop()

class SMAgentXMPP(Client):
    def __init__(self, config):
        """
        XMPP agent class.
        """
        l.info("Starting agent...")
        self.config = config

        l.debug("Loading XMPP...")
        observers = [
            ('/iq', self.__onIq),
            ]
        Client.__init__(self,
                        self.config['XMPP'],
                        observers,
                        resource='ecm_agent-%d' % AGENT_VERSION
        )

        l.info("Loading commands...")
        self.command_runner = CommandRunner(config['Plugins'])

    def __onIq(self, msg):
        """
        A new IQ message has been received and we should process it.
        """
        l.debug('__onIq')
        message_type = msg['type']

        l.debug("q Message received: \n%s" % msg.toXml())
        l.debug("Message type: %s" % message_type)

        if message_type == 'set':
            #Parse and check message format
            message = IqMessage(msg)

            if hasattr(message, 'command') and hasattr(message, 'from_'):

                l.debug('online contacts: %s' % self._online_contacts)
                #l.debug("command: \n%s" % message.command)

                if message.from_ not in self._online_contacts:
                    l.warn('IQ sender not in roster (%s), dropping message'
                           % message.from_)
                else:
                    l.debug('Processing command...')
                    self._processCommand(message)
            else:
                l.warn('Unknown ecm_message received: "%s" Full XML:\n%s'
                       % (message_type, msg.toXml()))
        else:
            l.warn('Unknown IQ type received: "%s" Full XML:\n%s'
                   % (message_type, msg.toXml()))

    def _processCommand(self, message):
        l.debug('Process Command')

        if not self._verify_message(message):
            l.info('Command from %s has bad signature (Ignored)' % message.from_)
            result=(E_UNVERIFIED_COMMAND, '', 'Bad signature', 0)
            self._onCallFinished(result,message)
            return

        l.info('Command from %s is RSA verified' % message.from_)

        flush_callback = self._Flush
        message.command_replaced = message.command.replace('.','_')
        d = self.command_runner.runCommand(message.command_replaced, message.command_args, flush_callback, message)
        if d:
            d.addCallbacks(self._onCallFinished, self._onCallFailed,
                           callbackKeywords={'message': message},
                           errbackKeywords={'message': message},
                           )
            return d

        else:
            l.debug('Command Ignored: Unknown command')
            result=(E_RUNNING_COMMAND, '', 'Unknown command', 0)
            self._onCallFinished(result,message)

        return

    def _onCallFinished(self, result, message):
        l.debug('Call Finished')
        self._send(result,message)

    def _Flush(self, result, message):
        l.debug('Flush Message')
        self._send(result,message)

    def _onCallFailed(self, failure, *argv, **kwargs):
        l.error("onCallFailed")
        l.debug(failure)
        if 'message' in kwargs:
            message = kwargs['message']
            result = (2, '', failure, 0)
            self._onCallFinished(result,message)

    def _send(self, result, message):
        l.debug('Send Response')
        message.toResult(*result)
        self.send(message.toEtree())

    def _verify_message(self,message):
        l.debug('Verify Message')

        args_encoded = ''
        for arg in sorted(message.command_args.keys()):
            args_encoded += arg + ':' + message.command_args[arg] + ':'

        text = message.from_.split('/')[0] + '::' +\
               message.to.split('/')[0] + '::' +\
               message.command + '::' +\
               args_encoded

        return self._rsa_verify(text,message.signature)

    def _rsa_verify(self,text,signature):
        def _emsa_pkcs1_v1_5_encode(M, emLen):
            # for PKCS1_V1_5 signing:
            SHA1DER = '\x30\x21\x30\x09\x06\x05\x2b\x0e\x03\x02\x1a\x05\x00\x04\x14'
            SHA1DERLEN = len(SHA1DER) + 0x14

            H = SHA.new(M).digest()
            T = SHA1DER + H
            if emLen < (SHA1DERLEN + 11):
                l.error('[CRYPT] intended encoded message length too short (%s)' % emLen)
                return
            ps = '\xff' * (emLen - SHA1DERLEN - 3)
            if len(ps) < 8:
                l.error('[CRYPT] ps length too short')
                return
            return '\x00\x01' + ps + '\x00' + T

        key = PublicKey.RSA.importKey(PUB_KEY)
        pub = key.publickey()

        signature = base64.b64decode(signature)
        em = _emsa_pkcs1_v1_5_encode(text, len(signature))

        if em:
            signature = number.bytes_to_long(signature)
            return pub.verify(em, (signature,))

        return False

class CommandRunner():
    def __init__(self, config):
        self.command_paths = [os.path.join(os.path.dirname(__file__),
                                           '..', 'plugins')]  # Built-in commands (absolute path)
        if 'plugin_paths' in config:
            self.command_paths.extend(config['plugin_paths'])

        if system() == "Windows":
            self._python_runner = config['python_interpreter_windows']
        else:
            self._python_runner = config['python_interpreter_linux']

        self.timeout = int(config['timeout'])
        self.env = os.environ
        self.env['PYTHONPATH'] = os.path.dirname(__file__)
        self.env['LANG']='en_US.utf8'
        self.env['PWD']='/root/'

        l.debug("ENV: %s" % self.env)
        reactor.callLater(0, self._loadCommands)

    def _loadCommands(self):
        self._commands = {}
        for path in self.command_paths:
            l.debug("Processing dir: %s" % path)
            try:
                if os.path.isdir(path):
                    for filename in os.listdir(path):
                        l.debug("  Queuing plugin %s for process." % filename)
                        full_filename = os.path.join(path, filename)
                        d = self._runProcess(full_filename, '', [])
                        d.addCallback(self._addCommand, filename=full_filename)
            except:
                print sys.exc_info()

    def _addCommand(self, data, **kwargs):
        (exit_code, stdout, stderr, timeout_called) = data

        if exit_code == 0:
            for line in stdout.splitlines():
                self._commands[line.split()[0]] = kwargs['filename']
                l.debug("Command %s added" % line.split()[0])
        else:
            l.error('Error adding commands from %s: %s'
                    % (kwargs['filename'], data))

    def runCommand(self, command, command_args, flush_callback = None, message = None):
        if (command in self._commands):
            l.debug("executing %s with args: %s" % (command, command_args))
            return self._runProcess(self._commands[command], command, command_args, flush_callback, message)
        return

    def _runProcess(self, filename, command_name, command_args, flush_callback=None, message=None):
        ext = os.path.splitext(filename)[1]
        if ext in ('.py', '.pyw', '.pyc'):
            command = self._python_runner
            # -u: sets unbuffered output
            args = [command, '-u', filename, command_name]
        else:
            command = filename
            args = [command, command_name]

        # Set timeout from command
        cmd_timeout = self.timeout
        if 'timeout' in command_args:
            cmd_timeout = int(command_args['timeout'])

        l.info("running %s from %s (%i)" % (command_name, filename, cmd_timeout))
        crp = CommandRunnerProcess(cmd_timeout, command_args, flush_callback, message)
        d = crp.getDeferredResult()
        reactor.spawnProcess(crp, command, args, env=self.env)
        return d

class CommandRunnerProcess(ProcessProtocol):
    def __init__(self, timeout, command_args, flush_callback = None, message=None):
        self.stdout = ""
        self.stderr = ""
        self.deferreds = []
        self.timeout = timeout
        self.command_args = command_args
        self.last_send_data_size = 0
        self.last_send_data_time = time()
        self.flush_callback = flush_callback
        self.flush_later = None
        self.message = message

    def connectionMade(self):
        l.debug("Process started.")
        self.timeout_dc = reactor.callLater(self.timeout,
                                            self.transport.signalProcess, 'KILL')
        #Pass the call arguments via stdin in json format so we can
        #pass binary data or whatever we want.
        self.transport.write(base64.b64encode(json.dumps(self.command_args)))

        #And close stdin to signal we are done writing args.
        self.transport.closeStdin()

    def outReceived(self, data):
        l.debug("Out made: %s" % data)

        if STDOUT_FINAL_OUTPUT_STR in data:
            for line in data.split("\n"):
                if line == STDOUT_FINAL_OUTPUT_STR:
                    self.stdout = ''
                    self.stderr = ''
                    self.flush_callback = None

                else:
                    self.stdout += line
        else:
            self.stdout += data

        self._flush()

    def errReceived(self, data):
        l.debug("Err made: %s" % data)
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

                l.debug("Scheduling a flush response: %s" %self.stdout)
                self.flush_later = reactor.callLater(1,self.flush_callback,(None, self.stdout, self.stderr, 0, total_out), self.message)

    def processEnded(self, status):
        l.debug("Process ended")
        self.flush_callback = None

        # Cancel flush callbacks
        self.flush_callback = None
        if self.flush_later:
            try: self.flush_later.cancel()
            except: pass

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
    <iq xmlns='jabber:client' to='ecm_agent@ejabberd/ecm_agent-1'
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

                if(int(self.version) > AGENT_VERSION):
                    raise Exception("Message format  (%s) is greater than supported version (%s)" % (self.version, AGENT_VERSION))

                self.type = elem['type']
                self.id = elem['id']
                self.to = elem['to']
                self.from_ = elem['from']
                self.resource = elem['to'].split("/")

                if len(self.resource) > 1:
                    self.resource = self.resource[-1]
                else:
                    self.resource= None

                el_command      = el_ecm_message.firstChildElement()
                self.command    = el_command['name']

                el_args = el_command.firstChildElement()
                self.command_args = el_args.attributes

                self.signature = el_command['signature']

            except Exception as e:
                l.error("Error parsing IQ message: %s" % elem.toXml())
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
            ecm_message['version'] = str(AGENT_VERSION)
            ecm_message['command'] = self.command

            result = ecm_message.addElement('result')
            result['retvalue']  = self.retvalue
            result['timed_out'] = self.timed_out
            result['partial']   = self.partial

            result.addElement('gzip_stdout').addContent(base64.b64encode(zlib.compress(self.stdout)))
            result.addElement('gzip_stderr').addContent(base64.b64encode(zlib.compress(self.stderr)))

        return msg

    def toXml(self):
        return self.toEtree().toXml()

    def toResult(self, retvalue, stdout, stderr, timed_out, partial=0):
        """
        Converts a query message to a result message.
        """

        # Don't switch to/from if already is a result
        if self.type != 'result':
            self.from_, self.to = self.to, self.from_

        self.type = 'result'
        self.retvalue  = str(retvalue)
        self.stdout    = str(stdout)
        self.stderr    = str(stderr)
        self.timed_out = str(timed_out)
        self.partial   = str(partial)
