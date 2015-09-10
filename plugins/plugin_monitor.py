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
import sys

import simplejson as json
from base64 import b64decode
from subprocess import Popen, PIPE
from time import time, sleep
from __helper import pip_install_single_package
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


class ECMMonitor(ECMPlugin):
    def cmd_monitor_get(self, *argv, **kwargs):
        """
        Runs monitor commands from monitor path
        """
        
        config = None
        b64_config = kwargs.get('config', None)
        
        try:
            config = json.loads(b64decode(b64_config))
        except:
            pass
        
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
                
            for p_path in os.listdir(plugin_path):
                p_path = os.path.join(plugin_path, p_path)

                # Skip disabled plugins
                if not os.path.isdir(p_path):
                    continue

                # Skip disabled plugins
                if os.path.basename(p_path).startswith('.'):
                    continue
                        
                runas = None
                scripts = []
                interval = COMMAND_INTERVAL

                # Search for plugin files
                if plugin_path == MPLUGIN_PATH:
                    mplugin = MPlugin(p_path)
                        
                    runas = mplugin.data.get('runas', None)
                    interval = mplugin.data.get('interval', interval)

                    script = os.path.join(plugin_path, p_path, mplugin.id)
                        
                    if not os.path.exists(script):
                        script += '.py'
                        
                    if not os.path.exists(script):
                        continue

                    # Add as valid mplugin script
                    scripts.append(script)
                                    
                    # Executable plugin base
                    if not os.access(script, os.X_OK):
                        os.chmod(script, 0755)
                                    
                    # Update config                                    
                    if config:
                        mplugin.write_config(config.get(mplugin.id))
                    
                # Custom plugins path
                elif plugin_path == CPLUGIN_PATH:
                    # Set default interval or read from path name
                    interval = self._interval_from_path(p_path)

                    for filename in os.listdir(p_path):
                        _tmp = os.path.join(plugin_path, p_path, filename)
                        if os.access(_tmp, os.X_OK):
                            scripts.append(_tmp)
                            
                for script in scripts:
                    # Read last result from cache (even if void)
                    from_cache = self._cache_read(script, interval + CACHE_SOFT_TIME)
                    retval.append(self._parse_script_name(script) + GLUE + str(interval) + GLUE + from_cache)
                    
                    # Execute script if cache wont be valid on next command_get execution
                    if not self._cache_read(script, interval - COMMAND_INTERVAL):
                        to_execute.append({'script': script, 'runas': runas})
                        
        for data in to_execute:
            _run_background_file(data['script'], data['runas'])

        return retval
        
    def cmd_monitor_plugin_install(self, *argv, **kwargs):
        """
        Installs a plugin [url=plugin_url]
        """
        
        url = kwargs.get('url', None)
        content = None
        
        if not url:
            raise ecm.InvalidParameters(self.cmd_monitor_plugin_install.__doc__)
        
        try:
            content = ecm.get_url(url)
        except:
            pass
        
        if not content:
            raise Exception("Unable to get URL: %s" % url)
            
        try: 
            plugin = json.loads(content)
        except:
            raise Exception("Invalid data received")

        id = plugin.get('id')
        runas = plugin.get('runas')
        
        arg_config = plugin.get('config')
        arg_script_b64 = plugin.get('script')

        arg_requirements = plugin.get('requirements', None)

        if arg_requirements:
            requirements = arg_requirements.keys()

        for item in requirements:
            result = pip_install_single_package(item)

            if not result:
                return False
        
        script = None
        try:
            script = b64decode(arg_script_b64)
        except:
            pass
        
        config = {
            'id': id,
            'runas': runas,
            'name': plugin.get('name'),
            'interval': plugin.get('interval'),
            'version': plugin.get('version'),
            'config': arg_config
        }
        
        if id and config and script:
            mplugin = MPlugin(MPLUGIN_PATH)
            if mplugin.install(id, config, script):
                # Installation ok, run it
                script_file = os.path.abspath(os.path.join(MPLUGIN_PATH, id, id))
                _run_background_file(script_file, runas)
            
                return True
            
        return False

    def cmd_monitor_plugin_uninstall(self, *argv, **kwargs):
        """
        Uninstalls a plugin [id=plugin_id]
        """

        plugin_id = kwargs.get('id', None)
        
        if not plugin_id:
            raise ecm.InvalidParameters(self.cmd_monitor_plugin_uninstall.__doc__)
        
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
        name = os.path.basename(name)
        components = str(name).split('.')
        if len(components) > 1:
            del components[-1]  # Delete ext

        return '.'.join(components)

    @staticmethod
    def _check_path(path):
        if not os.path.isdir(path):
            os.makedirs(path)

    @staticmethod
    def _cache_read(command, cache_time):
        cache_file = os.path.join(CACHE_PATH, os.path.basename(command) + '.' + CACHE_FILE_EXTENSION)
        content = ''

        # check updated cache
        if os.path.isfile(cache_file):
            modified = os.path.getmtime(cache_file)
    
            if (modified + cache_time) < time():
                # Invalid cache file
                os.remove(cache_file)
            
            else:
                # Return cache content
                f = open(cache_file, 'r')
                for line in f.readlines():
                    content += line
                f.close()

        return content
        
    @staticmethod
    def _cache_clean():
        for f in os.listdir(CACHE_PATH):
            cachefile = os.path.join(CACHE_PATH, f)
            modified = os.path.getmtime(cachefile)
            if modified < (time() - CACHE_FILE_EXPIRES):
                os.remove(cachefile)


def _write_cache(script, retval, std_out):
    # Write to cache file
    cache_file = os.path.abspath(
        os.path.join(CACHE_PATH, script + '.' + CACHE_FILE_EXTENSION)
    )
    f = open(cache_file, 'w')
    f.write("%s%s%s" % (retval, GLUE, std_out))
    f.close()


def _run_background_file(script, run_as=None):
    fullpath = os.path.abspath(script)
    script_name = os.path.basename(fullpath)
    workdir = os.path.dirname(script)

    # Create child process and return if parent
    if ecm.fork(workdir):
        return

    # Write timeout to cache file
    _write_cache(script_name, CRITICAL, 'Timeout')
    
    try:
        command = [fullpath]
        sys.path.append(MY_PATH)
        
        env = os.environ.copy()
        env['PYTHONPATH'] = MY_PATH + ':' + env.get('PYTHONPATH', '')
        
        retval, stdout, stderr = ecm.run_command(command, runas=run_as, envars=env)
        _write_cache(script_name, retval, stdout)

    except Exception, e:
        _write_cache(script_name, CRITICAL, e.message)
        pass

    sys.exit(0)


ECMMonitor().run()
