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

from base64 import b64decode
from tempfile import mkdtemp
from shutil import rmtree
import tarfile

# Local
from __plugin import ECMPlugin
import __helper as ecm

MODULES_PATH = '/etc/puppet/modules'
MODULES_PATH_WINDOWS = 'c:\ECM\puppet\modules'

BOOTSTRAP = 'http://bootstrap.ecmanaged.com/puppet/linux/'
BOOTSTRAP_ALT = 'http://bootstrap-devel.ecmanaged.com/puppet/linux/'

BOOTSTRAP_WINDOWS = 'http://bootstrap.ecmanaged.com/puppet/windows/'
BOOTSTRAP_WINDOWS_ALT = 'http://bootstrap-devel.ecmanaged.com/puppet/windows/'

class ECMPuppet(ECMPlugin):
    def cmd_puppet_available(self, *argv, **kwargs):
        """ Checks if puppet commands are available
        """
        return bool(self._is_available())

    def cmd_puppet_install(self, *argv, **kwargs):
        """ Installs saltstack using bootstrap scripts
        """
        if self._is_available():
            return True

        bootstrap = BOOTSTRAP
        bootstrap_file = 'bootstrap.sh'
        if ecm.is_windows():
            bootstrap = BOOTSTRAP_WINDOWS
            bootstrap_file = 'bootstrap.ps1'

        if not self._install(bootstrap, bootstrap_file):
            # Try alternative bootstrap
            bootstrap = BOOTSTRAP_ALT
            if ecm.is_windows():
                bootstrap = BOOTSTRAP_WINDOWS_ALT

            if not self._install(bootstrap,bootstrap_file):
                raise Exception("Unable to install puppet")

        return True

    def cmd_puppet_apply(self, *argv, **kwargs):
        """
        Syntax: puppet.appy[recipe_code,evars,facts]
        """
        recipe_base64 = kwargs.get('recipe_code', None)
        recipe_envars = kwargs.get('envars', None)
        recipe_facts = kwargs.get('facts', None)

        if not recipe_base64:
            raise ecm.InvalidParameters(self.cmd_puppet_apply.__doc__)

        # Set module path
        module_path = kwargs.get('module_path', None)
        if module_path is None:
            module_path = MODULES_PATH
            if ecm.is_windows():
                module_path = MODULES_PATH_WINDOWS

        # Set environment variables before execution
        envars = ecm.envars_decode(recipe_envars)
        facts = ecm.envars_decode(recipe_facts)

        # Update envars and facts file
        ecm.write_envars_facts(envars, facts)

        try:
            catalog = b64decode(recipe_base64)
        except:
            raise ecm.InvalidParameters("Unable to decode recipe")

        try:
            command = ['puppet',
                       'apply',
                       '--modulepath',
                       module_path,
                       '--detailed-exitcodes',
                       '--debug']

            out, stdout, stderr = ecm.run_command(command, stdin=catalog, envars=envars)
            ret = ecm.format_output(out, stdout, stderr)

            # exit code of '2' means there were changes
            if ret['out'] == 2: ret['out'] = 0
            if "\nError: " in ret['stderr']: ret['out'] = 4

            return ret

        except Exception as e:
            raise Exception("Error running puppet apply: %s" % e)

    def cmd_puppet_apply_file(self, *argv, **kwargs):
        """
        Syntax: puppet.apply_file[recipe_url,envars,facts]
        """
        recipe_url = kwargs.get('recipe_url', None)
        recipe_envars = kwargs.get('envars', None)
        recipe_facts = kwargs.get('facts', None)

        if not recipe_url:
            raise ecm.InvalidParameters(self.cmd_puppet_apply.__doc__)

        recipe_file = None
        recipe_path = None
        module_path = MODULES_PATH
        if ecm.is_windows(): module_path = MODULES_PATH_WINDOWS
        module_path = kwargs.get('module_path', module_path)

        # Set environment variables before execution
        envars = ecm.envars_decode(recipe_envars)
        facts = ecm.envars_decode(recipe_facts)

        # Update envars and facts file
        ecm.write_envars_facts(envars, facts)

        try:
            # Download recipe url
            recipe_path = mkdtemp()
            tmp_file = recipe_path + '/recipe.tar.gz'

            if ecm.download_file(recipe_url, tmp_file):
                if tarfile.is_tarfile(tmp_file):
                    tar = tarfile.open(tmp_file)
                    tar.extractall(path=recipe_path)

                    for file_name in tar.getnames():
                        if file_name.endswith('.catalog.pson'):
                            recipe_file = file_name
                    tar.close()

                    # Apply puppet catalog
                    return self._run_catalog(recipe_file, recipe_path, module_path=module_path, envars=envars)
                else:
                    raise Exception("Invalid recipe tgz file")
            else:
                raise Exception("Unable to download file")

        except:
            raise Exception("Unable to get recipe")

        finally:
            rmtree(recipe_path, ignore_errors=True)

    def _is_available(self):
        """ which puppet
        """
        if ecm.is_windows():
            return ecm.which('puppet.exe')

        return ecm.which('puppet')

    def _run_catalog(self, recipe_file, recipe_path, module_path, envars=None):
        """ Execute catalog file
        """
        retval = self._run_puppet(recipe_file, recipe_path, module_path, 'catalog', envars)

        # Try old way
        if 'invalid option' in retval.get('stdout', ''):
            retval = self._run_puppet(recipe_file, recipe_path, module_path, 'apply', envars)

        return retval

    def _run_puppet(self, recipe_file, recipe_path, module_path, catalog_cmd='catalog', envars=None):
        """ Real puppet execution
        """
        puppet_cmd = self._is_available()
        if not puppet_cmd:
            raise Exception("Puppet is not available")

        command = [puppet_cmd, 'apply', '--detailed-exitcodes', '--modulepath', module_path, '--debug',
                   '--' + catalog_cmd, recipe_file]

        out, stdout, stderr = ecm.run_command(command, workdir=recipe_path, envars=envars)
        ret = ecm.format_output(out, stdout, stderr)

        # --detailed-exitcodes
        # Provide transaction information via exit codes. If this is enabled,
        # an exit code of '2' means there were changes,
        # an exit code of '4' means there were failures during the transaction,
        # and an exit code of '6' means there were both changes and failures.

        # bug in exitcodes in some version even with errors return 0
        # http://projects.puppetlabs.com/issues/6322

        if ret['out'] == 2: ret['out'] = 0
        if "\nError: " in ret['stderr']: ret['out'] = 4

        return ret

    def _install(self, bootstrap_url, bootstrap_file = 'bootstrap.sh'):
        """ Installs puppet using bootstrap url
        """
        tmp_dir = mkdtemp()
        bootstrap_file = tmp_dir + '/' + bootstrap_file
        ecm.download_file(bootstrap_url, bootstrap_file)

        # wget -O - http://bootstrap.ecmanaged.com/puppet/linux/ | sudo sh

        if ecm.file_read(bootstrap_file):
            envars = {'DEBIAN_FRONTEND': 'noninteractive'}
            ecm.run_file(bootstrap_file, envars=envars)

        rmtree(tmp_dir)
        return bool(self._is_available())


ECMPuppet().run()
