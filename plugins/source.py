# -*- coding:utf-8 -*-

from smplugin import SMPlugin

from subprocess import Popen, PIPE
from shlex import split
from tempfile import mkdtemp

import os
import twisted.python.procutils as procutils
import urllib2
import simplejson as json

from time import time
from shutil import move, rmtree

try:
    import tarfile
    import zipfile
except Exception as e:
    pass

class ECMsource(SMPlugin):
    def cmd_source_run(self, *argv, **kwargs):
        type = kwargs.get('type',None)

        if type and type.upper() == 'URI':
            ret = self._cmd_source_file_download(*argv, **kwargs)
        elif type and type.upper() == 'FILE':
            ret = self._cmd_source_file_download(*argv, **kwargs)
        elif type and type.upper() == 'GIT':
            ret = self._cmd_source_git_clone(*argv, **kwargs)
        elif type and type.upper() == 'SVN':
            ret = self._cmd_source_svn_co(*argv, **kwargs)
        else:
            raise Exception("Unknown source")
            
        return self._return(ret)
    
    def _cmd_source_git_clone(self, *argv, **kwargs):
        path   = kwargs.get('path',None)
        source = kwargs.get('source',None)
        envars = kwargs.get('envars',None)

        if (not path or not source):
            raise Exception("Invalid parameters")
        
        git = Git(path)
        return git.clone(git_url=source, envars=envars)

    def _cmd_source_svn_co(self, *argv, **kwargs):
        path   = kwargs.get('path',None)
        source = kwargs.get('source',None)
        envars = kwargs.get('envars',None)

        if (not path or not source):
            raise Exception("Invalid parameters")
        
        svn = Svn(path)
        return svn.clone(svn_url=source, envars=envars)


    def _cmd_source_file_download(self, *argv, **kwargs):
        path   = kwargs.get('path',None)
        source = kwargs.get('source',None)
        envars = kwargs.get('envars',None)
        
        if (not path or not source):
            raise Exception("Invalid parameters")
        
        file = File(path)
        return file.download_extract(file_url=source,envars=envars)
        
    def _return(self,ret):
        output = {}
        try:
            output['out']    = ret.get('status',1)
            output['stderr'] = ret.get('stderr','')
            output['stdout'] = ret.get('stdout','')
        except Exception as e:
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
        
    def clone(self, git_url, envars, user='git', password='nopass'):
        # Create git command with user and password
        command = self.git_cmd + " clone --quiet --verbose '" + git_url + "' ."
#        command = command.replace('://','://' + user + ':' + password + '@')
        
        result_exec = Aux().myexec(command,path=self.working_dir,envars=envars)
        extra_msg = ''
        if not result_exec['status']:
            extra_msg = "Origin deployed successfully to '%s'\n" % self.working_dir
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
        
    def clone(self, svn_url, envars, user='svn', password='nopass'):
        # Create svn command with user and password
        command = self.svn_cmd + " co '" + svn_url + "' ."
#        command = command.replace('://','://' + user + ':' + password + '@')
        
        result_exec = Aux().myexec(command,path=self.working_dir,envars=envars)
        extra_msg = ''
        if not result_exec['status']:
            extra_msg = "Origin deployed successfully to '%s'\n" % self.working_dir
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
 
    def download_extract(self, envars, file_url, user='anonymous', password='nopass'):
        # Add username and password to url (FIXME)
#        file_url = file_url.replace('://','://' + user + ':' + password + '@')
        
        extract = {}
        ret = {}
        file_name = 'downloaded.file'
        tmp_dir = mkdtemp()
        
        file_downloaded = self._download(
            url = file_url, 
            file = tmp_dir + '/' + file_name
        )
        if file_downloaded:
            extract = self._extract(file_downloaded)
            if extract:
                extract['head'] = ''
                if extract.get('stdout',None): 
                    extract['head']  = "Origin deployed successfully to '%s'\n" % self.working_dir
                if extract.get('stdout',None) and self.old_dir: 
                    extract['head'] += "Old source files moved to '%s'\n" % self.old_dir

        else:
            rmtree(tmp_dir, ignore_errors = True)
            raise Exception("Unable to download file")

        # Clean and output
        rmtree(tmp_dir, ignore_errors = True)
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
            members = cfile.getmembers()
            if members[0].isdir():
               is_packed = members[0].name

            stdout = ''
            if is_packed:
                for member in members:
                    member.name = member.name.replace(is_packed,'.')
                    if member.name == '.': continue
                    stdout +=  "Extracted " + member.name + "\n"
                    cfile.extract(member,self.working_dir)
            else:
                cfile.extractall(self.working_dir)
            cfile.close()
                
        except Exception as e:
            raise Exception("Could not extract file")
    
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


    def _download(self, url, file):
	try:
            req = urllib2.urlopen(url.replace("'",""))
            total_size = int(req.info().getheader('Content-Length').strip())
            downloaded = 0
            CHUNK = 256 * 10240
            with open(file, 'wb') as fp:
                while True:
                    chunk = req.read(CHUNK)
                    downloaded += len(chunk)
                    if not chunk: break
                    fp.write(chunk)
        except Exception as e:
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
                    os.environ[envar] = envars[envar]
        except Exception as e:
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

ECMsource().run()
