# -*- coding:utf-8 -*-

from ecplugin import ECPlugin

from base64 import b64decode
from shutil import move

import os

class ECMConfigfile(ECPlugin):
    def cmd_configfile_run(self, *argv, **kwargs):
        code_base64  = kwargs.get('configfile',None)
        path         = kwargs.get('path',None)
        chown_user   = kwargs.get('chown_user',None)
        chown_group  = kwargs.get('chown_group',None)
        command      = kwargs.get('command',None)
        runas        = kwargs.get('command_runas',None)
        rotate	     = kwargs.get('rotate',False)

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

        if command:
            out,stdout,stderr = self._execute_command(command,runas=runas,workdir=working_dir)
            ret = self._format_output(out,stdout,stderr)

        return ret

ECMConfigfile().run()
