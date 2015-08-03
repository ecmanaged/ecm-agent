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

configure_uuid = None
configure_account_id = None
configure_server_group_id = None

optlist, args = getopt.getopt(sys.argv[1:], 'uasp:', ["uuid=", "account-id=", "server-group-id=", "password="])

for option, value in optlist:
    if option in ("-u", "--uuid"):
        configure_uuid = value
    elif option in ("-a", "--account-id"):
        configure_account_id = value
    elif option in ("-s", "--server-group-id"):
        configure_server_group_id = value
    elif option in ("-p", "--password"):
        configure_password = value
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

if configure_uuid:
    # Write static configuration and continue
    config['XMPP']['user'] = '%s@%s' % (configure_uuid, config['XMPP']['host'])
    config['XMPP']['manual'] = True
    config['XMPP']['unique_id'] = config.get_unique_id()

if configure_account_id:
    config['XMPP']['account_id'] = configure_account_id
if configure_server_group_id:
    config['XMPP']['server_group_id'] = configure_server_group_id

# Generate a new password if not set and write it asap
# Avoids problem when starting at same time two agents not configured (fedora??)
if configure_password:
    config['XMPP']['password'] = configure_password

if not config['XMPP'].get('password'):
    config['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]
config.write()

print 'Manual configuration override succeeded.'
