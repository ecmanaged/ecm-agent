# -*- coding:utf-8 -*-

#Twisted
from twisted.words.protocols.jabber import client, jid, xmlstream
from twisted.words.xish.domish import Element
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.words.protocols.jabber.xmlstream import STREAM_END_EVENT
from twisted.words.protocols.jabber.client import IQ

import twlogging as log
from random import random

# Add registerAccount to XMPPAuthenticator
class FixedXMPPAuthenticator(client.XMPPAuthenticator):
    AUTH_FAILED_EVENT = "//event/client/xmpp/authfailed"

    def registerAccount(self, username=None, password=None):
        if username:
            self.jid.user = username
        if password:
            self.password = password

        iq = IQ(self.xmlstream, "set")
        iq.addElement(("jabber:iq:register", "query"))
        iq.query.addElement("username", content=self.jid.user)
        iq.query.addElement("password", content=self.password)

        iq.addCallback(self._registerResultEvent)

        iq.send()

    def _registerResultEvent(self, iq):
        if iq['type'] == 'result':
            # Registration succeeded -- go ahead and auth
            # self.streamStarted(iq)
            pass
        else:
            self.xmlstream.dispatch(iq, self.AUTH_FAILED_EVENT)


client.XMPPAuthenticator = FixedXMPPAuthenticator


class BasicClient:
    def __init__(self, user, password, host, observers,
                 resource="XMPPBasicClient", max_delay=60):
        """
        Basic XMPP Client class.

        @param user: The user to use when authenticating to the XMPP server.
        @param password: The password for the user.
        @param host: XMPP server address.
        @param observers: Dictionary of observers.
        @param resource: Resource to use when sending messages by default.
        """

        #use_http = False
        #url="http://xmpp.ecmanaged.net/http-bind")
        #auth = XMPPAuthenticator(client_jid, secret)
        #self._factory = HTTPBindingStreamFactory(auth)

        self._user = user
        self._password = password
        self._host = host
        self._port = 5222

        self._observers = observers
        myJid = jid.JID('/'.join((user, resource)))

        self._factory = client.XMPPClientFactory(myJid, password)

        self._factory.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self._connected)
        self._factory.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self._authd)
        self._factory.addBootstrap(xmlstream.STREAM_END_EVENT, self._stream_end)
        self._factory.addBootstrap(xmlstream.INIT_FAILED_EVENT, self._failed_auth)
        self._factory.maxDelay = max_delay

        #        if(use_http):
        #            connector = HTTPBClientConnector(str(url))
        #            connector.connect(f)
        #        else:
        #            connector = XMPPClientConnector(reactor, host, self._factory)
        #            connector.connect()

        # Give time to load commands
        reactor.callLater(3, self._connect)

    def _connect(self):
        reactor.connectTCP(self._host, self._port, self._factory)

    def _failed_auth(self, error):
        """ overwrite in derivated class """
        log.info("Auth failed, trying to autoregister")
        self._factory.authenticator.registerAccount(self._user.split('@')[0], self._password)

        # Initialize again in a few
        reactor.callLater(3, self._factory.authenticator.initializeStream)

    def _stream_end(self, error):
        """ overwrite in derivated class """
        log.info("XMPPClient stream end: %s" % error)

    def _connected(self, xml_stream):
        log.info("XMPPClient connected")
        self._xs = xml_stream

    def _authd(self, xml_stream):
        """
        Authenticated event callback.

        This method gets called when login has been successful.
        """
        log.info("XMPPClient authenticated")

        #Keepalive: Send a newline every 60 seconds
        #to avoid server disconnect
        self._keep_alive_lc = LoopingCall(self._xs.send, '\n')
        self._keep_alive_lc.start(60)
        self._xs.addObserver(STREAM_END_EVENT,
                             lambda _: self._keep_alive_lc.stop())

        for message, callable in self._observers:
            self._xs.addObserver(message, callable)

        presence = Element(('jabber:client', 'presence'))
        self._xs.send(presence)

    def _newid(self):
        return str(int(random() * (10 ** 31)))

    def send(self, elem):
        log.debug('BasicClient.send: %s' % elem.toXml())
        if not elem.getAttribute('id'):
            log.debug('No message ID in message, creating one')
            elem['id'] = self._newid()
        d = self._xs.send(elem.toXml())

        #Reset keepalive looping call timer
        if self._keep_alive_lc.running:
            self._keep_alive_lc.stop()
            self._keep_alive_lc.start(60)
        return d

    def debug(self, elem):
        """
        Prints a dump of the xml message.

        @param elem: Message to print.
        """
        log.debug("Message dump follows:")
        log.debug("v" * 20)
        log.debug(elem.toXml().encode('utf-8'))
        log.debug("^" * 20)
