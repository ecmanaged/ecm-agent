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
import os
import gc
import sys
import stat
import random

# Twisted
from twisted.application.service import Application

root_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(root_dir)

if root_dir not in sys.path:
    sys.path.append(root_dir)

# In windows . is not on python path.
if "." not in sys.path:
    sys.path.append(".")

# Local
from ecagent.config import SMConfigObj
from ecagent.agent import SMAgent
import ecagent.twlogging as log

# Enable automatic garbage collection.
gc.enable()

# Check for other processes running
pid_file = os.path.join(os.path.sep, root_dir, 'twistd.pid')

if os.path.exists(pid_file):
    from psutil import pid_exists

    pid = open(pid_file).read()
    if pid and pid_exists(int(pid)):
        print 'Sorry, found another agent running'
        print 'Agent will now quit'
        sys.exit(-1)

# Write my pid
open(pid_file, 'w').write(str(os.getpid()))

# Start agent and setup logging
config_file = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.cfg')

os.chmod(config_file, stat.S_IRWXU)

if not os.path.isfile(config_file):
    raise Exception("Config file not found: " + config_file)

config = SMConfigObj(config_file)

# Start agent and setup logging
application = Application("ecagent")
log.setup(application, config['Log'])

agent = SMAgent(config)
