# -*- coding:utf-8 -*-

from ecplugin import ecplugin

from base64 import b64decode
from shutil import move

import os


class ECMConfigfile(ecplugin):
    def cmd_configfile_run(self, *argv, **kwargs):
        code_base64     = kwargs.get('configfile', None)
        file            = kwargs.get('path', None)
        chown_user      = kwargs.get('chown_user', None)
        chown_group     = kwargs.get('chown_group', None)
        chmod           = kwargs.get('chmod', None)
        rotate          = kwargs.get('rotate', False)

        command         = kwargs.get('command', None)
        runas           = kwargs.get('command_runas', None)

        if not code_base64 or not file:
            raise Exception("Invalid parameters")

        ret = {}
        ret['out'] = 0
        ret['stdout'] = ''
        ret['stderr'] = ''

        try:
            if rotate and os.path.isfile(file):
                new_file = file + '_rotated_' + self._utime()
                move(file, new_file)
                ret['stdout'] = self._output("Old configfile moved to '%s'" % new_file)

            # Write down file
            self._file_write(file, b64decode(code_base64))
            ret['stdout'] += self._output("Configfile created successfully at '%s'" % file)

        except Exception as e:
            raise Exception("Unable to write configfile: %s" % e)

        try:
            # Chown to specified user/group
            if chown_user and chown_group and os.path.isfile(file):
                self._chown(file, chown_user, chown_group)
                ret['stdout'] += self._output("Owner changed to '%s':'%s'" % (chown_user, chown_group))

            # Chown to specified user/group
            if chmod and os.path.isfile(file):
                self._chmod(file, chmod)
                ret['stdout'] += self._output("Owner changed to '%s':'%s'" % (chown_user, chown_group))

        except Exception as e:
            raise Exception("Unable to change permissions for configfile: %s" % e)

        if command:
            workdir = os.path.dirname(file)
            out, stdout, stderr = self._execute_command(command, runas=runas, workdir=workdir)
            ret = self._format_output(out, stdout, stderr)

        return ret


ECMConfigfile().run()
