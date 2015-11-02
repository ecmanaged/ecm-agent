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
from commands import getstatusoutput
from pkg_resources import parse_version

# Local
from __plugin import ECMPlugin
import __helper as ecm


pkg_kit = True

try:
    from gi.repository import PackageKitGlib
except ImportError:
    pkg_kit = False


class ECMRebootRequirePackageKit(ECMPlugin):
    def cmd_reboot_require(self, *argv, **kwargs):
        from platform import release, machine
        from gi.repository import PackageKitGlib

        working_kernel = release()

        client = PackageKitGlib.Client()
        client.refresh_cache(False, None, lambda p, t, d: True, None)
        res = client.resolve(PackageKitGlib.FilterEnum.INSTALLED, ['kernel'], None, lambda p, t, d: True, None)

        if res.get_exit_code() != PackageKitGlib.ExitEnum.SUCCESS:
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

class ECMRebootRequire(ECMPlugin):
    def cmd_reboot_require(self, *argv, **kwargs):
        distribution, _version = ecm.get_distribution()
        if distribution.lower() in ['debian', 'ubuntu']:
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
            return False

        elif distribution.lower() in ['centos', 'redhat', 'fedora', 'amazon']:
            retval, current_kernel = getstatusoutput('uname -r')
            if retval != 0:
                return False
            retval, latest_kernel = getstatusoutput("rpm -q --last kernel | perl -pe 's/^kernel-(\S+).*/$1/' | head -1")
            if retval != 0:
                return False
            return parse_version(latest_kernel) > parse_version(current_kernel)
        return False



if pkg_kit:
    ECMRebootRequirePackageKit().run()
else:
    ECMRebootRequire().run()