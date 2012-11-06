
#Twisted
from twisted.internet.defer import (inlineCallbacks, returnValue,
        succeed, Deferred)
from twisted.web.client import getPage
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessTerminated, ProcessDone

#Local
import ecm_agent.twlogging as l

#Python
from uuid import getnode
import random
import sys
import urllib
import hashlib
import os
import re

#External
from configobj import ConfigObj
import dmidecode


class SMConfigObj(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the UUID and try to
    reconfigure if it has changed before launching the agent.
    """
    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    @inlineCallbacks
    def checkUUID(self):
        uuid = yield self._getUUID()
        if uuid:
            if uuid == self._getStoredUUID():
                l.debug("UUID has not changed.")
            else:
                l.info("UUID has changed, reconfiguring XMPP user/pass")
                self['XMPP']['user'] = '@'.join((uuid, self['XMPP']['host']))
                self['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]
                self.write()
            returnValue(True)
        else:
            l.error("ERROR: Could not obtain UUID,\
 please set up XMPP manually in %s" % self.filename)
            returnValue(False)

    def _getUUID(self):
        if self['XMPP'].as_bool('manual'):
            l.info("Skipping UUID auto configuration as manual flag is set.")
            return self['XMPP']['user'].split('@')[0]
        else:
            # try to get UUID using dmidecode
            for v in dmidecode.QuerySection('system').values():
                if type(v) == dict and v['dmi_type'] == 1:
                    if (v['data']['UUID']):
                        return str((v['data']['UUID'])).lower()
        
            # Try to get via web (EC2 or ECM)
            retr = self._getUUIDViaWeb()
            if retr: return retr
            
            # Try by dmidecode command
            return self._getUUIDViaCommand()

    @inlineCallbacks
    def _getUUIDViaWeb(self):
        retr = yield getPage(
            "https://my.ecmanaged.com/agent/meta-data/uuid")
        for line in retr.splitlines():
            if line and line.startswith('uuid:'):
                returnValue(line.split(':')[1])

        retr = yield getPage(
               "http://169.254.169.254/latest/meta-data/instance-id")
        for line in retr.splitlines():
            if line and line.startswith('i-'):
                returnValue(hashlib.sha1("%s:1" % (line)).hexdigest())

        returnValue('')

    def _getUUIDViaCommand(self):
        # using direct binary access
        exit_code, stdout, stderr = yield self._run("dmidecode",
                                                "-s system-uuid")

        match = re.match('^([\d|\w|\-]{30,50})$', stdout)
        if match and match.group(1):
            returnValue(str(match.group(1)).lower())

        returnValue('')

    def _getStoredUUID(self):
        return self['XMPP']['user'].split('@')[0]

    def _run(self, command, args):
        spp = SimpleProcessProtocol()
        d = spp.getDeferredResult()
        reactor.spawnProcess(spp, command, args.split())
        d.addErrback(self._onErrorRunning)
        return d

    def _onErrorRunning(self, failure):
        l.warn('Command failed to execute: %s' % failure)
        return (255, '', '')


class SimpleProcessProtocol(ProcessProtocol):
    def __init__(self):
        self.stdout = ""
        self.stderr = ""
        self.deferreds = []

    def connectionMade(self):
        l.debug("Process started.")

    def outReceived(self, data):
        l.debug("Out made")
        self.stdout += data

    def errReceived(self, data):
        l.debug("Err made: %s" % data)
        self.stderr += data

    def processEnded(self, status):
        l.debug("process ended")
        t = type(status.value)
        if t is ProcessDone:
            exit_code = 0
        elif t is ProcessTerminated:
            exit_code = status.value.exitCode
        else:
            raise status

        for d in self.deferreds:
            d.callback((exit_code, self.stdout, self.stderr))

    def getDeferredResult(self):
        d = Deferred()
        self.deferreds.append(d)
        return d
