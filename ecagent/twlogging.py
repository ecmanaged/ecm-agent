# -*- coding:utf-8 -*-

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

from os.path import split, exists
from os import makedirs
from sys import modules

# Twisted imports
from twisted.python import log
from twisted.python.logfile import LogFile


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
        log_level = 1

    # Hack to speed up disabled logging methods
    modname = globals()['__name__']
    module = modules[modname]
    c = 0
    while c < log_level:
        setattr(module, loglevels[c], _blackhole)
        c += 1

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
