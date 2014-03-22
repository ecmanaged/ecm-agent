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

import os

# Local
from __plugin import ECMPlugin, PROTECTED_FILES
import __helper as ecm

class ECMFile(ECMPlugin):
    def cmd_file_exist(self, *argv, **kwargs):
        """Syntax: file.exist[file]"""

        filename = kwargs.get('file', None)

        if not filename:
            raise ecm.InvalidParameters(self.cmd_file_exist.__doc__)

        if os.path.exists(filename):
            return True

        return False

    def cmd_file_time(self, *argv, **kwargs):
        """Syntax: file.time[file,type=(modify|create|access)]"""

        filename = kwargs.get('file', None)
        time_type = kwargs.get('time', None)
        retval = None

        if not filename or not time_type:
            raise ecm.InvalidParameters(self.cmd_file_time.__doc__)

        if not time_type in ['modify', 'create', 'access']:
            raise ecm.InvalidParameters(self.cmd_file_regexp.__doc__)

        if not os.path.exists(filename):
            raise ecm.InvalidParameters("%s doesn't exists" % filename)

        if time_type == 'modify':
            retval = os.path.getmtime(filename)

        elif time_type == 'create':
            retval = os.path.getctime(filename)

        elif time_type == 'access':
            retval = os.path.getatime(filename)

        return retval

    def cmd_file_size(self, *argv, **kwargs):
        """Syntax: file.size[file]"""

        filename = kwargs.get('file', None)

        if not filename:
            raise ecm.InvalidParameters(self.cmd_file_size.__doc__)

        if not os.path.exists(filename):
            raise ecm.InvalidParameters("%s doesn't exists" % filename)

        return str(os.path.getsize(filename))

    def cmd_file_regexp(self, *argv, **kwargs):
        """Syntax: file.regexp[file,regex]"""
        import re

        filename = kwargs.get('file', None)
        regex = kwargs.get('regex', None)

        if not filename or not regex:
            raise ecm.InvalidParameters(self.cmd_file_regexp.__doc__)

        if not os.path.exists(filename):
            raise ecm.InvalidParameters("%s doesn't exists" % filename)

        # don't cat protected files
        if filename in PROTECTED_FILES:
            raise ecm.NotAllowed('File is protected')

        _regex = re.compile(regex)

        retval = ''
        for line in open(filename):
            if _regex.match(line):
                retval += line

        return retval

    def cmd_file_cat(self, *argv, **kwargs):
        """Syntax: file.cat[file]"""

        filename = kwargs.get('file', None)
        if not filename:
            raise Exception(self.cmd_file_cat.__doc__)

        filename = os.path.abspath(filename)

        if not os.path.exists(filename):
            raise ecm.InvalidParameters("%s doesn't exists" % filename)

        # don't cat protected files
        if filename in PROTECTED_FILES:
            raise ecm.NotAllowed('File is protected')

        try:
            _file = open(filename, "r")
            retval = _file.read()
            _file.close()

            return retval

        except:
            raise Exception('Unable to read file')


ECMFile().run()
