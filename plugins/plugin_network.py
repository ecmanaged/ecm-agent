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

import time
import re
import urllib
import socket

from __ecm_plugin import ECMPlugin

class ECMNetwork(ECMPlugin):
    def cmd_web_regexp(self, *argv, **kwargs):
        """ Syntax: page_regexp <url> <regex> """

        url = kwargs.get('url', None)
        regex = kwargs.get('regex', None)

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

        url = kwargs.get('url', None)

        if not url:
            raise Exception(self.cmd_web_download.__doc__)

        try:
            retval = urllib.urlretrieve(url)
            return (retval[0])

        except:
            raise Exception("Unable to retrieve URL %s" % url)

    def cmd_web_get(self, *argv, **kwargs):
        """Syntax: page_get <url>"""

        url = kwargs.get('url', None)

        if not url:
            raise Exception(self.cmd_web_get.__doc__)

        try:
            urlopen = urllib.urlopen(url)
            retval = ''.join(urlopen.readlines())
            urlopen.close()
            return (retval)

        except:
            raise Exception("Unable to retrieve URL %s" % url)

    def cmd_web_perf(self, *argv, **kwargs):
        """Syntax: page_perf <url>"""

        url = kwargs.get('url', None)

        if not url:
            raise Exception(self.cmd_web_perf.__doc__)
        try:
            starttime = time.time()
            urlopen = urllib.urlopen(url)
            retval = time.time() - starttime
            urlopen.close()
            return (retval)

        except:
            raise Exception("Unable to retrieve URL %s" % url)

    # TCP
    def cmd_net_tcp(self, *argv, **kwargs):
        """Syntax net.tcp <hostname> <port>"""

        host    = kwargs.get('host', None)
        port    = kwargs.get('port', None)
        timeout = kwargs.get('timeout', 30)

        if not (host and port):
            raise Exception(self.cmd_net_tcp.__doc__)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)

            data = ''
            s.connect((host, int(port)))
            s.shutdown(2)

            return ("Connected: %s" % str(data))

        except socket.error, e:
            raise Exception("Unable to connect: %s" % e[1])


ECMNetwork().run()
