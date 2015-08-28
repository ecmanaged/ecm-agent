# -*- coding:utf-8 -*-

# Copyright (C) 2012 Juan Carlos Moreno <juancarlos.moreno at ecmanaged.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempfile import mkdtemp
from base64 import b64decode
from shutil import rmtree

# Local
from __plugin import ECMPlugin
import __helper as ecm


class ECMScript(ECMPlugin):
    def cmd_script_run(self, *argv, **kwargs):
        """
        run script(b64) extension envars runas executable
        Syntax: script.run[script,extenion,envars,facts,runas,executable]
        """
        script_b64 = kwargs.get('script', None)
        script_extension = kwargs.get('extension', None)
        script_runas = kwargs.get('runas', None)
        script_executable = kwargs.get('executable', None)
        metadata = kwargs.get('metadata', None)

        if not script_extension:
            script_extension = '.cmd'

        if not script_b64:
            raise ecm.InvalidParameters(self.cmd_script_run.__doc__)

        try:
            # Write down
            tmp_dir = mkdtemp()
            tmp_file = tmp_dir + '/script' + script_extension
            ecm.file_write(tmp_file, b64decode(script_b64))
        except:
            raise ecm.InvalidParameters("Unable to decode b64")

        # Set environment variables before execution
        envars = ecm.metadata_to_env(metadata_b64=metadata)

        # Update metadata
        ecm.write_metadata(metadata_b64=metadata)

        # Chown
        if script_runas:
            ecm.chown(tmp_dir,script_runas,recursive=True)

        if script_executable:
            cmd = script_executable + ' ' + tmp_file
            out, stdout, stderr = ecm.run_command(cmd, runas=script_runas, workdir=tmp_dir, envars=envars)
        else:
            out, stdout, stderr = ecm.run_file(tmp_file, runas=script_runas, workdir=tmp_dir, envars=envars)

        rmtree(tmp_dir, ignore_errors=True)
        return ecm.format_output(out, stdout, stderr)

    def cmd_code_run(self, *argv, **kwargs):
        """
        run code(b64) in path
        Syntax: code.run[code,path,runas]
        """
        code_b64 = kwargs.get('code', None)
        code_path = kwargs.get('path', None)
        code_runas = kwargs.get('runas', None)

        if not code_b64:
            raise ecm.InvalidParameters(self.cmd_code_run.__doc__)

        try:
            code = b64decode(code_b64)
        except:
            raise ecm.InvalidParameters("Unable to decode b64")

        out, stdout, stderr = ecm.run_command(code, runas=code_runas, workdir=code_path, only_stdout=True)
        return ecm.format_output(out, stdout, stderr)


ECMScript().run()
