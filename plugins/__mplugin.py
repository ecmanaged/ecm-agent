#!/usr/bin/env python

# -*- coding:utf-8 -*-

# Copyright (C) 2012 Juan Carlos Moreno <juancarlos.moreno at ecmanaged.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

CONFIG_FILE_NAME = 'data.json'
LOG_FILE_NAME = 'mplugin.log'

COUNTER_FILE_NAME = '.counter.dat'
TOUCH_FILE_NAME = '.touch'

INTERVAL_INDEX = '__interval__'

CHECK_TIMEOUT = 55
DEFAULT_INTERVAL = 60

# Monitor status
OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3
TIMEOUT = 254

import sys
import signal

from os.path import dirname, abspath, join, exists, basename, getmtime
from time import time
from os import makedirs, chmod, utime

import logging 
log = logging


def _timeout(signum, frame):
    sys.exit(TIMEOUT)


class MPlugin:
    def __init__(self, plugin_path=None):

        # set alarm for timeout
        signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(CHECK_TIMEOUT)

        if plugin_path:
            self.path = abspath(plugin_path)

        else:
            self.path = abspath(dirname(sys.argv[0]))
            
        # Configure log
        if self.path:
            log.basicConfig(
                filename=join(self.path, LOG_FILE_NAME),
                format='%(levelname)s:%(message)s',
                level=log.DEBUG
            )
        
        # Read configuration
        self.data = self._read_config()

        # Build config hash
        self.config = {}
        for idx in self.data.get('config', {}).keys():
            self.config[idx] = self.data.get('config').get(idx, {}).get('value', None)
            
        # set id and interval
        self.interval = self.data.get('interval', DEFAULT_INTERVAL)
        self.id = str(self.data.get('id', None))
            
        # Get name from config or filename
        self.name = str(self.data.get('name', basename(sys.argv[0])))
        
        # Initialize variables for counters and intervals
        self._time_start = time()
        self._time_interval = None
        self._counters = None

    def write_config(self, config=None):
        if not config or not self._is_dict(config):
            return

        # Same config?
        json_config = self._to_json(config)
        if self.data.get('.raw', '') == json_config:
            return

        # Read from configfile
        config_file = join(self.path, CONFIG_FILE_NAME)
        if self.path in config_file:
            self._file_write(config_file, json_config)
            log.info("Updating config")

        else:
            log.warning("Unable to find data file")

    def exit(self, state, data=None, metrics=None, message=None):
        if not message or not self._is_string(message):
            message = ' '.join([self.name, self._state_to_str(state)])

        if not data or not self._is_dict(data):
            data = {}

        if not metrics or not self._is_dict(metrics):
            metrics = {}
            
        # Sanitize
        data = self._sanitize(data)
        metrics = self._sanitize(metrics)
            
        # Write counters and interval
        self._counters_write()
        self._interval_write()
        
        print str(
            self._to_json({
                'id': self.id,
                'name': self._to_utf8(self.name),
                'message': self._to_utf8(message),
                'data': self._to_utf8(data),
                'metrics': self._to_utf8(metrics),
                'interval': self._get_time_interval()
            }).encode('utf-8')
        )
        
        sys.exit(state)

    def install(self, id, config, script):
        if not id or not config or not script:
            log.error("install: Invalid information received")
            return False

        plugin_path = abspath(join(self.path, id))
        if not exists(plugin_path):
            makedirs(plugin_path)

        self.path = plugin_path

        # Write new configuration
        self.write_config(config)

        # Write script
        script_file = join(plugin_path, id)
        self._file_write(script_file, script)

        chmod(script_file, 0755)
        return True

    def uninstall(self, id):
        plugin_path = abspath(join(self.path, id))
        move_to = abspath(join(self.path, '.' + id))

        # Exists and is inside our plugin path
        if exists(plugin_path) and self.path in plugin_path:
            from shutil import move

            move(plugin_path, move_to)
            return True

        return False
        
    def _read_config(self):
        retval = {}

        # Read from configfile
        config_file = join(self.path, CONFIG_FILE_NAME)
        if exists(config_file):
            content = self._file_read(config_file)
            retval = self._from_json(content)

            if not retval:
                log.warning("Invalid data in file: %s" % config_file)

            # Add raw config
            retval['.raw'] = content

        else:
            log.warning("Data file doesn't exists: %s" % config_file)

        return retval
        
    def _counters_read(self):
        counters_file = join(self.path, COUNTER_FILE_NAME)
        
        if exists(counters_file):
            # check last modification time
            mod_time = getmtime(counters_file)
            valid_time = time() - self.interval - 30
            
            if mod_time > valid_time:
                return self._from_json(self._file_read(counters_file))
            else:
                log.warning("Ignored counters file, is too old")
            
        return {}
    
    def _counters_write(self):
        if self._counters:
            counters_file = join(self.path, COUNTER_FILE_NAME)
            self._file_write(counters_file, self._to_json(self._counters))

    def _interval_write(self):
        touch_file = join(self.path, TOUCH_FILE_NAME)
        with open(touch_file, 'a'):
            utime(touch_file, (self._time_start, self._time_start))
            
    def _get_time_interval(self):
        """
        Read modification time from touch file and calculate
        interval from last run time

        @return: interval
        """
        if self._time_interval:
            return self._time_interval

        touch_file = join(self.path, TOUCH_FILE_NAME)


        retval = 1
        if exists(touch_file):
            tmp = int(time() - getmtime(touch_file))
            retval = tmp if tmp > 0 else 1

        self._time_interval = retval
        return retval

    # Helper functions
    def _sanitize(self, obj, recursion=0):
        if not self._is_dict(obj):
            return obj

        # Avoid recursion loop
        recursion += 1
        if recursion > 100:
            return obj

        for idx in obj:
            if self._is_dict(obj[idx]):
                obj[idx] = self._sanitize(obj[idx], recursion)

            elif self._is_list(obj[idx]):
                obj[idx] = self._sanitize(obj[idx], recursion)

            elif self._is_string:
                obj[idx] = str(obj[idx])
                pass

            elif self._is_number(obj[idx]):
                pass

            else:
                obj[idx] = str(obj[idx])

        return obj

    def gauge(self, value, interval=None):
        """
            value divided by the step interval
        """
        if not self._is_number(value):
            return value
            
        if not interval:
            interval = self._get_time_interval()

        return value / interval

    def counter(self, value, index, gauge=True):
        """
            Saves a value and returns difference
        """
        if not self._is_number(value):
            return value

        # Read counters
        if self._counters is None:
            self._counters = self._counters_read()
            
        # Get interval
        interval = self._get_counter_interval(index)

        retval = 0
        if self._counters.get(index):
            retval = self.gauge(value - self._counters[index], interval) if gauge else (value - self._counters[index])

        # Save counter
        self._counters[index] = value

        return retval if retval > 0 else 0

    def counters(self, obj, index, gauge=True):
        """
            Save values for metrics, compare with latest values and return difference
            convert counter values to average values
        """

        # Read counters
        if self._counters is None:
            self._counters = self._counters_read()

        if not self._counters.get(index):
            self._counters[index] = {}
            
        if not self._counters.get(INTERVAL_INDEX):
            self._counters[INTERVAL_INDEX] = {}

        # Read interval from last counter
        interval = self._get_counter_interval(index)

        current_counter = self._counters[index]
        new_counter = {}
        retval = {}
        
        if not self._is_dict(obj):
            return retval

        for elm in obj:
            new_counter[elm] = {}
            retval[elm] = {}
            
            if not current_counter.get(elm):
                current_counter[elm] = {}

            # Go deeper if is dict
            if self._is_dict(obj.get(elm)):
                for elm2 in obj[elm]:
                    new_counter[elm][elm2] = {}
                    retval[elm][elm2] = {}

                    # Update counter with current value
                    new_counter[elm][elm2] = obj[elm][elm2]
                    retval[elm][elm2] = 0

                    if current_counter[elm].get(elm2):
                        diff = obj[elm][elm2] - current_counter[elm].get(elm2)
                        if diff > 0:
                            retval[elm][elm2] = self.gauge(diff, interval) if gauge else diff

            elif self._is_list(obj.get(elm)):
                # Not supported
                continue

            else:
                # Update counter with current value
                new_counter[elm] = obj[elm]
                retval[elm] = 0

                # Return difference between last counter and current
                if current_counter.get(elm):
                    diff = obj[elm] - current_counter.get(elm)
                    if diff > 0:
                        retval[elm] = self.gauge(diff, interval) if gauge else diff

        # Update index and last used time
        self._counters[index] = new_counter
        self._counters[INTERVAL_INDEX][index] = time()

        return retval

    def _get_counter_interval(self, index):
        """
        @param index: counter index
        @return: interval calculated from last updated index
        """
        interval = self._get_time_interval()

        # Read counters
        if self._counters is None:
            self._counters = self._counters_read()

        if self._counters.get(INTERVAL_INDEX):
            if self._counters[INTERVAL_INDEX].get(index):
                last_time = self._counters[INTERVAL_INDEX][index]
                interval = int(time() - last_time)

        return interval
        
    def to_gb(self, n):
        return self._convert_bytes(n, 'G')

    def to_mb(self, n):
        return self._convert_bytes(n, 'M')

    def _to_utf8(self, elm):
        # FIXME: Do it recursive
        from codecs import decode
        if self._is_dict(elm):
            for key in elm.keys():
                if self._is_dict(elm[key]):
                    for key2 in elm[key].keys():
                        if self._is_string(elm[key][key2]):
                            elm[key][key2] = decode(elm[key][key2], 'utf-8', 'ignore')

                if self._is_string(elm[key]):
                    elm[key] = decode(elm[key], 'utf-8', 'ignore')

        return elm

    @staticmethod
    def _state_to_str(state):
        states = {
            OK: 'OK',
            WARNING: 'WARNING',
            CRITICAL: 'CRITICAL',
            UNKNOWN: 'UNKNOWN'
        }
        try:
            return states[state]
        except:
            return 'UNKNOWN'

    @staticmethod
    def _from_json(string):
        import simplejson as json

        retval = {}

        try:
            retval = json.loads(string)
        except:
            pass

        return retval
        
    @staticmethod
    def _to_json(elm):
        import simplejson as json

        retval = ''

        try:
            retval = json.dumps(elm).encode('utf8')
        except:
            pass

        return retval

    @staticmethod
    def _file_write(filepath, content):
        if content:
            try:
                f = open(filepath, 'w')
                f.write(content)
                f.close()

            except:
                pass

        return

    @staticmethod
    def _file_read(filepath):
        if exists(filepath):
            try:
                f = open(filepath, 'r')
                retval = f.read()
                f.close()
                return retval

            except:
                pass

        return

    @staticmethod
    def _convert_bytes(n, to=None):
        if n == 0:
            return "0"

        symbols = ('k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10

        for s in reversed(symbols):
            if to == s:
                value = float(n) / prefix[s]
                return '%.2f' % value

    @staticmethod
    def _is_dict(obj):
        return isinstance(obj, dict)

    @staticmethod
    def _is_list(obj):
        return isinstance(obj, list)

    @staticmethod
    def _is_string(obj):
        return isinstance(obj, str) or isinstance(obj, unicode)

    @staticmethod
    def _is_number(obj):
        return isinstance(obj, (int, long, float, complex))
        
    @staticmethod
    def is_win():
        if sys.platform.startswith("win32"):
            return True
            
        return False
