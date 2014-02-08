# -*- coding:utf-8 -*-

import os

from tempfile import mkdtemp, NamedTemporaryFile
from urlparse import urlparse
from shutil import move, rmtree
from base64 import b64decode

try:
    import tarfile
    import zipfile

except ImportError:
    pass

from plugin import ECMPlugin
from __plugin_common import ECMCommon

class ECMSource(ECMPlugin):
    def cmd_source_run(self, *argv, **kwargs):
        path            = kwargs.get('path', None)
        url             = kwargs.get('source', None)
        branch          = kwargs.get('branch', None)
        source_envars   = kwargs.get('envars', None)
        source_facts    = kwargs.get('facts', None)
        user            = kwargs.get('username', None)
        passwd          = kwargs.get('password', None)
        private_key     = kwargs.get('private_key', None)
        chown_user      = kwargs.get('chown_user', None)
        chown_group     = kwargs.get('chown_group', None)
        rotate          = kwargs.get('rotate', True)
        type            = kwargs.get('type', None)

        if not path or not url or not type:
            raise Exception("Invalid parameters")
            
        if private_key:
            try:
                private_key = b64decode(private_key)
            except:
                raise Exception("Invalid private key format")

        if type.upper() in ('URI', 'FILE'):
            source = FILE(path, rotate)

        elif type.upper() == 'GIT':
            source = GIT(path, rotate)

        elif type.upper() == 'SVN':
            source = SVN(path, rotate)

        else:
            raise Exception("Unknown source")

        # Set environment variables before execution
        envars = self._envars_decode(source_envars)
        facts = self._envars_decode(source_facts)

        # Update envars and facts file
        self._write_envars_facts(envars, facts)

        retval = source.clone(url=url, branch=branch, envars=envars, username=user, password=passwd,
                              private_key=private_key)

        # Chown to specified user/group
        if chown_user and chown_group and os.path.isdir(path):
            self._chown(path, chown_user, chown_group, recursive=True)
            retval['stdout'] += self._output("Owner changed to '%s':'%s'" % (chown_user, chown_group))

        return self._return(retval)

    def _return(self, ret):
        output = {
            'out': ret.get('out', 1),
            'stderr': ret.get('stderr', ''),
            'stdout': ret.get('stdout', '')
        }
        return output


class GIT(ECMCommon):
    def __init__(self, working_dir, rotate):

        if not working_dir:
            raise Exception("Invalid path")

        self.working_dir = working_dir
        self.rotate = rotate

        # Create or rename working_dir
        deploy = Deploy(self.working_dir, rotate)
        self.old_dir = deploy.prepare()

        # Get git path
        self.git_cmd = self._is_available()
        
        if not self.git_cmd:
            if not self._install():
                raise Exception('Unable to find or install git')
            self.git_cmd = self._is_available()

    def clone(self, url, branch, envars, username, password, private_key):
        """ runs git clone URL
        """
            
        command = self._get_command(url,branch)

        # Create git command with user and password
        if username and password:
            parsed = urlparse(url)
            if parsed.scheme in ('http', 'https'):
                command = command.replace('://', '://' + username + ':' + password + '@')

            elif parsed.scheme == 'ssh':
                command = command.replace('://', '://' + username + '@')

        elif private_key:
            helper, indetity = self._certificate_helper(private_key)
            envars['GIT_SSH'] = helper

        out, stdout, stderr = self._execute_command(command=command, workdir=self.working_dir, envars=envars)
        result_exec = self._format_output(out, stdout, stderr)

        if not result_exec['out']:
            extra_msg = self._output("Source deployed successfully to '%s'" % self.working_dir)
            if self.old_dir:
                extra_msg += self._output("Old source files moved to '%s'" % self.old_dir)
            result_exec['stdout'] += extra_msg

        if private_key:
            try:
                os.unlink(helper)
                os.unlink(indetity)
            except:
                pass

        return result_exec
        
    def _get_command(self,url,branch):
        param = ''
        if branch and branch != 'master':
            param = " -b " + str(branch)
        
        command = self.git_cmd + " clone" + param + " --quiet --verbose '" + url + "' ."
        command_pull = self.git_cmd + " pull --quiet --verbose"
        
        if os.path.isdir(self.working_dir + '/.git'):
            # GIT clone on already .git repo, do a pull and hope...
            command = command_pull
                
        return command

    def _certificate_helper(self,private_key=None):
        '''
        Returns the path to a helper script which can be used in the GIT_SSH env
        var to use a custom private key file.
        '''
        opts = {
            'StrictHostKeyChecking': 'no',
            'PasswordAuthentication': 'no',
            'KbdInteractiveAuthentication': 'no',
            'ChallengeResponseAuthentication': 'no',
        }

        # Create identity file
        identity = NamedTemporaryFile(delete=False)
        self._chmod(identity.name, 0600)
        identity.writelines([private_key])
        identity.close()

        # Create helper script
        helper = NamedTemporaryFile(delete=False)
        helper.writelines([
            '#!/bin/sh\n',
            'exec ssh ' + 
            ' '.join('-o%s=%s' % (key, value) for key, value in opts.items()) + 
            ' -i ' + identity.name + 
            ' $*\n'
        ])

        helper.close()
        self._chmod(helper.name, 0750)

        return helper.name, identity.name

    def _is_available(self):
        """ checks if git is on path
        """
        if self._is_windows(): return self._which('git.exe')
        return self._which('git')

    def _install(self):
        """ Try to install git
        """
        self._install_package('git')
        return bool(self._is_available())


