# -*- coding:utf-8 -*-

import os

from base64 import b64decode
from shutil import move

from __ecm_plugin import ECMPlugin
import __ecm_helper as ecm

class ECMConfigfile(ECMPlugin):
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
                new_file = file + '_rotated_' + ecm.utime()
                move(file, new_file)
                ret['stdout'] = ecm.output("Old configfile moved to '%s'" % new_file)

            # Write down file
            ecm.file_write(file, b64decode(code_base64))
            ret['stdout'] += ecm.output("Configfile created successfully at '%s'" % file)

        except Exception as e:
            raise Exception("Unable to write configfile: %s" % e)

        try:
            # Chown to specified user/group
            if chown_user and chown_group and os.path.isfile(file):
                ecm.chown(file, chown_user, chown_group)
                ret['stdout'] += ecm.output("Owner changed to '%s':'%s'" % (chown_user, chown_group))

            # Chown to specified user/group
            if chmod and os.path.isfile(file):
                ecm.chmod(file, chmod)
                ret['stdout'] += ecm.output("Owner changed to '%s':'%s'" % (chown_user, chown_group))

        except Exception as e:
            raise Exception("Unable to change permissions for configfile: %s" % e)

        if command:
            workdir = os.path.dirname(file)
            out, stdout, stderr = ecm.execute_command(command, runas=runas, workdir=workdir)
            ret = ecm.format_output(out, stdout, stderr)

        return ret


ECMConfigfile().run()
