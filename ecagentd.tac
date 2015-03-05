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

# Chmod to current path
from os import chdir, remove, rename, getpid
from os.path import dirname, abspath, join, exists
import gc

# Enable automatic garbage collection.
gc.enable()

chdir(dirname(abspath(__file__)))

#In windows . is not on python path.
import sys
sys.path.append(".")

#Twisted
from twisted.application.service import Application

# Local
from ecagent.config import SMConfigObj
from ecagent.agent import SMAgent
import ecagent.twlogging as log

# Read pre-configuration
configure_uuid = None
try:
    configure_uuid_file = join(dirname(__file__), './config/_uuid.cfg')
    if exists(configure_uuid_file):
        f = open(configure_uuid_file, 'r')
        for line in f:
            if line.startswith('uuid:'):
                configure_uuid = line.split(':')[1]
        f.close()
        remove(configure_uuid_file)

except:
    pass

# Parse config file or end execution
config_file = join(dirname(__file__), './config/ecagent.cfg')
config_file_init = join(dirname(__file__), './config/ecagent.init.cfg')

# Is inital config (move init to cfg)
if not exists(config_file) and exists(config_file_init):
    rename(config_file_init, config_file)

# Read config and start
try:
    config = SMConfigObj(config_file)

    if configure_uuid:
        # Write static configuration and continue
        config['XMPP']['user'] = '%s@%s' % (configure_uuid, config['XMPP']['host'])
        config['XMPP']['unique_id'] = config._get_unique_id()
        config['XMPP']['manual'] = True
        config.write()

    # Generate a new password if not set and write it asap
    # Avoids problem when starting at same time two agents not configured (fedora??)
    if not config['XMPP'].get('password'):
        import random
        config['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]
        config.write()

except Exception:
    print 'Unable to read the config file at %s' % config_file
    print 'Agent will now quit'
    sys.exit(-1)

# Check for other processes running
pid_file = join(dirname(__file__), './twistd.pid')

if exists(pid_file):
    from psutil import pid_exists

    pid = open(pid_file).read()
    if pid and pid_exists(int(pid)):
        print 'Sorry, found another agent running'
        print 'Agent will now quit'
        sys.exit(-1)

# Write my pid
open(pid_file, 'w').write(str(getpid()))

# Start agent and setup logging
application = Application("ecagent")

log.setup(application, config['Log'])
agent = SMAgent(config)
