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

import urllib2
import json
import socket

from os import getpid


try:
    import psutil
    from gc import collect

except ImportError:
    psutil = None
    collect = None
    pass

import core.logging as log


def mem_usage():
    rss, vms = 0, 0
    try:
        rss, vms = psutil.Process(getpid()).get_memory_info()
        rss /= 1000000.0
        vms /= 1000000.0
    except:
        pass
    log.info("Current Memory usage: rss=%sMB | vms=%sMB" % (rss, vms))

    return rss, vms


def mem_clean(where=''):
    _collect = collect()
    rss, vms = mem_usage()
    string = "_mem_clean: %s collected %d objects. (current mem: rss=%sMB | vms=%sMB)" % (where, _collect, rss, vms)

    log.debug(string)

    del _collect, where, vms, string

    return rss


def read_url(url, data=None, headers=None):
        """
        :param url: URL to get
        :param data: will use POST method on data
        :param headers:
        :return:

        """
        log.debug('functions.read_url(%s)' % url)
        retval = {}

        if data:
            data = json.dumps(data)

        try:
            socket.setdefaulttimeout(80)
            req = urllib2.Request(url, data=data, headers=headers)
            urlopen = urllib2.urlopen(req)
            result = ''.join(urlopen.readlines())

            if result:
                log.debug('read_url::content: %s' % result)
                retval = json.loads(result)

        except Exception, e:
            log.error('read_url::failed %s' % str(e))

        return retval

