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

from __logger import LoggerManager
log = LoggerManager.getLogger(__name__)

from __packages import pip_install_single_package
from __plugin import ECMPlugin

class ECMPip(ECMPlugin):
    def cmd_pip_install(self, *argv, **kwargs):
        '''packagke: package name
           side_wide: boolean. if True package will be installed in site packages, else in user site
        '''
        # site_wide is a boolean. if True package will be installed in site packages, else in user site
        install_site_wide = kwargs.get('site_wide', False)
        pkg = kwargs.get('package', None)

        log.info('installing %s using pip' %pkg)

        pip_install_single_package(pkg, install_site_wide)

ECMPip().run()