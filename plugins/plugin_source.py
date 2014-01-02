# -*- coding:utf-8 -*-

from ecplugin import ecplugin
from ectools import ectools

from tempfile import mkdtemp
from base64 import b64decode
from urlparse import urlparse
import urllib2

import os
import twisted.python.procutils as procutils

import simplejson as json
from shutil import move, rmtree

try:
    import tarfile
    import zipfile

except:
    pass

class ECMSource(ecplugin):
    def cmd_source_run(self, *argv, **kwargs):
        path            = kwargs.get('path',None)
        url             = kwargs.get('source',None)
        source_envars   = kwargs.get('envars',None)
        source_facts    = kwargs.get('facts',None)
        user            = kwargs.get('username',None)
        passwd          = kwargs.get('password',None)
        private_key     = kwargs.get('private_key',None)
        chown_user      = kwargs.get('chown_user',None)
        chown_group     = kwargs.get('chown_group',None)
        rotate          = kwargs.get('rotate',False)

        if (not path or not url):
            raise Exception("Invalid parameters")

        type = kwargs.get('type',None)

        if type and type.upper() in ('URI','FILE'):
            source = File(path,rotate)

        elif type and type.upper() == 'GIT':
            source = Git(path,rotate)

        elif type and type.upper() == 'SVN':
            source = Svn(path,rotate)

        else: raise Exception("Unknown source")

        # Set environment variables before execution
        envars = self._envars_decode(source_envars)
        facts  = self._envars_decode(source_facts)

        # Update envars and facts file
        self._write_envars_facts(envars,facts)

        retval = source.clone(url=url, envars=envars,\
                              username=user, password=passwd, private_key=private_key)

        # Chown to specified user/group
        if chown_user and chown_group and os.path.isdir(path):
            self._chown(path,chown_user,chown_group,recursive=True)
            retval['stdout'] += self._output("Owner changed to '%s':'%s'" %(chown_user,chown_group))

        return self._return(retval)

    def _return(self,ret):
        output = {
            'out': ret.get('out',1),
            'stderr': ret.get('stderr',''),
            'stdout': ret.get('stdout','')
        }
        return output

class Git(ectools):
    def __init__(self,working_dir,rotate):
        if not working_dir:
            raise Exception("Invalid path")

        self.working_dir = working_dir
        self.rotate = rotate

        # Create or rename working_dir
        deploy = Deploy(self.working_dir,rotate)
        self.old_dir = deploy.prepare()

        if not self._is_available():
            if not self._install():
                raise Exception('Unable to find or install git')

    def clone(self, url, envars, username, password, private_key):
        command_clone = self.git_cmd + " clone --quiet --verbose '" + url + "' ."
        command_pull  = self.git_cmd + " pull --quiet --verbose"

        command = command_clone
        if os.path.isdir(self.working_dir + '/.git'):
            if not self.rotate:
                # Git clone will fail: no empty dir (so make a pull and hope...)
                command = command_pull

        else:
            # Rotate this dir or will fail
            deploy = Deploy(self.working_dir,True)
            self.old_dir = deploy.prepare()

        # Create git command with user and password
        if username and password:
            parsed = urlparse(url)
            if parsed.scheme in ('http','https'):
                command = command.replace('://','://' + username + ':' + password + '@')

            elif parsed.scheme == 'ssh':
                command = command.replace('://','://' + username + '@')

        out,stdout,stderr = self._execute_command(command = command, workdir = self.working_dir, envars = envars)
        result_exec = self._format_output(out,stdout,stderr)

        if not result_exec['out']:
            extra_msg = self._output("Source deployed successfully to '%s'" % self.working_dir)
            if self.old_dir:
                extra_msg += self._output("Old source files moved to '%s'" % self.old_dir)
            result_exec['stdout'] = extra_msg

        return result_exec

    def _is_available(self):
        which_posix  = procutils.which('git')
        which_win    = procutils.which('git.exe')

        try: self.git_cmd = which_posix[0]
        except IndexError:
            try: self.git_cmd = which_win[0]
            except IndexError:
                return False

        return True

    def _install(self):
        self._install_package('git')
        return self._is_available()

