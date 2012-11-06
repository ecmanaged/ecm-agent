#Twisted
from twisted.python import log
from twisted.python.logfile import LogFile

#Python
from os.path import split, exists
from os import makedirs
from sys import modules


def setup(app, config):
    loglevels = [ 
        'debug',  
        'info',    
        'warning', 
        'error',   
        'critical',
        ]

    if 'log_level' in config and config['log_level'] in loglevels:
        log_level = loglevels.index(config['log_level'])
    else:
        warning('loglevel invalid or missing, falling back to "info"')
        log_level = 3

    #Hack to speed up disabled logging methods
    modname = globals()['__name__']
    module = modules[modname]
    c = 0
    while c < log_level:
        setattr(module, loglevels[c], _blackhole)
        c += 1

    if 'log_to_file' in config and config.as_bool('log_to_file'):
        logfile = makeLogFile(config)
        app.setComponent(log.ILogObserver, log.FileLogObserver(logfile).emit)


def makeLogFile(config):
        log_dir, log_file = split(config['log_path'])

        if not log_dir:  
            log_dir = '.'
            
        if not exists(log_dir):
            makedirs(log_dir)

        if 'max_log_file_size' in config:
            max_log_file_size = config.as_int('max_log_file_size') * 1024
        else:
            max_log_file_size = 1024 ** 2  # 1MB log files by default

        if 'max_log_files' in config:
            max_log_files = config.as_int('max_log_files')
        else:
            max_log_files = 1  # 1 rotated file by default



        logfile = LogFile(log_file, log_dir,
                          rotateLength=max_log_file_size,
                          maxRotatedFiles=max_log_files)
        return logfile

def _blackhole(message):
    """
    Auxiliar method that does nothing, used to speed up discarded log entries
    """
    pass


def debug(message):
    log.msg('DEBUG: ' + message)


def info(message):
    log.msg('INFO: ' + message)


def warn(message):
    warning(message)


def warning(message):
    log.msg('WARNING: ' + message)


def error(message):
    log.msg('ERROR: ' + message)


def critical(message):
    log.msg('CRITICAL: ' + message)
