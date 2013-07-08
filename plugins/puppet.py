# -*- coding:utf-8 -*-

from ecplugin import ECPlugin

from tempfile import mkdtemp
from shutil import rmtree

import twisted.python.procutils as procutils
import tarfile

from base64 import b64decode

class ECMPuppet(ECPlugin):
    def cmd_puppet_available(self, *argv, **kwargs):
        return self._is_available()

    def cmd_puppet_apply(self, *argv, **kwargs):
        recipe_base64 = kwargs.get('recipe_code',None)

        if not recipe_base64:
            raise Exception("Invalid argument")

        self._parse_args(*argv, **kwargs)

        try:
            # Create temp file
            catalog = b64decode(recipe_base64)
        except:
            raise Exception("Unable to decode recipe")

        try:
            command = ['puppet', 'apply', '--modulepath', self.module_path,
                       '--detailed-exitcodes']
            if self.debug: command.append('--debug')

            out,stdout,stderr = self._execute_command(command,stdin = catalog)
            ret = self._format_output(out,stdout,stderr)

            # exit code of '2' means there were changes
            if ret['out'] == 2: ret['out'] = 0
            if "\nError: " in ret['stderr']: ret['out'] = 4

            return ret

        except Exception as e:
            raise Exception("Error running puppet apply: %s" %e)

    def cmd_puppet_apply_file(self, *argv, **kwargs):
        recipe_url  = kwargs.get('recipe_url',None)
        recipe_file = None
        recipe_path = None

        if not recipe_url: raise Exception("Invalid argument")
        self._parse_args(*argv, **kwargs)

        try:
            # Download recipe url
            recipe_path = mkdtemp()
            tmp_file = recipe_path + '/recipe.tar.gz'

            if self._download_file(url=recipe_url,file=tmp_file):
                if tarfile.is_tarfile(tmp_file):
                    tar = tarfile.open(tmp_file)
                    tar.extractall(path=recipe_path)

                    for file_name in tar.getnames():
                        if  file_name.endswith('.catalog.pson'):
                            recipe_file = file_name
                    tar.close()

                    # Apply puppet
                    return self._run_catalog(recipe_file,recipe_path)
                else:
                    raise Exception("Invalid recipe tgz file")
            else:
                raise Exception("Unable to download file")

        except:
            raise Exception("Unable to get recipe")

        finally:
            rmtree(recipe_path, ignore_errors = True)

    def cmd_puppet_install(self, *argv, **kwargs):
        try:
            # raises if not found
            if self.cmd_puppet_available(*argv, **kwargs):
                return False
        except:
            pass

        out,stdout,stderr = self._install_package('puppet')
        return out
        
    def _is_available(self):
        which_posix = procutils.which('puppet')
        which_win   = procutils.which('puppet.exe')

        try: puppet_cmd = which_posix[0]
        except IndexError:
            try: puppet_cmd = which_win[0]
            except IndexError:
                raise Exception("Not found")

        return puppet_cmd

    def _run_catalog(self,recipe_file,recipe_path):
        retval = self._run_puppet(recipe_file,recipe_path,'catalog')

        # Try old way
        if 'invalid option' in retval.get('stdout',''):
            retval = self._run_puppet(recipe_file,recipe_path,'apply')

        return retval

    def _run_puppet(self,recipe_file,recipe_path,catalog_cmd = 'catalog'):
        command = ['puppet', 'apply', '--detailed-exitcodes',
                   '--modulepath', self.module_path]

        if self.debug: command.append('--debug')
        command.append('--' + catalog_cmd)
        command.append(recipe_file)

        out,stdout,stderr = self._execute_command(command,workdir=recipe_path)
        ret = self._format_output(out,stdout,stderr)

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

    def _parse_args(self, *argv, **kwargs):
        self.debug = kwargs.get('debug',False)
        if self.debug == '0': self.debug = False
        self.module_path = kwargs.get('module_path','/etc/puppet/modules')

ECMPuppet().run()
