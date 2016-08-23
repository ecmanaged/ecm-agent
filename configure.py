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
from core.config import ECMConfig

root_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(root_dir)

if root_dir not in sys.path:
    sys.path.append(root_dir)

# In windows . is not on python path.
if "." not in sys.path:
    sys.path.append(".")

configure_account = None
configure_groups = None
configure_add_groups = None
configure_delete_groups = None

try:
    optlist, args = getopt.getopt(sys.argv[1:], 'a:g:ag:dg', ["account=", "groups=", "add-groups=", "delete-groups="])

except getopt.GetoptError:
    print 'Please configure agent with ./configure.py --account=XXXXX --groups=abc,def'
    print 'You can add groups using --add-groups=xyz'
    print 'You can delete groups using --delete-groups=xyz'
    sys.exit(-1)

for option, value in optlist:
    if option in ("-a", "--account"):
        configure_account = value

    elif option in ("-g", "--groups"):
        configure_groups = value

    elif option in ("-ag", "--add-groups"):
        configure_add_groups = value

    elif option in ("-dg", "--delete-groups"):
        configure_delete_groups = value

root_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(root_dir)

# Parse config file or end execution
config_file = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.cfg')
config_file_init = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.cfg.init')

# manipulate configuration file
if not os.path.isfile(config_file):
    os.rename(config_file_init, config_file)

if not os.path.isfile(config_file):
    print 'Unable to read the config file at %s' % config_file
    print 'Agent will now quit'
    sys.exit(-1)

config = ECMConfig(config_file)

if not configure_account and not config['Auth']['account']:
    print 'Please configure agent with ./configure.py --account=XXXXX'
    sys.exit(-1)

if configure_account:
    config['Auth']['account'] = configure_account

if configure_groups:
    list_groups = configure_groups.split(',')
    list_groups = map(str.strip, list_groups)
    groups = ','.join(list_groups)
    config['Groups']['groups'] = groups

if configure_add_groups:
    groups = config['Groups']['groups']
    list_groups = groups.split(',')
    list_groups = map(str.strip, list_groups)

    add_groups = configure_add_groups.split(',')
    add_groups = map(str.strip, add_groups)

    for group in add_groups:
        if group not in list_groups:
            list_groups.append(group)

    groups_string = ','.join(list_groups)
    config['Groups']['groups'] = groups_string

if configure_delete_groups:
    groups = config['Groups']['groups']
    list_groups = groups.split(',')
    list_groups = map(str.strip, list_groups)

    del_groups = configure_delete_groups.split(',')
    del_groups = map(str.strip, del_groups)

    for group in del_groups:
        if group in list_groups:
            list_groups.remove(group)
    groups_string = ','.join(list_groups)
    config['Groups']['groups'] = groups_string

config.write()
print 'Manual configuration override succeeded.'
