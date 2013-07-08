##################
# Dependencies:
#
# ConfigObj
# twisted
# twisted-words
#
##################

#In windows . is not on python path.
import sys
sys.path.append(".")

from sys import exit
from os.path import join, dirname

#Twisted
from twisted.internet import reactor
from twisted.application.service import Application

#Local
from ecagent.config import SMConfigObj
from ecagent.agent import SMAgent
import ecagent.twlogging as l

#Parse config file or end execution
try:
    config_filename = join(dirname(__file__), 'ecagent.cfg')
    config = SMConfigObj(config_filename)
except:
    print 'Unable to read the config file at %s' % config_filename
    print 'Agent will now quit'
    sys.exit(-1)

#Start agent and setup logging
application = Application("ecagent")
l.setup(application, config['Log'])
agent = SMAgent(config)
