# -*- coding:utf-8 -*-

#Twisted
from twisted.internet.defer import (inlineCallbacks, returnValue, Deferred)
from twisted.web.client import getPage
from twisted.internet import reactor
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.error import ProcessTerminated, ProcessDone

#Local
import ecagent.twlogging as log

#Python
from time import sleep
from platform import node
import random
import socket

#External
from configobj import ConfigObj

try:
    import dmidecode

except:
    pass

_ECMANAGED_AUTH_URL = 'https://my.ecmanaged.com/agent/meta-data/uuid'
_ECMANAGED_AUTH_URL_ALT = 'https://my.ecmanaged.com/agent/meta-data/uuid'

class SMConfigObj(ConfigObj):
    """
    A simple wrapper for ConfigObj that will check the MAC and try to
    reconfigure if it has changed before launching the agent.
    """

    def __init__(self, filename):
        ConfigObj.__init__(self, filename)

    @inlineCallbacks
    def checkUUID(self):
        mac = self._get_mac()

        # Always generate a new password if not is set
        if not self['XMPP']['password']:
            self['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]

        if mac:
            if str(mac) == str(self._getStoredMAC()):
                log.debug("MAC has not changed. Skip UUID check")

            else:
                # Try to get uuid
                uuid = None
                for i in range(30):
                    try:
                        uuid = yield self._getUUID()
                        if uuid:
                            break

                    except:
                        pass
                    sleep(20)

                if not uuid:
                    log.error("ERROR: Could not obtain UUID. please set up XMPP manually in %s" % self.filename)
                    returnValue(False)

                if str(uuid) == str(self._getStoredUUID()):
                    log.debug("UUID has not changed.")

                    # Update mac
                    self['XMPP']['mac'] = mac
                    self.write()

                else:
                    log.info("UUID has changed, reconfiguring XMPP user/pass")
                    self['XMPP']['user'] = '@'.join((uuid, self['XMPP']['host']))

                    self['XMPP']['mac'] = mac
                    self.write()

            returnValue(True)

        else:
            log.error("ERROR: Could not obtain MAC. please set up XMPP manually in %s" % self.filename)
            returnValue(False)

    def _getUUID(self):
        if self['XMPP'].as_bool('manual'):
            log.info("Skipping UUID auto configuration as manual flag is set.")
            return self['XMPP']['user'].split('@')[0]

        else:
            # Try to get from preconfigured
            log.info("try to get UUID via preconfiguration")
            uuid = self._getUUIDPreConfig()

            if not uuid:
                # Try to configure via URL (ECM meta-data)
                log.info("try to get UUID via URL (ecagent meta-data)")
                uuid = self._getUUIDViaWeb()

            return uuid

    @inlineCallbacks
    def _getUUIDViaWeb(self):
        hostname = ''
        address = ''
        try:
            hostname = self._get_hostname()
            address  = self._get_ip()
        except:
            pass

        auth_url = _ECMANAGED_AUTH_URL + "/?ipaddress=%s&hostname=%s" % (address, hostname)
        auth_url_alt = _ECMANAGED_AUTH_URL + "/?ipaddress=%s&hostname=%s" % (address, hostname)

        auth_content = yield getPage(auth_url)

        if not auth_content:
            auth_content = yield getPage(auth_url_alt)

        for line in auth_content.splitlines():
            if line and line.startswith('uuid:'):
                returnValue(line.split(':')[1])

        returnValue('')

    def _getUUIDPreConfig(self):
        from os import remove
        from os.path import dirname, abspath, join, exists

        uuid_file = join(dirname(__file__), './config/_uuid.cfg')
        if exists(uuid_file):
            f = open(uuid_file, 'r')
            for line in f:
                if line.startswith('uuid:'):
                    return line.split(':')[1]
            f.close()
            remove(uuid_file)

        return None

    def _run(self, command, args):
        spp = SimpleProcessProtocol()
        d = spp.getDeferredResult()
        reactor.spawnProcess(spp, command, args.split())
        d.addErrback(self._onErrorRunning)
        return d

    def _onErrorRunning(self, failure):
        log.warn('Command failed to execute: %s' % failure)
        return (255, '', '')

    def _get_ip(self):
        'Create dummy socket to get address'
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('my.ecmanaged.com', 0))
        return s.getsockname()[0]

    def _get_hostname(self):
        return node()

    def _getStoredUUID(self):
        return self['XMPP']['user'].split('@')[0]

    def _getStoredMAC(self):
        return self['XMPP']['mac']

    def _get_mac(self):
        """
            Try to get a unique identified, Amazon may change mac on stop/start
        """
        uuid = None
        try:
            import urllib

            urlopen = urllib.urlopen("http://169.254.169.254/latest/meta-data/instance-id")
            for line in urlopen.readlines():
                if ("i-" in line):
                    uuid = hex(line)
            urlopen.close()

        except:
            pass

        # Use network mac for non aws
        if not uuid:
            from uuid import getnode
            uuid = getnode()

        return uuid


class SimpleProcessProtocol(ProcessProtocol):
    def __init__(self):
        self.stdout = ""
        self.stderr = ""
        self.deferreds = []

    def connectionMade(self):
        log.debug("Process started.")

    def outReceived(self, data):
        log.debug("Out made")
        self.stdout += data

    def errReceived(self, data):
        log.debug("Err made: %s" % data)
        self.stderr += data

    def processEnded(self, status):
        log.debug("process ended")
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

