# -*- coding:utf-8 -*-

from ecmplugin import ECMPlugin

from subprocess import Popen, PIPE
from shlex import split
from tempfile import mkdtemp

from base64 import b64decode
from shutil import rmtree
from os import chmod, environ

import simplejson as json
import stat

class ECMScript(ECMPlugin):
    def cmd_script_run(self, *argv, **kwargs):
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

        cmd = []
        if script_executable:
        # Add executable to command
            cmd = split(script_executable)
        else:
            # Set as executable by owner if not explicit executable
            chmod(tmp_file,0700)

        # Add temp file as last argument (or first if not executable)
        cmd.append(tmp_file)

        # Set environment variables before execution
        try:
            if script_envars:
                script_envars = b64decode(script_envars)
                script_envars = json.loads(script_envars)
                for envar in script_envars:
                    if not script_envars[envar]: script_envars[envar] = ''
                    environ[envar] = str(script_envars[envar])

        except: pass

        # Execute but don't try/catch to get real error
        if(script_runas):
            # Change owner and execute
            self._chown(path=tmp_dir,user=script_runas,group='root',recursive=True)
            p = Popen(['su', script_runas],
                      stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=tmp_dir)
            stdout, stderr = p.communicate(' '.join(cmd))

        else:
            p = Popen(cmd,
                      stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=tmp_dir)
            stdout, stderr = p.communicate()

        ret = {}
        ret['out'] = p.wait()
        ret['stdout'] = str(stdout)
        ret['stderr']  = str(stderr)

        # Clean
        rmtree(tmp_dir, ignore_errors = True)
        return ret


ECMScript().run()