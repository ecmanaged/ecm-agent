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

# In windows . is not on python path.
import random
import sys
import getopt
import os
from ecagent.config import SMConfigObj

root_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(root_dir)

if root_dir not in sys.path:
    sys.path.append(root_dir)

# In windows . is not on python path.
if "." not in sys.path:
    sys.path.append(".")

configure_account = None
configure_server_groups = None
configure_groups = None

try:
    optlist, args = getopt.getopt(sys.argv[1:], 'a:t:', ["account=", "tags="])
except getopt.GetoptError:
    print 'Please configure agent with ./configure.py --account=XXXXX --tags=XXX,XXX'
    sys.exit(-1)

for option, value in optlist:
    if option in ("-a", "--account"):
        configure_account = value

    elif option in ("-t", "--tags"):
        configure_tags = value

if not configure_account and not configure_tags:
    print 'Please configure agent with ./configure.py --account=XXXXX --tags=XXX'
    sys.exit(-1)

root_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(root_dir)

# Parse config file or end execution
config_file = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.cfg')
config_file_init = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.cfg.init')

# manipulate configuration file
if not os.path.isfile(config_file):
    config_file = config_file_init

if not os.path.isfile(config_file):
    print 'Unable to read the config file at %s' % config_file
    print 'Agent will now quit'
    sys.exit(-1)

config = SMConfigObj(config_file)

if configure_account:
    config['XMPP']['account'] = configure_account

if configure_tags:
    config['XMPP']['tags'] = configure_tags

config.write()
print 'Manual configuration override succeeded.'
