# -*- coding:utf-8 -*-

#Twisted
from twisted.internet.defer import (inlineCallbacks, returnValue, Deferred)
from twisted.web.client import getPage
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessTerminated, ProcessDone

#Local
import ecagent.twlogging as l

#Python
from uuid import getnode
from time import sleep
from platform import node
import random, re, socket


#External
from configobj import ConfigObj

try:
    import dmidecode

except:
    pass


class SMConfigObj(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the MAC and try to
    reconfigure if it has changed before launching the agent.
    """
    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    @inlineCallbacks
    def checkUUID(self):
        mac = getnode()

        # Always generate a new password if not is set
        if not self['XMPP']['password']:
            self['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]

        if mac:
            if str(mac) == str(self._getStoredMAC()):
                l.debug("MAC has not changed. Skip UUID check")
            else:
                # Try to get uuid
                for i in range(30):
                    try:
                        uuid = yield self._getUUID()
                        if uuid: break
                    except: pass
                    sleep(20)

                else:
                    l.error("ERROR: Could not obtain UUID. please set up XMPP manually in %s" % self.filename)
                    returnValue(False)

                if str(uuid) == str(self._getStoredUUID()):
                    l.debug("UUID has not changed.")

                    # Update mac
                    self['XMPP']['mac'] = mac
                    self.write()

                else:
                    l.info("UUID has changed, reconfiguring XMPP user/pass")
                    self['XMPP']['user'] = '@'.join((uuid, self['XMPP']['host']))

                    self['XMPP']['mac'] = mac
                    self.write()

            returnValue(True)

        else:
            l.error("ERROR: Could not obtain MAC. please set up XMPP manually in %s" % self.filename)
            returnValue(False)

    def _getUUID(self):
        if self['XMPP'].as_bool('manual'):
            l.info("Skipping UUID auto configuration as manual flag is set.")
            return self['XMPP']['user'].split('@')[0]

        else:
            # Try to configure via URL (ECM meta-data)
            l.info("try to get UUID via URL (ecagent meta-data)")
            uuid = self._getUUIDViaWeb()
            if uuid: return uuid

            l.info("try to get UUID using dmidecode")
            try:
                for v in dmidecode.QuerySection('system').values():
                    if type(v) == dict and v['dmi_type'] == 1:
                        if (v['data']['UUID']):
                            return str((v['data']['UUID'])).lower()

            except:
                pass

            l.info("Try to get UUID  by dmidecode command")
            return self._getUUIDViaCommand()

    @inlineCallbacks
    def _getUUIDViaWeb(self):
        hostname = ''
        address = ''
        try:
            hostname = node()
            address = self._get_ip()
        except:
            pass

        retr = yield getPage("https://my.ecmanaged.com/agent/meta-data/uuid/?ipaddress=%s&hostname=%s" %(address,hostname))
        for line in retr.splitlines():
            if line and line.startswith('uuid:'):
                returnValue(line.split(':')[1])
        returnValue('')

    def _getUUIDViaCommand(self):
        # using direct binary access
        exit_code, stdout, stderr = yield self._run("dmidecode",
                                                    "-s system-uuid")

        match = re.match('^([\d|\w|\-]{30,50})$', stdout)
        if match and match.group(1):
            returnValue(str(match.group(1)).lower())

        returnValue('')

    def _get_ip(self):
        'Create dummy socket to get address'
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('my.ecmanaged.com', 0))
        return s.getsockname()[0]

    def _getStoredUUID(self):
        return self['XMPP']['user'].split('@')[0]

    def _getStoredMAC(self):
        return self['XMPP']['mac']

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

