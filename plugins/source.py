# -*- coding:utf-8 -*-

from ecmplugin import ECMPlugin

from subprocess import Popen, PIPE
from shlex import split
from tempfile import mkdtemp
from base64 import b64decode
from urlparse import urlparse
import urllib2

import os
import twisted.python.procutils as procutils

import simplejson as json

from time import time
from shutil import move, rmtree

try:
    import tarfile
    import zipfile
except:
    pass

class ECMSource(ECMPlugin):
    def cmd_source_run(self, *argv, **kwargs):
        self.path           = kwargs.get('path',None)
        self.source         = kwargs.get('source',None)

        self.envars         = kwargs.get('envars',None)

        self.user           = kwargs.get('username',None)
        self.passwd         = kwargs.get('password',None)
        self.private_key    = kwargs.get('private_key',None)

        self.chown_user     = kwargs.get('chown_user',None)
        self.chown_group    = kwargs.get('chown_group',None)

        if (not self.path or not self.source):
            raise Exception("Invalid parameters")

        type = kwargs.get('type',None)

        if type and type.upper() in ('URI','FILE'):
            source = File(self.path)

        elif type and type.upper() == 'GIT':
            source = Git(self.path)

        elif type and type.upper() == 'SVN':
            source = Svn(self.path)

        else: raise Exception("Unknown source")

        retval = source.clone(url=self.source, envars=self.envars, \
            username=self.user, password=self.passwd, private_key=self.private_key)

        # Chown to specified user/group
        if self.chown_user and self.chown_group and os.path.isdir(self.path):
            self._chown(self.path,self.chown_user,self.chown_group)

        return self._return(retval)

    def _return(self,ret):
        output = {}
        try:
            output['out']    = ret.get('status',1)
            output['stderr'] = ret.get('stderr','')
            output['stdout'] = ret.get('stdout','')
        except:
            output['out']    = 1
            output['stderr'] = ret.get('stderr','')
            output['stdout'] = ret.get('stdout','')

        return output

class Deploy(object):
    def __init__(self, working_dir):
        self.working_dir = os.path.abspath(working_dir)

    def rotate(self):
        # Rotate if exists
        to_dir = None
        if os.path.isdir(self.working_dir):
            to_dir = self.working_dir + '_rotated_' + self._utime()
            move(self.working_dir,to_dir)

        # create working dir
        self._mkdir_p(self.working_dir)
        return to_dir

    def rollback(self,path):
        # to be done
        pass

    def _mkdir_p(self,path):
        try:
            os.makedirs(path)
        except OSError as e:
            pass

    def _utime(self):
        str_time = str(time()).replace('.','_')
        return str_time


class Git(object):
    def __init__(self, working_dir = None):
        if not working_dir:
            raise Exception("Invalid path")
        self.working_dir = working_dir

        # Create or rename working_dir
        deploy = Deploy(self.working_dir)
        self.old_dir = deploy.rotate()

        which_posix  = procutils.which('git')
        which_win    = procutils.which('git.cmd')

        try: self.git_cmd = which_posix[0]
        except IndexError:
            try: self.git_cmd = which_win[0]
            except IndexError:
                raise Exception("Unable to find git on path")

    def clone(self, url, envars, username, password, private_key):

        command = self.git_cmd + " clone --quiet --verbose '" + url + "' ."

        # Create git command with user and password
        if username and password:
            parsed = urlparse(url)
            if parsed.scheme in ('http','https'):
                command = command.replace('://','://' + username + ':' + password + '@')
            elif parsed.scheme == 'ssh':
                command = command.replace('://','://' + username + '@')


        result_exec = Aux().myexec(command,path=self.working_dir,envars=envars)
        extra_msg = ''
        if not result_exec['status']:
            extra_msg = "Source deployed successfully to '%s'\n" % self.working_dir
            if self.old_dir:
                extra_msg += "Old source files moved to '%s'\n" % self.old_dir
            result_exec['stdout'] = extra_msg

        return result_exec

class Svn(object):
    def __init__(self, working_dir = None):
        if not working_dir:
            raise Exception("Invalid path")
        self.working_dir = working_dir

        # Create or rename working_dir
        deploy = Deploy(self.working_dir)
        self.old_dir = deploy.rotate()

        which_posix  = procutils.which('svn')
        which_win    = procutils.which('svn.cmd')

        try: self.svn_cmd = which_posix[0]
        except IndexError:
            try: self.svn_cmd = which_win[0]
            except IndexError:
                raise Exception("Unable to find svn on path")

    def clone(self, url, envars, username, password, private_key):

        # Add username and password to url
        if username and password:
            url = url.replace('://','://' + username + ':' + password + '@')

        command = self.svn_cmd + " co '" + url + "' ."

        result_exec = Aux().myexec(command,path=self.working_dir,envars=envars)

        if not result_exec['status']:
            extra_msg = "Source deployed successfully to '%s'\n" % self.working_dir
            if self.old_dir:
                extra_msg += "Old source files moved to '%s'\n" % self.old_dir
            if result_exec['stdout']:
                result_exec['stdout'] = extra_msg + result_exec['stdout']
            else:
                result_exec['stdout'] = extra_msg

        return result_exec

class File:
    def __init__(self,working_dir = None):
        if not working_dir:
            raise Exception("Invalid path")
        self.working_dir = working_dir

        # Create or rename working_dir
        deploy = Deploy(self.working_dir)
        self.old_dir = deploy.rotate()

    def clone(self, envars, url, username, password, private_key):

        # Add username and password to url
        if username and password:
            url = url.replace('://','://' + username + ':' + password + '@')

        file_name = 'downloaded.file'
        tmp_dir = mkdtemp()

        file_downloaded = self._download_file(
            url = url,
            file = tmp_dir + '/' + file_name
        )

        if file_downloaded:
            extract = self._extract(file_downloaded)
            if extract:
                extract['head'] = ''
                if extract.get('stdout',None):
                    extract['head']  = "Source deployed successfully to '%s'\n" % self.working_dir
                if extract.get('stdout',None) and self.old_dir:
                    extract['head'] += "Old source files moved to '%s'\n" % self.old_dir

        else:
            rmtree(tmp_dir, ignore_errors = True)
            raise Exception("Unable to download file")

        # Clean and output
        rmtree(tmp_dir, ignore_errors = True)
        ret = {}
        ret['stdout'] = extract.get('head','') + extract.get('stdout','')
        ret['stderr'] = extract.get('stderr','Unable to download file')
        ret['status'] = extract.get('status',1)
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

            first_path = None
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

        ret = {}
        ret['status'] = 0
        ret['stderr'] = ''
        ret['stdout'] = stdout

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

    def _download_file(self, url, file):
        try:
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

class Aux:
    def myexec(self, command, path=None, envars=None):

        # Set environment variables before execute
        try:
            if envars:
                envars = b64decode(envars)
                envars = json.loads(envars)
                for envar in envars:
                    if not envars[envar]: envars[envar] = ''
                    os.environ[envar] = str(envars[envar])
        except:
            # Ignore it
            pass

        if path: path = os.path.abspath(path)
        p = Popen(split(command),
                  cwd=path,
                  stdin=None,
                  stderr=PIPE,
                  stdout=PIPE,
                  close_fds=(os.name=='posix') # unsupported on linux
        )
        _stdout, _stderr = p.communicate()

        ret = {}
        ret['status'] = p.wait()
        ret['stderr'] = str(_stderr)
        ret['stdout'] = str(_stdout)

        return ret

ECMSource().run()
