# -*- coding:utf-8 -*-

from ecmplugin import ECMPlugin

from subprocess import Popen, PIPE
from shlex import split

from base64 import b64decode
from time import time
from shutil import move

import os

class ECMConfigfile(ECMPlugin):
    def cmd_configfile_run(self, *argv, **kwargs):
        code_base64  = kwargs.get('configfile',None)
        path         = kwargs.get('path',None)
        chown_user   = kwargs.get('chown_user',None)
        chown_group  = kwargs.get('chown_group',None)
        command      = kwargs.get('command',None)
        runas        = kwargs.get('command_runas',None)
        rotate	     = kwargs.get('rotate',True)

        if (not code_base64 or not path):
            raise Exception("Invalid parameters")

        ret = {}
        ret['out'] = 0
        ret['stdout'] = ''
        ret['stderr'] = ''

        try:
            if rotate and os.path.isfile(path):
                new_file = path + '_rotated_' + self._utime()
                move(path,new_file)
                ret['stdout'] = self._output("Old configfile moved to '%s'" % new_file)

            # create working dir if not exists
            working_dir = os.path.abspath(os.path.join(path, os.pardir))
            self._mkdir_p(working_dir)

            # Write down
            fh = open(path, "wb")
            fh.write(b64decode(code_base64))
            fh.close()
            ret['stdout'] += self._output("Configfile created successfully at '%s'" %path)

        except Exception as e:
            raise Exception("Unable to write configfile: %s" %e)

        try:
            # Chown to specified user/group
            if chown_user and chown_group and os.path.isfile(path):
                self._chown(path,chown_user,chown_group)
                ret['stdout'] += self._output("Configfile owner changed to '%s':'%s'" %(chown_user,chown_group))

        except Exception as e:
            raise Exception("Unable to change owner for configfile: %s" %e)

        # exec command
        cmd = []
        if command:
            cmd = split(command)

        if cmd:
            # Execute but don't try/catch to get real error
            ret['stdout'] += self._output("Executing command: %s" %(command))
            if(runas):
                p = Popen(['su', runas],
                          stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=working_dir)
                stdout, stderr = p.communicate(' '.join(cmd))

            else:
                p = Popen(cmd,
                          stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=working_dir)
                stdout, stderr = p.communicate()

            ret['out'] = p.wait()
            ret['stdout'] += "\n" + str(stdout)
            ret['stderr'] = str(stderr)

        return ret

    def _mkdir_p(self,path):
        try:
            os.makedirs(path)
        except OSError as e:
            pass

    def _utime(self):
        str_time = str(time()).replace('.','_')
        return str_time

ECMConfigfile().run()
