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
from os import chdir, remove
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
config_filename = join(dirname(__file__), './config/ecagent.cfg')

try:
    config = SMConfigObj(config_filename)

    if configure_uuid:
        # Write static configuration and continue
        import random
        from uuid import getnode
        config['XMPP']['user'] = '%s@%s' % (configure_uuid, config['XMPP']['host'])
        config['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]
        config['XMPP']['mac'] = str(getnode())
        config['XMPP']['manual'] = True
        config.write()

except Exception:
    print 'Unable to read the config file at %s' % config_filename
    print 'Agent will now quit'
    sys.exit(-1)

# Start agent and setup logging
application = Application("ecagent")

log.setup(application, config['Log'])
agent = SMAgent(config)
