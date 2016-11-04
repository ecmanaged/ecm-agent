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

# Twisted
from twisted.application.service import Application

try:
    root_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:  # We are the main py2exe script, not a module
    import sys
    root_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

os.chdir(root_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# In windows . is not on python path.
if "." not in sys.path:
    sys.path.append(".")

# Local
from core.config import ECMConfig
from core.agent import ECMAgent
import core.logging as log

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
config_file_init = os.path.join(os.path.sep, root_dir, 'config', 'ecagent.cfg.init')

# rename config/ecagent.cfg.init to config/ecagent.cfg for fresh install
if os.path.exists(config_file) and os.path.exists(config_file_init):
    os.remove(config_file_init)

if os.path.exists(config_file_init) and not os.path.exists(config_file):
    os.rename(config_file_init, config_file)

if not os.path.isfile (config_file):
    print "Failed to find config file."
    sys.exit(-1)

os.chmod(config_file, stat.S_IRWXU)

if not os.path.isfile(config_file):
    raise Exception("Config file not found: " + config_file)

config = ECMConfig(config_file)

# Start agent and setup logging
application = Application("ecagent")
log.setup(application, config['Log'])

agent = ECMAgent(config)