class SVN(ECMCommon):
    def __init__(self, working_dir, rotate):

        if not working_dir:
            raise Exception("Invalid path")

        self.working_dir = working_dir
        self.rotate = rotate

        # Create or rename working_dir
        deploy = Deploy(self.working_dir, rotate)
        self.old_dir = deploy.prepare()

        # Get git path
        self.svn_cmd = self._is_available()

        if not self.svn_cmd:
            if not self._install():
                raise Exception('Unable to find or install subversion')
            self.svn_cmd = self._is_available()

    def clone(self, url, branch, envars, username, password, private_key):
        """ svn co URL
        """

        # Add username and password to url
        if username and password:
            url = url.replace('://', '://' + username + ':' + password + '@')

        command = self.svn_cmd + " co '" + url + "' ."

        out, stdout, stderr = self._execute_command(command=command, workdir=self.working_dir, envars=envars)
        result_exec = self._format_output(out, stdout, stderr)

        if not result_exec['out']:
            extra_msg = self._output("Source deployed successfully to '%s'" % self.working_dir)
            if self.old_dir:
                extra_msg += self._output("Old source files moved to '%s'" % self.old_dir)

            if result_exec['stdout']:
                result_exec['stdout'] = extra_msg + result_exec['stdout']

            else:
                result_exec['stdout'] = extra_msg

        return result_exec

    def _is_available(self):
        """ is svn on path
        """
        if self._is_windows(): return self._which('svn.cmd')
        return self._which('svn')

    def _install(self):
        """ try to install subversion
        """
        self._install_package('subversion')
        return self._is_available()


class FILE(ECMCommon):
    def __init__(self, working_dir, rotate):

        if not working_dir:
            raise Exception("Invalid path")

        self.working_dir = working_dir
        self.rotate = rotate

        # Create or rename working_dir
        deploy = Deploy(self.working_dir, rotate)
        self.old_dir = deploy.prepare()

    def clone(self, branch, envars, url, username, password, private_key):
        """ Downloads a file from a remote url and decompress it
        """

        file_name = 'downloaded.file'
        tmp_dir = mkdtemp()

        file_downloaded = self._download_file(
            url=url,
            file=tmp_dir + '/' + file_name,
            user=username,
            passwd=password
        )

        if file_downloaded:
            extract = self._extract(file_downloaded)
            if extract:
                extract['head'] = ''
                if extract.get('stdout', None):
                    extract['head'] = self._output("Source deployed successfully to '%s'" % self.working_dir)

                if extract.get('stdout', None) and self.old_dir:
                    extract['head'] += self._output("Old source files moved to '%s'" % self.old_dir)

        else:
            rmtree(tmp_dir, ignore_errors=True)
            raise Exception("Unable to download file")

        # Clean and output
        rmtree(tmp_dir, ignore_errors=True)
        ret = {
            'stdout': extract.get('head', '') + extract.get('stdout', ''),
            'stderr': extract.get('stderr', 'Unable to download file'),
            'out': extract.get('out', 1)
        }
        return ret

    def _extract(self, file):
        """ extractor helper
        """

        try:
            file_type = self._get_file_type(file)
            if file_type == 'zip':
                opener, mode = zipfile.ZipFILE, 'r'

            elif file_type == 'gz':
                opener, mode = tarfile.open, 'r:gz'

            elif file_type == 'bz2':
                opener, mode = tarfile.open, 'r:bz2'

            else:
                raise Exception("Unsupported file compression")

            cfile = opener(file, mode)

            # if first member is dir, skip 1st container path
            is_packed = None
            if file_type == 'zip':
                members = cfile.namelist()
            else:
                members = cfile.getmembers()
                if members[0].isdir():
                    is_packed = members[0].name

            stdout = ''
            if is_packed:
                for member in members:
                    member.name = member.name.replace(is_packed, '.')
                    if member.name.endswith('/.'): continue
                    if member.name == './': continue
                    if member.name == '.': continue

                    stdout += "Extracted " + member.name + "\n"
                    cfile.extract(member, self.working_dir)
            else:
                for member in members:
                    if file_type == 'zip':
                        member_name = member
                    else:
                        member_name = member.name

                    stdout += "Extracted " + member_name + "\n"
                cfile.extractall(self.working_dir)
            cfile.close()

        except Exception as e:
            raise Exception("Could not extract file: %s" % e)

        ret = {'out': 0, 'stderr': '', 'stdout': stdout}
        return ret

    def _get_file_type(self, file):
        """ get compressed file type based on marks
        """

        magic_dict = {
            "\x1f\x8b\x08": "gz",
            "\x42\x5a\x68": "bz2",
            "\x50\x4b\x03\x04": "zip"
        }

        max_len = max(len(x) for x in magic_dict)
        with open(file) as f:
            file_start = f.read(max_len)
            for magic, filetype in magic_dict.items():
                if file_start.startswith(magic):
                    return filetype
        return False


class Deploy(ECMCommon):
    def __init__(self, working_dir, rotate):

        self.working_dir = os.path.abspath(working_dir)
        self.rotate = rotate

    def prepare(self):
        """ Common function to create and rotate
        """

        to_dir = None
        if self.rotate and os.path.isdir(self.working_dir):
            drive, path = os.path.splitdrive(self.working_dir)
            split_path = self._split_path(path)

            try:
                a = split_path[1]
            except IndexError:
                # Unsafe rotate
                self.rotate = False

            if self.rotate:
                to_dir = self.working_dir + '_rotated_' + self._utime()
                move(self.working_dir, to_dir)

        # create working dir
        if not os.path.isdir(self.working_dir):
            self._mkdir_p(self.working_dir)

        return to_dir

    def rollback(self, path):

        return


ECMSource().run()
