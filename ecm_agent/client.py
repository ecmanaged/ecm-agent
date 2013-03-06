# -*- coding:utf-8 -*-

#Twisted
from twisted.internet.defer import DeferredSemaphore
from twisted.words.xish.domish import Element

#Python
import logging as l

#Local
from core import BasicClient

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

        if 'max_concurrent_messages' in config:
            max = config.as_int('max_concurrent_messages')
        else:
            max = 10
        self._concurrency_semaphore = DeferredSemaphore(max)

        if 'max_delay' in config:
            max_delay = self.cfg.as_int('max_delay')
        else:
            max_delay = 60

        self._my_full_jid = '/'.join((config['user'], resource))

        BasicClient.__init__(self,
                            config['user'],
                            config['password'],
                            config['host'],
                            my_observers,
                            resource=resource,
                            max_delay=max_delay,
                           )

    def _onPossibleErrorIq(self, elem):
        if elem['type'] == "error":
            sender = elem['from']
            for el in elem.elements():
                if el.name == 'error' and el['code'] == '404':
                    l.warn('Received a 404 code from the server,\
 setting the target user as offline')
                    if sender in self._online_contacts:
                        self._online_contacts.remove(sender)
                    else:
                        l.debug('Received a 404 from %s which not (anymore?)\
 in the online contacts list.')

    def _onPresence(self, elem):
        """
        A new presence message has been received,
        let's see who has (dis)connected.
        """
        l.debug('_onPresence')
        presence = XMPPPresence(elem)
        if presence.available:
            l.debug("%s is now available" % presence.sender)
            #Store full jid.
            self._online_contacts.add(presence.sender)
        else:
            l.debug("%s is not available anymore" % presence.sender)
            if presence.jid in self._online_contacts:
                self._online_contacts.remove(presence.sender)

    def isOnline(self, jid):
        l.debug('isOnline "%s"' % jid)
        l.debug('current JIDS: %s' % self._online_contacts)
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
        l.debug('XMPPPresence.toEtree')
        msg = Element(('jabber:client', 'presence'))
        msg.addElement('status', content=self.status)
        msg.addElement('priority', content=str(self.priority))
        return msg


#
#Exceptions
#
class UserNotAvailable(Exception):
    def __init__(self, user):
        self._user = user

    def __str__(self):
        return "User %s is not available" % self._user
