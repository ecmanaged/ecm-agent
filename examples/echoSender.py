#!/usr/bin/env python

#
# Originally written by Darryl Vandorp
# http://randomthoughts.vandorp.ca/

from twisted.words.protocols.jabber import client, jid
from twisted.words.xish import domish
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from time import time

target = "test@xmpp.ecmanaged.net/sm_agent-1"

class JabberClient:
    def __init__(self):
        #Connect to jabber server
        myJid = jid.JID('task-devel@cloud.ackstorm.es/tasker')
        factory = client.basicClientFactory(myJid, 'mypass')
        factory.addBootstrap('//event/stream/authd', self.authd)
        reactor.connectTCP('xmpp.ecmanaged.net', 5222, factory)

        #Set up the looping call that will be sending messages.
        self._lc = LoopingCall(self.sendMessage)

    def authd(self, xmlstream):
        print "Authenticated"
        self._xs = xmlstream

        #Send presence update
        presence = domish.Element(('jabber:client', 'presence'))
        xmlstream.send(presence)
        xmlstream.addObserver('/iq', self.debug)

        #Send a message every 5 secs.
        self._lc.start(5)

    def sendMessage(self):
        print "SENDMESSAGE"

        #Build the command message
        msg = domish.Element(("jabber:client", "iq"))
        msg["id"] = str(time())
        msg["to"] = target
        msg["from"] = 'task-devel@cloud.ackstorm.es/tasker'
        msg["type"] = "set"
        sm = msg.addElement('sm_message')
        sm['version'] = '1'
        command = sm.addElement('command')
        command['name'] = 'test_echo'
        args = command.addElement('args')
        args['arg1'] = 'foo'
        args['arg2'] = 'bar'

        #And send it.
        print str(msg.toXml())
        self._xs.send(msg.toXml())

    @staticmethod
    def debug(elem):
        print "=" * 20
        print elem.toXml().encode('utf-8')
        print "=" * 20


client = JabberClient()
reactor.run()
