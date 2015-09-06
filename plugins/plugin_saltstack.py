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

from tempfile import mkdtemp
from shutil import rmtree
from base64 import b64decode

# Local
from __plugin import ECMPlugin
import __helper as ecm

DEFAULT_SALT_PATH = '/srv/salt'
DEFAULT_SALT_PATH_WINDOWS = 'C:\ECM\SALTSTACK\salt'

DEFAULT_PILLAR_PATH = '/srv/pillar'
DEFAULT_PILLAR_PATH_WINDOWS = 'C:\ECM\SALTSTACK\pillar'

BOOTSTRAP = 'http://bootstrap.ecmanaged.com/saltstack/linux'
BOOTSTRAP_ALT = 'http://bootstrap.saltstack.org'

BOOTSTRAP_WINDOWS = 'http://bootstrap.ecmanaged.com/saltstack/windows'
BOOTSTRAP_WINDOWS_ALT = 'http://bootstrap.saltstack.org'

TOP_CONTENT = """base:
  '*':
    - ecmanaged
"""

class ECMSaltstack(ECMPlugin):
    def cmd_saltstack_available(self, *argv, **kwargs):
        """ Checks if saltstack commands are available
        """
        return bool(self._is_available())

    def cmd_saltstack_install(self, *argv, **kwargs):
        """ Installs saltstack using bootstrap scripts
        """
        if self._is_available(): return True

        bootstrap = BOOTSTRAP
        bootstrap_file = 'bootstrap.sh'

        if ecm.is_win():
            bootstrap = BOOTSTRAP_WINDOWS
            bootstrap_file = 'bootstrap.ps1'

        if not self._install(bootstrap,bootstrap_file):
            # Try alternative bootstrap
            bootstrap = BOOTSTRAP_ALT
            if ecm.is_win():
                bootstrap = BOOTSTRAP_WINDOWS_ALT

            if not self._install(bootstrap,bootstrap_file):
                raise Exception("Unable to install saltstack")

        return True

    def cmd_saltstack_apply(self, *argv, **kwargs):
        """
        Apply a saltstack manifest
        Syntax: saltstack.apply[recipe_code,pillar_code,envars,facts]
        """
        recipe_b64 = kwargs.get('recipe_code', None)
        pillar_b64 = kwargs.get('pillar_code', None)
        metadata = kwargs.get('metadata', None)

        if not recipe_b64:
            raise ecm.InvalidParameters(self.cmd_saltstack_apply.__doc__)

        saltstack_cmd = self._is_available()
        if not saltstack_cmd:
            raise Exception('Saltstack no available')

        # Get default paths
        default_path = DEFAULT_SALT_PATH
        if ecm.is_win():
            default_path = DEFAULT_SALT_PATH_WINDOWS
        module_path = kwargs.get('module_path', default_path)

        default_pillar_path = DEFAULT_PILLAR_PATH
        if ecm.is_win():
            default_pillar_path = DEFAULT_PILLAR_PATH_WINDOWS
        pillar_path = kwargs.get('pillar_path', default_pillar_path)

        # Set environment variables before execution
        envars = ecm.metadata_to_env(metadata_b64=metadata)

        # Update metadata
        ecm.write_metadata(metadata_b64=metadata)

        try:
            # Create top file
            self._create_top_file(module_path)

            recipe_file = module_path + '/ecmanaged.sls'
            ecm.file_write(recipe_file, b64decode(recipe_b64))

            if pillar_b64:
                self._create_top_file(pillar_path)
                pillar_file = pillar_path + '/ecmanaged.sls'
                ecm.file_write(pillar_file, b64decode(pillar_b64))

        except:
            raise Exception("Unable to write recipe")

        try:
            # salt-call state.highstate
            command = [saltstack_cmd, 'state.highstate', '--local', '--no-color', '-l debug']

            out, stdout, stderr = ecm.run_command(command, envars=envars, workdir=module_path)
            return ecm.format_output(out, stdout, stderr)

        except Exception as e:
            raise Exception("Error running saltstack state.highstate: %s" % e)

    def _create_top_file(self, path):
        top_file = path + '/top.sls'
        ecm.file_write(top_file, TOP_CONTENT)

    def _is_available(self):
        """ it's salt-call on path?
        """
        if ecm.is_win():
            return ecm.which('salt-call.exe')
        return ecm.which('salt-call')

    def _install(self, bootstrap_url, bootstrap_file = 'bootstrap.sh'):
        """ Installs saltstack using bootstrap url
        """

        tmp_dir = mkdtemp()
        bootstrap_file = tmp_dir + '/' + bootstrap_file
        ecm.download_file(bootstrap_url, bootstrap_file)

        # wget -O - http://bootstrap.saltstack.org | sudo sh

        # Options:
        #-h  Display this message
        #-v  Display script version
        #-n  No colours.
        #-D  Show debug output.
        #-c  Temporary configuration directory
        #-g  Salt repository URL. (default: git://github.com/saltstack/salt.git)
        #-k  Temporary directory holding the minion keys which will pre-seed the master.
        #-M  Also install salt-master
        #-S  Also install salt-syndic
        #-N  Do not install salt-minion
        #-X  Do not start daemons after installation
        #-C  Only run the configuration function. This option automatically bypasses any installation.
        #-P  Allow pip based installations. On some distributions the required salt packages or its dependencies are not available as a package for that distribution. Using this flag allows the script to use pip as a last resort method. NOTE: This works for functions which actually implement pip based installations.
        #-F  Allow copied files to overwrite existing(config, init.d, etc)
        #-U  If set, fully upgrade the system prior to bootstrapping salt
        #-K  If set, keep the temporary files in the temporary directories specified with -c and -k.

        if ecm.file_read(bootstrap_file):
            envars = {'DEBIAN_FRONTEND': 'noninteractive'}
            ecm.run_file(bootstrap_file, args=['-n', '-P', '-X'], envars=envars)

        rmtree(tmp_dir)
        return bool(self._is_available())


ECMSaltstack().run()
