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

import os

from subprocess import Popen, PIPE
from time import time

# Local
from __plugin import ECMPlugin
from __helper import is_integer, is_windows

CRITICAL = 2
COMMAND_GET_INTERVAL = 60
COMMAND_CACHE_OFFSET = 10
COMMAND_GLUE = ':::'

MY_PATH = os.path.dirname(os.path.abspath(__file__))
ENABLED_MONITORS_PATH = os.path.join(MY_PATH, '../monitor/enabled')
MONITORS_CACHE_PATH = os.path.join(MY_PATH, '../monitor/_cache')
MONITORS_CACHE_EXT = 'cache'
MONITOR_RUNAS_USER = ''

class ECMMonitor(ECMPlugin):
    def cmd_monitor_get(self, *argv, **kwargs):
        """
        Runs monitor commands from monitor path
        """
        monitor_path = ENABLED_MONITORS_PATH
        retval = []
        to_execute = []

        # Create dirs if necessary
        self._check_path(ENABLED_MONITORS_PATH)
        self._check_path(MONITORS_CACHE_PATH)

        if not os.path.isdir(monitor_path):
            return retval

        # Foreach custom monitor
        for root, dirs, files in os.walk(monitor_path):
            for f in files:
                if f.endswith(MONITORS_CACHE_EXT):
                    continue
                if f.endswith('~'):
                    continue
                
                interval = self._interval_from_path(root)
                script = os.path.join(root, f)

                # Read last result from cache
                from_cache = self._read_cache(script, interval + COMMAND_CACHE_OFFSET)
                if from_cache:
                    retval.append(self._parse_script_name(f) + COMMAND_GLUE + str(interval) + COMMAND_GLUE + from_cache)
                    
                # Execute script if cache wont be valid on next command_get execution
                if not self._read_cache(script, interval - COMMAND_GET_INTERVAL):
                    to_execute.append(script)
                    
        for script in to_execute:
            _run_background_file(script)

        return retval
        
    @staticmethod
    def _interval_from_path(my_path):
        interval = os.path.split(my_path)[-1]
        if not is_integer(interval):
            interval = COMMAND_GET_INTERVAL
            
        return int(interval)

    @staticmethod
    def _parse_script_name(name):
        components = str(name).split('.')
        if components[-1] in ['py', 'pl', 'sh', 'rb', 'bash', 'cmd', 'bat']:
            del components[-1]

        return '.'.join(components).upper()


    @staticmethod
    def _check_path(path):
        if not os.path.isdir(path):
            os.makedirs(path)

    @staticmethod
    def _read_cache(command, cache_time):
        cache_file = os.path.join(MONITORS_CACHE_PATH, os.path.basename(command) + '.' + MONITORS_CACHE_EXT)
        content = ''
        if os.path.isfile(cache_file):
            # check updated cache
            modified = os.path.getmtime(cache_file)
            if (modified + cache_time) < time():
                os.remove(cache_file)
                return None

            # Return cache content
            f = open(cache_file, 'r')
            for line in f.readlines():
                content += line
            f.close()

        return content


def _alarm_handler(signum, frame):
    os._exit()


def _write_cache(script, retval, std_out):
    # Write to cache file
    cache_file = os.path.abspath(
        os.path.join(MONITORS_CACHE_PATH, script + '.' + MONITORS_CACHE_EXT)
    )
    f = open(cache_file, 'w')
    f.write("%s%s%s" % (retval, COMMAND_GLUE, std_out))
    f.close()


def _run_background_file(script):
    """Detach a process from the controlling terminal and run it in the
    background as a daemon.
    """
    workdir = os.path.dirname(script)
    fullpath = os.path.abspath(script)
    
    try:
        pid = os.fork()
    except OSError:
        raise Exception

    if pid == 0:
        os.setsid()
        try:
            pid = os.fork()
        except OSError:
            raise Exception

        if pid == 0:
            os.chdir(workdir)
            os.umask(0)
        else:
            os._exit(0)
    else:
        # parent returns
        return

    os.dup2(0, 1)
    os.dup2(0, 2)

    # Set alarm
    import signal
    signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(300)

    # Write timeout to cache file
    _write_cache(os.path.basename(fullpath), CRITICAL, 'Timeout')

    try:
        command = [fullpath]

        if MONITOR_RUNAS_USER and not is_windows():
            command = ['su', MONITOR_RUNAS_USER, '-c', ' '.join(map(str, fullpath))]

        p = Popen(
            command,
            env=os.environ.copy(),
            bufsize=0,
            stdin=PIPE, stdout=PIPE, stderr=PIPE,
            universal_newlines=True,
            close_fds=(os.name == 'posix')
        )

        std_out, std_err = p.communicate()
        retval = p.wait()

        _write_cache(os.path.basename(fullpath), retval, std_out)

    except Exception, e:
        _write_cache(os.path.basename(fullpath), CRITICAL, e.message)
        pass

    os._exit(0)


ECMMonitor().run()
