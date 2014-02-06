# -*- coding:utf-8 -*-

from ecplugin import ecplugin

from tempfile import mkdtemp
from shutil import rmtree
from base64 import b64decode

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

class ECMSaltstack(ecplugin):
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

        if self._is_windows():
            bootstrap = BOOTSTRAP_WINDOWS
            bootstrap_file = 'bootstrap.ps1'

        if not self._install(bootstrap,bootstrap_file):
            # Try alternative bootstrap
            bootstrap = BOOTSTRAP_ALT
            if self._is_windows():
                bootstrap = BOOTSTRAP_WINDOWS_ALT

            if not self._install(bootstrap,bootstrap_file):
                raise Exception("Unable to install saltstack")

        return True

    def cmd_saltstack_apply(self, *argv, **kwargs):
        """ Apply a saltstack manifest
        """
        recipe_base64   = kwargs.get('recipe_code', None)
        pillar_base64   = kwargs.get('pillar_code', None)
        recipe_envars   = kwargs.get('envars', None)
        recipe_facts    = kwargs.get('facts', None)

        if not recipe_base64:
            raise Exception("Invalid arguments")

        saltstack_cmd = self._is_available()
        if not saltstack_cmd:
            raise Exception('Saltstack no available')

        # Get default paths
        default_path = DEFAULT_SALT_PATH
        if self._is_windows(): default_path = DEFAULT_SALT_PATH_WINDOWS
        module_path = kwargs.get('module_path', default_path)

        default_pillar_path = DEFAULT_PILLAR_PATH
        if self._is_windows(): default_pillar_path = DEFAULT_PILLAR_PATH_WINDOWS
        pillar_path = kwargs.get('pillar_path', default_pillar_path)

        # Set environment variables before execution
        envars = self._envars_decode(recipe_envars)
        facts = self._envars_decode(recipe_facts)

        # Update envars and facts file
        self._write_envars_facts(envars, facts)

        try:
            # Create top file
            self._create_top_file(module_path)

            recipe_file = module_path + '/ecmanaged.sls'
            self._file_write(recipe_file, b64decode(recipe_base64))

            if pillar_base64:
                self._create_top_file(pillar_path)
                pillar_file = pillar_path + '/ecmanaged.sls'
                self._file_write(pillar_file, b64decode(pillar_base64))

        except:
            raise Exception("Unable to write recipe")

        try:
            # salt-call state.highstate
            command = [saltstack_cmd, 'state.highstate', '--local', '--no-color', '-l debug']

            out, stdout, stderr = self._execute_command(command, envars=envars, workdir=module_path)
            return self._format_output(out, stdout, stderr)

        except Exception as e:
            raise Exception("Error running saltstack state.highstate: %s" % e)

    def _create_top_file(self, path):
        top_file = path + '/top.sls'
        self._file_write(top_file, TOP_CONTENT)

    def _is_available(self):
        """ it's salt-call on path?
        """
        if self._is_windows():
            return self._which('salt-call.exe')
        return self._which('salt-call')

    def _install(self, bootstrap_url, bootstrap_file = 'bootstrap.sh'):
        """ Installs saltstack using bootstrap url
        """

        tmp_dir = mkdtemp()
        bootstrap_file = tmp_dir + '/' + bootstrap_file
        self._download_file(bootstrap_url, bootstrap_file)

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

        if self._file_read(bootstrap_file):
            envars = {'DEBIAN_FRONTEND': 'noninteractive'}
            self._execute_file(bootstrap_file, args=['-n', '-P', '-X'], envars=envars)

        rmtree(tmp_dir)
        return bool(self._is_available())


ECMSaltstack().run()
