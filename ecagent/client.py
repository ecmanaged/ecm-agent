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

import logging as log

# Twisted imports
from twisted.internet.defer import DeferredSemaphore
from twisted.words.xish.domish import Element

# Local
from core import BasicClient

XMPP_HOST = 'xmpp.ecmanaged.net'


class Client(BasicClient):
    def __init__(self, config, observers, resource='XMPPClient'):
        """
        XMPP Client class with ConfigObj, presence,
        concurrent message sending limit, and observers support.

        @param config: ConfigObj from where to read client settings.
        @param observers: Iterable of ("resource", callback') tuples.
        """
        my_observers = [
            ('/presence', self._onPresence),
            ('/iq', self._onPossibleErrorIq),
        ]
        my_observers.extend(observers)

        self._online_contacts = set()

        max_concurrent = 10
        if 'max_concurrent_messages' in config:
            max_concurrent = config.as_int('max_concurrent_messages')

        max_delay = 60
        if 'max_delay' in config:
            max_delay = self.cfg.as_int('max_delay')

        self._concurrency_semaphore = DeferredSemaphore(max_concurrent)
        self._my_full_jid = '/'.join((config['user'] + '@' + XMPP_HOST, resource))
        BasicClient.__init__(self,
                             config['user'] + '@' + XMPP_HOST,
                             config['password'],
                             XMPP_HOST,
                             my_observers,
                             resource=resource,
                             max_delay=max_delay,
        )

    def _onPossibleErrorIq(self, elem):
        if elem['type'] == "error":
            sender = elem['from']
            for el in elem.elements():
                if el.name == 'error' and el['code'] == '404':
                    log.warn('Received a 404 code from the server, setting the target user as offline')
                    if sender in self._online_contacts:
                        self._online_contacts.remove(sender)
                    else:
                        log.debug('Received a 404 from %s which not (anymore?) in the online contacts list.')

    def _onPresence(self, elem):
        """
        A new presence message has been received,
        let's see who has (dis)connected.
        """
        log.debug('_onPresence')
        presence = XMPPPresence(elem)
        if presence.available:
            log.debug("%s is now available" % presence.sender)
            #Store full jid.
            self._online_contacts.add(presence.sender)

        else:
            log.debug("%s is not available anymore" % presence.sender)
            if presence.jid in self._online_contacts:
                self._online_contacts.remove(presence.sender)

    def isOnline(self, jid):
        log.debug('isOnline "%s"' % jid)
        log.debug('current JIDS: %s' % self._online_contacts)
        if jid in self._online_contacts:
            return True
        return False


class XMPPPresence:
    def __init__(self, elem=None):
        if elem:
            self.sender = elem['from']
            sp = self.sender.split("/")
            self.jid = sp[0]
            if len(sp) > 1:
                self.sender_resource = sp[-1]
            else:
                self.sender_resource = "[[UNSPECIFIED]]"

            if elem.hasAttribute('type'):
                self.status = elem['type']
            else:
                self.status = 'available'

            if self.status == 'available':
                self.available = True
            else:
                self.available = False
        else:
            self.sender = None
            self.status = "available"
            self.priority = 4

    def toEtree(self):
        log.debug('XMPPPresence.toEtree')
        msg = Element(('jabber:client', 'presence'))
        msg.addElement('status', content=self.status)
        msg.addElement('priority', content=str(self.priority))
        return msg