class Svn(ectools):
    def __init__(self,working_dir,rotate):
        if not working_dir:
            raise Exception("Invalid path")

        self.working_dir = working_dir
        self.rotate = rotate

        # Create or rename working_dir
        deploy = Deploy(self.working_dir,rotate)
        self.old_dir = deploy.prepare()

        if not self._is_available():
            if not self._install():
                raise Exception('Unable to find or install subversion')

    def clone(self, url, envars, username, password, private_key):
        # Add username and password to url
        if username and password:
            url = url.replace('://','://' + username + ':' + password + '@')

        command = self.svn_cmd + " co '" + url + "' ."

        out,stdout,stderr = self._execute_command(command = command, workdir = self.working_dir, envars = envars)
        result_exec = self._format_output(out,stdout,stderr)

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
        which_posix  = procutils.which('svn')
        which_win    = procutils.which('svn.cmd')

        try: self.svn_cmd = which_posix[0]
        except IndexError:
            try: self.svn_cmd = which_win[0]
            except IndexError:
                return False

        return True

    def _install(self):
        out,stdout,stderr = self._install_package('subversion')
        return self._is_available()

class File(ectools):
    def __init__(self,working_dir,rotate):
        if not working_dir:
            raise Exception("Invalid path")

        self.working_dir = working_dir
        self.rotate = rotate

        # Create or rename working_dir
        deploy = Deploy(self.working_dir,rotate)
        self.old_dir = deploy.prepare()

    def clone(self, envars, url, username, password, private_key):
        file_name = 'downloaded.file'
        tmp_dir = mkdtemp()

        file_downloaded = self._download_file(
            url = url,
            file = tmp_dir + '/' + file_name,
            user = username,
            passwd = password
        )

        if file_downloaded:
            extract = self._extract(file_downloaded)
            if extract:
                extract['head'] = ''
                if extract.get('stdout',None):
                    extract['head'] = self._output("Source deployed successfully to '%s'" % self.working_dir)

                if extract.get('stdout',None) and self.old_dir:
                    extract['head'] += self._output("Old source files moved to '%s'" % self.old_dir)

        else:
            rmtree(tmp_dir, ignore_errors = True)
            raise Exception("Unable to download file")

        # Clean and output
        rmtree(tmp_dir, ignore_errors = True)
        ret = {
            'stdout': extract.get('head','') + extract.get('stdout',''),
            'stderr': extract.get('stderr','Unable to download file'),
            'out': extract.get('out',1)
        }
        return ret

    def _extract(self, file):
        try:
            file_type = self._get_file_type(file)
            if file_type == 'zip':
                opener, mode = zipfile.ZipFile, 'r'

            elif file_type == 'gz':
                opener, mode = tarfile.open, 'r:gz'

            elif file_type == 'bz2':
                opener, mode = tarfile.open, 'r:bz2'

            else:
                raise Exception("Unsupported file compression")

            cfile = opener(file, mode)

            # if first member is dir, skip 1st container path
            is_packed = None
            if(file_type == 'zip'):
                members = cfile.namelist()
            else:
                members = cfile.getmembers()
                if members[0].isdir():
                    is_packed = members[0].name

            stdout = ''
            if is_packed:
                for member in members:
                    member.name = member.name.replace(is_packed,'.')
                    if member.name.endswith('/.'): continue
                    if member.name == './': continue
                    if member.name == '.': continue

                    stdout +=  "Extracted " + member.name + "\n"
                    cfile.extract(member,self.working_dir)
            else:
                for member in members:
                    if(file_type == 'zip'): member_name = member
                    else: member_name = member.name

                    stdout +=  "Extracted " + member_name + "\n"
                cfile.extractall(self.working_dir)
            cfile.close()

        except Exception as e:
            raise Exception("Could not extract file: %s" % e)

        ret = { 'out': 0, 'stderr': '', 'stdout': stdout }
        return ret

    def _get_file_type(self,file):
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

    def _download_file(self, url, file, user = None, passwd=None):
        try:
            if user and passwd:
                password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
                password_manager.add_password(None, url, user, passwd)

                auth_manager = urllib2.HTTPBasicAuthHandler(password_manager)
                opener = urllib2.build_opener(auth_manager)

                # ...and install it globally so it can be used with urlopen.
                urllib2.install_opener(opener)

            req = urllib2.urlopen(url.replace("'",""))
            CHUNK = 256 * 10240
            with open(file, 'wb') as fp:
                while True:
                    chunk = req.read(CHUNK)
                    if not chunk: break
                    fp.write(chunk)
        except:
            return False

        return file


class Deploy(ectools):
    def __init__(self, working_dir, rotate):
        self.working_dir = os.path.abspath(working_dir)
        self.rotate = rotate

    def prepare(self):
        to_dir = None
        if self.rotate and os.path.isdir(self.working_dir):
            if not self.working_dir == '/':
                to_dir = self.working_dir + '_rotated_' + self._utime()
                move(self.working_dir,to_dir)

        # create working dir
        if not os.path.isdir(self.working_dir):
            self._mkdir_p(self.working_dir)

        return to_dir

    def rollback(self,path):
        return

ECMSource().run()
