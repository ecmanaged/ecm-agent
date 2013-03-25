# -*- coding:utf-8 -*-

from ecmplugin import ECMPlugin

import time, re
import urllib
import socket

class ECMNetwork(ECMPlugin):

    def cmd_web_regexp(self, *argv, **kwargs):
        """ Syntax: page_regexp <url> <regex> """

        url = kwargs.get('url',None)
        regex = kwargs.get('regex',None)

        if not (url and regex):
            raise Exception(self.cmd_web_regexp.__doc__)

        try:
            urlopen = urllib.urlopen(url)

        except:
            raise Exception("Unable to retrieve URL %s" % url)

        _regex = re.compile(regex)
        retval = ''
        for line in urlopen.readlines():
            if _regex.match(line):
                retval = retval + line

        urlopen.close()
        return retval

    def cmd_web_download(self, *argv, **kwargs):
        """Syntax: download <url>"""

        url = kwargs.get('url',None)

        if not url:
            raise Exception(self.cmd_web_download.__doc__)

        try:
            retval = urllib.urlretrieve(url)
            return(retval[0])

        except:
            raise Exception("Unable to retrieve URL %s" % url)

    def cmd_web_get(self, *argv, **kwargs):
        """Syntax: page_get <url>"""

        url = kwargs.get('url',None)

        if not url:
            raise Exception(self.cmd_web_get.__doc__)

        try:
            urlopen = urllib.urlopen(url)
            retval = ''.join(urlopen.readlines())
            urlopen.close()
            return(retval)

        except:
            raise Exception("Unable to retrieve URL %s" % url)

    def cmd_web_perf(self, *argv, **kwargs):
        """Syntax: page_perf <url>"""

        url = kwargs.get('url',None)

        if not url:
            raise Exception(self.cmd_web_perf.__doc__)
        try:
            starttime = time.time()
            urlopen = urllib.urlopen(url)
            retval = time.time() - starttime
            urlopen.close()
            return(retval)

        except:
            raise Exception("Unable to retrieve URL %s" % url)

    # TCP
    def cmd_net_tcp(self, *argv, **kwargs):
        """Syntax net.tcp <hostname> <port>"""

        host = kwargs.get('host',None)
        port = kwargs.get('port',None)

        if not (host and port):
            raise Exception(self.cmd_net_tcp.__doc__)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(30)

            data=''
            s.connect((host, int(port)))
            #            data = s.recv(1024)
            s.shutdown(2)

            return("Connected: %s" % str(data))

        except socket.error, e:
            raise Exception("Unable to connect: URL %s" % e[1])


ECMNetwork().run()