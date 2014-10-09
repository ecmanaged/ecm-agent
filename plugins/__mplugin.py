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
COUNTER_FILE_NAME = 'counter.dat'
LOG_FILE_NAME = 'mplugin.log'

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
from os import makedirs, chmod

import logging 
log = logging


def _timeout(signum, frame):
    from os import _exit
    _exit(TIMEOUT)


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
            
        # Get counters information
        self.counters = self._counters_read()

        # Get name from config or filename
        self.name = str(self.data.get('name', basename(sys.argv[0])))

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
            mtime = getmtime(counters_file)
            valid_time = time() - self.interval - 30
            
            if mtime > valid_time:
                return self._from_json(self._file_read(counters_file))
            else:
                log.warning("Ignored counters file, is too old")
            
        return {}
    
    def _counters_write(self):
        counters_file = join(self.path, COUNTER_FILE_NAME)
        self._file_write(counters_file, self._to_json(self.counters))

    def write_config(self, config=None):
        if not config or not self._is_dict(config):
            return

        # Same config?
        json_config = self._to_json(config)
        if self.data.get('.raw', '') == json_config:
            log.debug('No need to update config')
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
            
        # Write counters
        self._counters_write()

        print str(
            self._to_json({'id': self.id, 'name': self.name, 'message': message, 'data': data, 'metrics': metrics}))
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

    # Helper functions

    def _sanitize(self, obj):
        if not self._is_dict(obj):
           return obj
 
        for idx in obj:
            if self._is_dict(obj[idx]):
                obj[idx] = self._sanitize(obj[idx])
            elif self._is_list(obj[idx]):
                obj[idx] = self._sanitize(obj[idx])
            elif self._is_string:
                obj[idx] = str(obj[idx])
                pass
            elif self._is_number(obj[idx]):
                pass
            else:
                obj[idx] = str(obj[idx])
                
        return obj

    def _gauge(self, value):
        """
            value divided by the step interval
        """
        retval = 0
        if value:
            retval = value / self.interval

        return retval

    def _counter(self, value, index):
        """
            Saves a value and returns difference
        """
        retval = 0
        if self.counters.get(index):
            retval = value - self.counters[index]
            if retval < 0: retval = 0

        # Save counter
        self.counters[index] = value

        return retval

    def _counters(self, obj, index):
        """
            Save values for metrics, compare with latest values and return difference
            convert counter values to average values
        """
        if not self.counters.get(index):
            self.counters[index] = {}

        current_counter = self.counters[index]
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
                            retval[elm][elm2] = diff

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
                        retval[elm] = diff

        self.counters[index] = new_counter

        return retval

    def _to_gb(self, n):
        return self._convert_bytes(n, 'G')

    def _to_mb(self, n):
        return self._convert_bytes(n, 'M')

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
            retval = json.dumps(elm)
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
            return "0B"

        symbols = ('k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10

        for s in reversed(symbols):
            if to == s:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)

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
