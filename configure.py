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
configure_groups = None

optlist, args = getopt.getopt(sys.argv[1:], 'as:', ["account=", "server-groups="])

for option, value in optlist:
    if option in ("-a", "--account"):
        configure_account = value

    elif option in ("-s", "--server-groups"):
        configure_groups = value

    else:
        raise Exception('unhandled option')

root_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(root_dir)

# Parse config file or end execution
config_file = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.cfg')
config_file_init = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.init.cfg')

# Is initial config (move init to cfg)
if not os.path.exists(config_file) and os.path.exists(config_file_init):
    os.rename(config_file_init, config_file)

# manipulate configuration file
if not os.path.isfile(config_file):
    print 'Unable to read the config file at %s' % config_file
    print 'Agent will now quit'
    sys.exit(-1)

config = SMConfigObj(config_file)

if configure_account:
    config['XMPP']['account'] = configure_account

if configure_groups:
    config['XMPP']['groups'] = configure_groups

config.write()
print 'Manual configuration override succeeded.'
