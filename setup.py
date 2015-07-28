#!/usr/bin/env python

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

from distutils.core import setup

setup(name='ecmanaged-ecagent',
      version='2.2',
      release='1',
      group='Applications/System',

      license='Apache v2',
      long_description='ECManaged  Agent - Monitoring and deployment agent',

      author='Juan Carlos Moreno',
      author_email='juancarlos.moreno@ecmanaged.com',

      url='www.ecmanaged.com',

      install_requires = ['python2','python-twisted-core','python-twisted-web','python-protocols','python-configobj',
                          'python-twisted-words','python-psutil','libxml2-python','python-simplejson','rpm-python',
                          'python-crypto','python-httplib2', 'psutil', 'configobj', 'twisted'],

      #provides='ecmanaged-ecagent'],

      packages=['ecagent', 'plugins','monitor.mplugin.__base__'],

      data_files=[('config', ['config/ecagent.init.cfg', 'config/xmpp_cert.pub']),
                  ('/usr/share/doc', ['copyright']),
                  ('/usr/lib/systemd/system', ['ecagentd.service'])],
      scripts=['configure.py','ecagent.bat', 'ecagent.sh', 'ecagentd.tac']
     )
