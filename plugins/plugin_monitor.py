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

import simplejson as json
from base64 import b64decode
from subprocess import Popen, PIPE
from time import time

# Local
import __helper as ecm
from __plugin import ECMPlugin
from __mplugin import MPlugin

CRITICAL = 2

COMMAND_TIMEOUT = 55
COMMAND_INTERVAL = 60
GLUE = ':::'

MY_PATH = os.path.dirname(os.path.abspath(__file__))
MPLUGIN_PATH = os.path.join(MY_PATH, '../monitor/mplugin')
CPLUGIN_PATH = os.path.join(MY_PATH, '../monitor/custom')

CACHE_PATH = os.path.join(MY_PATH, '../monitor/.cache')
CACHE_FILE_EXTENSION = 'cache'
CACHE_FILE_EXPIRES = 86400
CACHE_SOFT_TIME = 10

IGNORE_EXT = ('cache','~','pyc')

class ECMMonitor(ECMPlugin):
    def cmd_monitor_get(self, *argv, **kwargs):
        """
        Runs monitor commands from monitor path
        """
        
        config = None
        b64_config = kwargs.get('config', None)
        
        try: config = json.loads(b64decode(b64_config))
        except: pass
        
        retval = []
        to_execute = []

        # Create dirs if necessary
        self._check_path(MPLUGIN_PATH)
        self._check_path(CPLUGIN_PATH)
        self._check_path(CACHE_PATH)
        
        # Clean old cache files
        self._cache_clean()

        if not os.path.isdir(MPLUGIN_PATH):
            return retval
            
        # Foreach plugin inside mplugins and custom
        for plugin_path in [MPLUGIN_PATH, CPLUGIN_PATH]:
            if not os.path.isdir(plugin_path):
                continue
                
            for root, dirs, files in os.walk(plugin_path):
                if plugin_path is MPLUGIN_PATH: files = files + dirs
                for f in files:
                    # Ignore som file extensions
                    if f.endswith((IGNORE_EXT)):
                        continue
                        
                    # Set default interval or read from path name
                    runas = None
                    script = os.path.join(root, f)
                    interval = self._interval_from_path(root)
                    
                    # If is a directory search for script
                    if plugin_path is MPLUGIN_PATH:
                        current_dir = os.path.join(root, f)
                        for _, _, files2 in os.walk(current_dir):
                            for f2 in files2:
                                if not f2.endswith('~') and f2.startswith(f):
                                    script = os.path.join(current_dir, f2)
                                    
                                    # Read data from plugin config
                                    mplugin = MPlugin(current_dir)
                                    
                                    runas = mplugin.data.get('runas',None)
                                    interval = mplugin.data.get('interval',interval)
                                    
                                    # Update config                                    
                                    if config:
                                        mplugin.write_config(config.get(mplugin.id))
                                        
                                    break
                       
                    # Check is valid and executable 
                    if not script or not os.access(script, os.X_OK):
                        continue
                    
                    # Read last result from cache (even if void)
                    from_cache = self._cache_read(script, interval + CACHE_SOFT_TIME)
                    retval.append(self._parse_script_name(f) + GLUE + str(interval) + GLUE + from_cache)
                    
                    # Execute script if cache wont be valid on next command_get execution
                    if not self._cache_read(script, interval - COMMAND_INTERVAL):
                        to_execute.append({'script' : script, 'runas': runas})
                        
        for data in to_execute:
            _run_background_file(data['script'],data['runas'])
            
        return retval
        
    def cmd_monitor_plugin_install(self, *argv, **kwargs):
        """
        Installs a plugin [url=plugin_url]
        """
        
        url = kwargs.get('url', None)
        
        if not url:
            raise ecm.InvalidParameters(self.cmd_set_info.__doc__)
        
        try: content = ecm.get_url(url)
        except: pass
        
        if not content:
            raise Exception("Unable to get URL: %s" %url)
            
        try: 
            plugin = json.loads(content)
        except:
            raise Exception("Invalid data recieved")

        id = plugin.get('id')
        runas = plugin.get('runas')
        
        arg_config = plugin.get('config')
        arg_script_b64 = plugin.get('script')
        
        script = None
        try: script = b64decode(arg_script_b64)
        except: pass
        
        config = {
            'id': id,
            'runas': runas,
            'name': plugin.get('name'),
            'interval': plugin.get('interval'),
            'config': arg_config
        }
        
        if id and config and script:
            mplugin = MPlugin(MPLUGIN_PATH)
            if mplugin.install(id,config,script):
                # Installation ok, run it
                script_file = os.path.abspath(os.path.join(MPLUGIN_PATH,id,id))
                _run_background_file(script_file,runas)
            
                return True
            
        return False

    def cmd_monitor_plugin_uninstall(self, *argv, **kwargs):
        """
        Uninstalls a plugin [id=plugin_id]
        """
        
        plugin_id = kwargs.get('id', None)
        
        if not plugin_id:
            raise ecm.InvalidParameters(self.cmd_set_info.__doc__)
        
        mplugin = MPlugin(MPLUGIN_PATH)
        return mplugin.uninstall(plugin_id)
        
    @staticmethod
    def _interval_from_path(my_path):
        interval = os.path.split(my_path)[-1]
        if not ecm.is_integer(interval):
            interval = COMMAND_INTERVAL
            
        return int(interval)

    @staticmethod
    def _parse_script_name(name):
        components = str(name).split('.')
        if len(components) > 1:
            del components[-1] # Delete ext

        return '.'.join(components)


    @staticmethod
    def _check_path(path):
        if not os.path.isdir(path):
            os.makedirs(path)

    @staticmethod
    def _cache_read(command, cache_time):
        cache_file = os.path.join(CACHE_PATH, os.path.basename(command) + '.' + CACHE_FILE_EXTENSION)
        content = ''
        if os.path.isfile(cache_file):
            # check updated cache
            modified = os.path.getmtime(cache_file)
            if (modified + cache_time) < time():
                os.remove(cache_file)
                return content

            # Return cache content
            f = open(cache_file, 'r')
            for line in f.readlines():
                content += line
            f.close()

        return content
        
    @staticmethod
    def _cache_clean():
        for f in os.listdir(CACHE_PATH):
            file = os.path.join(CACHE_PATH,f)
            modified = os.path.getmtime(file)
            if modified < (time() - CACHE_FILE_EXPIRES):
                os.remove(file)


