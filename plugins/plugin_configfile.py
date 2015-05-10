# -*- coding:utf-8 -*-

import os

from base64 import b64decode
from shutil import move

# Local
from __plugin import ECMPlugin
import __helper as ecm


class ECMConfigfile(ECMPlugin):
    def cmd_configfile_run(self, *argv, **kwargs):
        """
        Deploy a file
        Syntax: configfile.run[configfile,file,chown_user,chown_group,chmod,rotate,command,runas]
        """
        code_base64 = kwargs.get('configfile', None)
        filename = kwargs.get('path', None)
        chown_user = kwargs.get('chown_user', None)
        chown_group = kwargs.get('chown_group', None)
        chmod = kwargs.get('chmod', None)
        rotate = kwargs.get('rotate', False)

        command = kwargs.get('command', None)
        runas = kwargs.get('command_runas', None)

        if not code_base64 or not filename:
            raise ecm.InvalidParameters(self.cmd_configfile_run.__doc__)

        ret = {'out': 0, 'stdout': '', 'stderr': ''}
        try:
            if rotate and os.path.isfile(filename):
                new_file = filename + '_rotated_' + ecm.utime()
                move(filename, new_file)
                ret['stdout'] = ecm.output("Old configfile moved to '%s'" % new_file)

            # Write down file
            ecm.file_write(filename, b64decode(code_base64))
            ret['stdout'] += ecm.output("Configfile created successfully at '%s'" % filename)

        except Exception as e:
            raise Exception("Unable to write configfile: %s" % e)

        try:
            # Chown to specified user/group
            if chown_user and chown_group and os.path.isfile(filename):
                ecm.chown(filename, chown_user, chown_group)
                ret['stdout'] += ecm.output("Owner changed to '%s':'%s'" % (chown_user, chown_group))

            # Chown to specified user/group
            if chmod and os.path.isfile(filename):
                ecm.chmod(filename, chmod)
                ret['stdout'] += ecm.output("Owner changed to '%s':'%s'" % (chown_user, chown_group))

        except Exception as e:
            raise Exception("Unable to change permissions for configfile: %s" % e)

        if command:
            working_dir = os.path.dirname(filename)
            out, stdout, stderr = ecm.run_command(command, runas=runas, workdir=working_dir)
            ret = ecm.format_output(out, stdout, stderr)

        return ret


ECMConfigfile().run()
