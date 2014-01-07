# -*- coding:utf-8 -*-

from ecplugin import ecplugin

from base64 import b64decode
from tempfile import mkdtemp
from shutil import rmtree

import tarfile

MODULES_PATH = '/etc/puppet/modules'
MODULES_PATH_WINDOWS = 'c:\ECM\puppet\modules'


class ECMPuppet(ecplugin):
    def cmd_puppet_available(self, *argv, **kwargs):
        """ Checks if puppet commands are available
         """
        return bool(self._is_available())

    def cmd_puppet_install(self, *argv, **kwargs):
        """ Installs puppet from packages
        """
        if self._is_available():
            return True

        package = kwargs.get('package', 'puppet')
        self._install_package(package)

        if not self._is_available():
            raise Exception("Unable to install puppet")

        return True

    def cmd_puppet_apply(self, *argv, **kwargs):

        recipe_base64 = kwargs.get('recipe_code', None)
        recipe_envars = kwargs.get('envars', None)
        recipe_facts = kwargs.get('facts', None)

        if not recipe_base64:
            raise Exception("Invalid argument")

        module_path = MODULES_PATH
        if self._is_windows: module_path = MODULES_PATH_WINDOWS
        module_path = kwargs.get('module_path', module_path)

        # Set environment variables before execution
        envars = self._envars_decode(recipe_envars)
        facts = self._envars_decode(recipe_facts)

        # Update envars and facts file
        self._write_envars_facts(envars, facts)

        try:
            # Create temp file
            catalog = b64decode(recipe_base64)
        except:
            raise Exception("Unable to decode recipe")

        try:
            command = ['puppet', 'apply', '--modulepath', module_path,
                       '--detailed-exitcodes', '--debug']

            out, stdout, stderr = self._execute_command(command, stdin=catalog, envars=envars)
            ret = self._format_output(out, stdout, stderr)

            # exit code of '2' means there were changes
            if ret['out'] == 2: ret['out'] = 0
            if "\nError: " in ret['stderr']: ret['out'] = 4

            return ret

        except Exception as e:
            raise Exception("Error running puppet apply: %s" % e)

    def cmd_puppet_apply_file(self, *argv, **kwargs):

        recipe_url = kwargs.get('recipe_url', None)
        recipe_envars = kwargs.get('envars', None)
        recipe_facts = kwargs.get('facts', None)

        if not recipe_url:
            raise Exception("Invalid argument")

        recipe_file = None
        recipe_path = None
        module_path = MODULES_PATH
        if self._is_windows: module_path = MODULES_PATH_WINDOWS
        module_path = kwargs.get('module_path', module_path)

        # Set environment variables before execution
        envars = self._envars_decode(recipe_envars)
        facts = self._envars_decode(recipe_facts)

        # Update envars and facts file
        self._write_envars_facts(envars, facts)

        try:
            # Download recipe url
            recipe_path = mkdtemp()
            tmp_file = recipe_path + '/recipe.tar.gz'

            if self._download_file(url=recipe_url, file=tmp_file):
                if tarfile.is_tarfile(tmp_file):
                    tar = tarfile.open(tmp_file)
                    tar.extractall(path=recipe_path)

                    for file_name in tar.getnames():
                        if file_name.endswith('.catalog.pson'):
                            recipe_file = file_name
                    tar.close()

                    # Apply puppet
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

        if self._is_windows: return self._which('puppet.exe')
        return self._which('puppet')

    def _run_catalog(self, recipe_file, recipe_path, module_path, envars=None):

        retval = self._run_puppet(recipe_file, recipe_path, module_path, 'catalog', envars)

        # Try old way
        if 'invalid option' in retval.get('stdout', ''):
            retval = self._run_puppet(recipe_file, recipe_path, module_path, 'apply', envars)

        return retval

    def _run_puppet(self, recipe_file, recipe_path, module_path, catalog_cmd='catalog', envars=None):

        puppet_cmd = self._is_available()
        if not puppet_cmd:
            raise Exception("Puppet is not available")

        command = [puppet_cmd, 'apply', '--detailed-exitcodes', '--modulepath', module_path, '--debug',
                   '--' + catalog_cmd, recipe_file]

        out, stdout, stderr = self._execute_command(command, workdir=recipe_path, envars=envars)
        ret = self._format_output(out, stdout, stderr)

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


ECMPuppet().run()
