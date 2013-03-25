# -*- coding:utf-8 -*-

from ecmplugin import ECMPlugin

from subprocess import Popen, PIPE
from shlex import split
from tempfile import mkdtemp

from base64 import b64decode
from shutil import rmtree
from os import chmod, environ

import simplejson as json

class ECMScript(ECMPlugin):
    def cmd_script_run(self, *argv, **kwargs):
        """script.run script(b64) extension envars runas executable"""

        script_base64       = kwargs.get('script',None)
        script_extension    = kwargs.get('extension',None)
        script_envars       = kwargs.get('envars',None)
        script_runas        = kwargs.get('runas',None)
        script_executable   = kwargs.get('executable',None)

        if not script_extension:
            script_extension = '.cmd'

        if not script_base64:
            raise Exception('Invalid argument')

        try:
            # Write down
            tmp_dir = mkdtemp()
            tmp_file = tmp_dir + '/script' + script_extension
            fh = open(tmp_file, "wb")
            fh.write(b64decode(script_base64))
            fh.close()

        except:
            raise Exception("Unable to decode script")

        # Set environment variables before execution
        try:
            if script_envars:
                script_envars = b64decode(script_envars)
                script_envars = json.loads(script_envars)
                for envar in script_envars:
                    if not script_envars[envar]: script_envars[envar] = ''
                    environ[envar] = str(script_envars[envar])

        except: pass

        if script_executable:
            cmd = script_executable + ' ' + tmp_file
            out, stdout, stderr = self._execute_command(cmd, runas=script_runas, workdir=tmp_dir)
        else:
            out, stdout, stderr = self._execute_file(tmp_file, runas=script_runas, workdir = tmp_dir)

        ret = {}
        ret['out'] = out
        ret['stdout'] = str(stdout)
        ret['stderr']  = str(stderr)

        # Clean
        rmtree(tmp_dir, ignore_errors = True)
        return ret


ECMScript().run()