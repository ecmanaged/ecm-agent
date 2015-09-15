import logging

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances.keys():
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class LoggerManager(object):
    __metaclass__ = Singleton

    _loggers = {}

    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def getLogger(name=None):
        if not name:
            logging.basicConfig(filename='/opt/ecmanaged/ecagent/log/plugin.log', level=logging.DEBUG)
            return logging.getLogger()
        elif name not in LoggerManager._loggers.keys():
            logging.basicConfig(filename='/opt/ecmanaged/ecagent/log/plugin.log', level=logging.DEBUG)
            LoggerManager._loggers[name] = logging.getLogger(str(name))
        return LoggerManager._loggers[name]  