def _alarm_handler(signum, frame):
    os._exit()


def _write_cache(script, retval, std_out):
    # Write to cache file
    cache_file = os.path.abspath(
        os.path.join(CACHE_PATH, script + '.' + CACHE_FILE_EXTENSION)
    )
    f = open(cache_file, 'w')
    f.write("%s%s%s" % (retval, GLUE, std_out))
    f.close()


def _run_background_file(script, run_as=None):
    """Detach a process from the controlling terminal and run it in the
    background as a daemon.
    """
    workdir = os.path.dirname(script)
    fullpath = os.path.abspath(script)
    
    script_name = os.path.basename(fullpath)
    
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
    signal.alarm(COMMAND_TIMEOUT)
    
    # Write timeout to cache file
    _write_cache(script_name, CRITICAL, 'Timeout')

    try:
        command = [fullpath]
        
        import sys
        sys.path.append(MY_PATH)
        
        env = os.environ.copy()
        env['PYTHONPATH'] = MY_PATH + ':' + env.get('PYTHONPATH', '')
        
        if run_as and not ecm.is_windows():
            # don't use su - xxx or env variables will not be available
            command = ['su', run_as, '-c', ' '.join(map(str, fullpath))]

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

        _write_cache(script_name, retval, std_out)

    except Exception, e:
        _write_cache(script_name, CRITICAL, e.message)
        pass

    os._exit(0)


ECMMonitor().run()
