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

# System imports
import zlib
import base64

# Twisted imports
from twisted.words.xish.domish import Element

# Local
import ecagent.twlogging as log

AGENT_VERSION_CORE = 3
AGENT_VERSION_PROTOCOL = 1


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

            except Exception:
                log.error("Error parsing IQ message: %s" % elem.toXml())
                pass

        else:
            self.type = ''
            self.id = ''
            self.from_ = ''
            self.to = ''
            self.resource = ''

        # Clean
        del elem

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
            del ecm_message

        return msg

    def toXml(self):
        return self.toXml()

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
        self.command_args = {}

        del retvalue, stdout, stderr, timed_out, partial

