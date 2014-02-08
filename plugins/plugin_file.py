# -*- coding:utf-8 -*-

import os
import re

from plugin import ECMPlugin


# :TODO: Move to config
PROTECTED_FILES = [
    '/etc/shadow',
]

class ECMFile(ECMPlugin):
    def cmd_file_exist(self, *argv, **kwargs):
        """Syntax: file.exist <file>"""

        file = kwargs.get('file', None)

        if not file:
            raise Exception(self.cmd_file_exist.__doc__)

        if os.path.exists(file):
            return True

        return False

    def cmd_file_time(self, *argv, **kwargs):
        """Syntax: file.time <file> <type=(modify|create|access)>"""

        file = kwargs.get('file', None)
        type = kwargs.get('time', None)

        if not (file and type):
            raise Exception(self.cmd_file_time.__doc__)

        if not type in ['modify', 'create', 'access']:
            raise Exception(self.cmd_file_regexp.__doc__)

        if not os.path.exists(file):
            raise Exception("%s doesn't exists" % file)

        if type == 'modify':
            retval = os.path.getmtime(file)

        elif type == 'create':
            retval = os.path.getctime(file)

        elif type == 'access':
            retval = os.path.getatime(file)

        return retval

    def cmd_file_size(self, *argv, **kwargs):
        """Syntax: file.size <file>"""

        file = kwargs.get('file', None)

        if not file:
            raise Exception(self.cmd_file_size.__doc__)

        if not os.path.exists(file):
            raise Exception("%s doesn't exists" % file)

        return str(os.path.getsize(file))

    def cmd_file_regexp(self, *argv, **kwargs):
        """Syntax: file.regexp <file> <regex>"""

        file = kwargs.get('file', None)
        regex = kwargs.get('regex', None)

        if not (file and regex):
            raise Exception(self.cmd_file_regexp.__doc__)

        if not os.path.exists(file):
            raise Exception("%s doesn't exists" % file)

        # don't cat protected files
        if file in PROTECTED_FILES:
            raise Exception('Not allowed')

        _regex = re.compile(regex)

        retval = ''
        for line in open(file):
            if _regex.match(line):
                retval = retval + line

        return retval

    def cmd_file_cat(self, *argv, **kwargs):
        """Syntax: file.cat <file>"""

        file = kwargs.get('file', None)
        if not file:
            raise Exception(self.cmd_file_cat.__doc__)

        file = os.path.abspath(file)

        if not os.path.exists(file):
            raise Exception("%s doesn't exists" % file)

        # don't cat protected files
        if file in PROTECTED_FILES:
            raise Exception('Not allowed')

        try:
            file = open(file, "r")
            retval = file.read()
            file.close()

            return (retval)

        except:
            raise Exception('Unable to read file')


ECMFile().run()
