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

#In windows . is not on python path.
import sys
sys.path.append(".")

import random
from os.path import join, dirname
from uuid import getnode

#Local
from configobj import ConfigObj

if len(sys.argv) == 2:
    uuid = sys.argv[1]
else:
    print "Usage: "
    print "%s XXXX-XXXX-XXX-XXX" % sys.argv[0]
    print "where XXXX-XXXX-XXX-XXX is the manualy set up UUID for the agent."
    sys.exit(1)


#Parse config file or end execution
config_filename = join(dirname(__file__), './config/ecagent.cfg')
try:
    config = ConfigObj(config_filename)
except:
    print 'Unable to read the config file at %s' % config_filename
    print 'Agent will now quit'
    sys.exit(2)

config['XMPP']['user'] = '%s@%s' % (uuid, config['XMPP']['host'])
config['XMPP']['password'] = hex(random.getrandbits(128))[2:-1]
config['XMPP']['mac'] = str(getnode())
config['XMPP']['manual'] = True
config.write()

print 'Manual configuration override succeeded.'
