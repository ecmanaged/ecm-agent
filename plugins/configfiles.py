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
        configfile_base64       = kwargs.get('configfile',None)
        configfile_path         = kwargs.get('path',None)

        configfile_chown_user   = kwargs.get('chown_user',None)
        configfile_chown_group  = kwargs.get('chown_group',None)

        configfile_command      = kwargs.get('command',None)
        configfile_runas        = kwargs.get('command_runas',None)

        if (not configfile_base64 or not configfile_path):
            raise Exception("Invalid parameters")

        ret = {}
        ret['out'] = 0
        ret['stdout'] = ''
        ret['stderr'] = ''

        try:
            if os.path.isfile(configfile_path):
                new_file = configfile_path + '_rotated_' + self._utime()
                move(configfile_path,new_file)
                ret['stdout'] = self._log_add(ret['stdout'],"Old configfile moved to '%s'\n" % new_file)

            # create working dir if not exists
            working_dir = os.path.abspath(os.path.join(configfile_path, os.pardir))
            self._mkdir_p(working_dir)

            # Write down
            fh = open(configfile_path, "wb")
            fh.write(b64decode(configfile_base64))
            fh.close()
            ret['stdout'] = self._log_add(ret['stdout'],"Configfile created successfully at '%s'\n" %configfile_path)

        except Exception as e:
            raise Exception("Unable to write configfile: %s" %e)

        try:
            # Chown to specified user/group
            if configfile_chown_user and configfile_chown_group and os.path.isfile(configfile_path):
                self._chown(configfile_path,configfile_chown_user,configfile_chown_group)
                ret['stdout'] = self._log_add(ret['stdout'],"Configfile owner changed to '%s':'%s'\n" %(configfile_chown_user,configfile_chown_group))

        except Exception as e:
            raise Exception("Unable to change owner for configfile: %s" %e)

        # exec command
        cmd = []
        if configfile_command:
            cmd = split(configfile_command)

        if cmd:
            # Execute but don't try/catch to get real error
            ret['stdout'] = self._log_add(ret['stdout'],"Executing command: %s\n\n" %(configfile_command))
            if(configfile_runas):
                p = Popen(['su', configfile_runas],
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
