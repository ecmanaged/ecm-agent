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
from gi.repository import PackageKitGlib as pk

# Local
from __plugin import ECMPlugin
import __helper as ecm

class UpdateScript(ECMPlugin):
    def cmd__run(self, *argv, **kwargs):
        client = pk.Client()
        res = client.get_updates(pk.FilterEnum.NONE, None, lambda p, t, d: True, None)
        packages = []
        for pkg in res.get_package_array():
            packages.append(pkg.get_id())

        # updating the system
        if packages:
            res = client.install_packages(False, packages, None, lambda p, t, d: True, None)
            success = False

            if res.get_exit_code() == pk.ExitEnum.SUCCESS:
                success = True

            return success, packages

        else:
            return True, packages
UpdateScript.run()
