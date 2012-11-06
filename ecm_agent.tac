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
from ecm_agent.config import SMConfigObj
from ecm_agent.agent import SMAgent
import ecm_agent.twlogging as l

#Parse config file or end execution
try:
    config_filename = join(dirname(__file__), 'ecm_agent.cfg')
    config = SMConfigObj(config_filename)
except:
    print 'Unable to read the config file at %s' % config_filename
    print 'Agent will now quit'
    sys.exit(-1)

#Start agent and setup logging
application = Application("ecm_agent")
l.setup(application, config['Log'])
agent = SMAgent(config)
