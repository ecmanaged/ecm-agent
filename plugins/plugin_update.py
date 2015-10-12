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

RUN_AS_ROOT = True

import os
import sys

# Local
from __plugin import ECMPlugin
import __helper as ecm

from commands import getstatusoutput
from time import time

class ECMSystemUpdateAPT(ECMPlugin):
    def cmd_update_check(self, *argv, **kwargs):
        status, result = self._update()
        status, result = getstatusoutput('nice apt-get -s -o Debug::NoLocking=true upgrade | grep ^Inst | cut -f2 -d" "')
        
        if status:
            raise Exception('Problem getting update: %s' % result)
        
        pkg_list = []
        for pkg in result.split('\n'):
            if not pkg: continue
            pkg_list.append(pkg)
            
        return ecm.format_output(status, pkg_list)

    def cmd_update_system(self, *argv, **kwargs):
        log_file = '/var/tmp/system-update_' + str(time()) + '.log'
        
        # Run on detached child
        if ecm.fork('/'):
            return log_file    
                           
        self._update()
        os.environ["LANG"] = "C"
        os.environ["DEBIAN_FRONTEND"] = "noninteractive"
        status, output = getstatusoutput('nice apt-get -f -y -o DPkg::Options::=--force-confold -qq \
            --allow-unauthenticated -o Debug::NoLocking=true upgrade < /dev/null')

        ecm.file_write(log_file, output)
        sys.exit(status)

    @staticmethod
    def _update():
        return getstatusoutput('nice apt-get -o Debug::NoLocking=true update')


class ECMSystemUpdateYUM(ECMPlugin):
    def cmd_update_check(self, *argv, **kwargs):
        status, result = self._update()
        status, result = getstatusoutput('nice yum check-update | egrep -e "x86|i386|noarch" | grep -v ^Exclud | cut -f1 -d" "')
        
        if status:
            raise Exception('Problem getting update: %s' % result)
        
        pkg_list = []
        for pkg in result.split('\n'):
            if not pkg: continue
            pkg_list.append(pkg)
        
        return ecm.format_output(status, pkg_list)

    def cmd_update_system(self, *argv, **kwargs):
        log_file = '/var/tmp/system-update_' + str(time()) + '.log'
        
        # Run on detached child
        if ecm.fork('/'):
            return log_file
                           
        self._update()
        os.environ["LANG"] = "C"
        status, output = getstatusoutput('nice yum update -y < /dev/null')

        ecm.file_write(log_file, output)
        sys.exit(status)

    @staticmethod
    def _update():
        return getstatusoutput('nice yum clean all')
        

distribution, _version = ecm.get_distribution()
if distribution.lower() in ['debian', 'ubuntu']:
    ECMSystemUpdateAPT().run()

elif distribution.lower() in ['centos', 'redhat', 'fedora', 'amazon']:
    ECMSystemUpdateYUM().run()

else:
    # Not supported
    sys.exit()
