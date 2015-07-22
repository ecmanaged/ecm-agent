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
from os import chdir, getpid
from os.path import dirname, abspath, join, exists, isfile
import gc

# Enable automatic garbage collection.
gc.enable()

chdir(dirname(abspath(sys.path[0])))

#In windows . is not on python path.
import sys
sys.path.append(".")

#Twisted
from twisted.application.service import Application

# Local
from ecagent.config import SMConfigObj
from ecagent.agent import SMAgentXMPP
import ecagent.twlogging as log

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
config_file = join(dirname(__file__), './config/ecagent.cfg')

if not isfile(config_file):
    raise Exception("Config file not found: "+config_file)

config = SMConfigObj(config_file)

application = Application("ecagent")

if (config.checkConfig()):
    log.setup(application, config['Log'])
    agent = SMAgentXMPP(config)

else:
    print 'Error in configuration'
    print 'Agent will now quit'
    sys.exit(-1)