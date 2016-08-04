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
from time import time
from pkg_resources import parse_version

# Local
from __plugin import ECMPlugin
import __helper as ecm

pkg_kit = True

try:
    from gi.repository import PackageKitGlib as pk
except ImportError:
    pkg_kit = False
    from commands import getstatusoutput

log_file = '/opt/ecmanaged/ecagent/log/system-update_' + str(time()) + '.log'


class ECMSystemPackageKit(ECMPlugin):
    def cmd_update_check(self, *argv, **kwargs):
        client = pk.Client()
        client.refresh_cache(False, None, lambda p, t, d: True, None)
        res = client.get_updates(pk.FilterEnum.NONE, None, lambda p, t, d: True, None)
        pkg_list = []
        for pkg in res.get_package_array():
            pkg_list.append(pkg.get_id())

        return ecm.format_output(0 if res.get_exit_code() == pk.ExitEnum.SUCCESS else 1, pkg_list)

    def cmd_update_system(self, *argv, **kwargs):
        # Run on detached child
        if ecm.fork('/'):
            return log_file

        client = pk.Client()
        client.refresh_cache(False, None, lambda p, t, d: True, None)
        res = client.get_updates(pk.FilterEnum.NONE, None, lambda p, t, d: True, None)
        pkg_list = []
        for pkg in res.get_package_array():
            pkg_list.append(pkg.get_id())

        # updating the system
        if pkg_list:
            res = client.install_packages(False, pkg_list, None, lambda p, t, d: True, None)
            ecm.file_write(log_file, pkg_list)
            sys.exit(res.get_exit_code() == pk.ExitEnum.SUCCESS)

    def cmd_reboot_require(self, *argv, **kwargs):
        from platform import release, machine

        working_kernel = release()

        client = pk.Client()
        client.refresh_cache(False, None, lambda p, t, d: True, None)
        res = client.resolve(pk.FilterEnum.INSTALLED, ['kernel'], None, lambda p, t, d: True, None)

        if res.get_exit_code() != pk.ExitEnum.SUCCESS:
            return False

        package_ids = res.get_package_array()

        if len(package_ids) == 0:
            return False

        installed_kernel = None

        for pkg in package_ids:
            if pkg.get_arch() == machine():
                if installed_kernel is None:
                    installed_kernel = pkg
                else:
                    if parse_version(pkg.get_version()) > parse_version(installed_kernel.get_version()):
                        installed_kernel = pkg

        installed_kernel = installed_kernel.get_version() + '.' +installed_kernel.get_arch()

        return parse_version(installed_kernel) > parse_version(working_kernel)

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

    def cmd_reboot_require(self, *argv, **kwargs):
        if os.path.exists('/var/run/reboot-required.pkgs') or os.path.exists('/var/run/reboot-required'):
            return True
        else:
            retval, current_kernel = getstatusoutput('uname -r')
            if retval != 0:
                return False
            retval, latest_kernel = getstatusoutput("dpkg --list | grep linux-image | head -n1 | cut -d ' ' -f3 | perl -pe 's/^linux-image-(\S+).*/$1/'")
            if retval != 0:
                return False
            return parse_version(latest_kernel) > parse_version(current_kernel)

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

    def cmd_reboot_require(self, *argv, **kwargs):
        retval, current_kernel = getstatusoutput('uname -r')
        if retval != 0:
            return False
        retval, latest_kernel = getstatusoutput("rpm -q --last kernel | perl -pe 's/^kernel-(\S+).*/$1/' | head -1")
        if retval != 0:
            return False
        return parse_version(latest_kernel) > parse_version(current_kernel)

if pkg_kit:
    ECMSystemPackageKit().run()
else:
    distribution, _version = ecm.get_distribution()
    if distribution.lower() in ['debian', 'ubuntu']:
        ECMSystemUpdateAPT().run()
    elif distribution.lower() in ['centos', 'redhat', 'fedora', 'amazon']:
        ECMSystemUpdateYUM().run()
    else:
        # Not supported
        sys.exit()
