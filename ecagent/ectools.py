# -*- coding:utf-8 -*-

import os, string, random, re
import platform
import urllib2

from subprocess import Popen, PIPE
from time import time
from shlex import split
from base64 import b64decode
from threading import Thread

import simplejson as json
import sys
import fcntl

class ECTools():
    def _file_write(self,file,content=None):
        try:
            if content:
                _path = os.path.dirname(file)
                if not os.path.exists(_path):
                    os.mkdir(_path)

                f = open(file,'w')
                f.write(content)
                f.close()

        except:
            raise Exception("Unable to write file: %s" % file)

    def _file_read(self,file):
        try:
            if os.path.isfile(file):
                f = open(file,'r')
                retval = f.read()
                f.close()
                return retval

        except:
            raise Exception("Unable to read file: %s" % file)

    def _secret_gen(self):
        chars = string.ascii_uppercase + string.digits  + '!@#$%^&*()'
        return ''.join(random.choice(chars) for x in range(60))

    def _clean_stdout(self,output):
        """ Remove color chars from output
        """
        try:
            r = re.compile("\033\[[0-9;]*m", re.MULTILINE)
            return r.sub('', output)
        except:
            return output

    def _download_file(self, url, file):
        """ Downloads remote file
        """
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

    def _chmod(self, file, mode):
        try:
            os.chmod(file,mode)
            return True

        except:
            return False

    def _chown(self, path, user, group, recursive = True):
        try:
            from pwd import getpwnam
            from grp import getgrnam

            uid = 0
            gid = 0
            try: uid = getpwnam(user)[2]
            except KeyError: pass

            try: gid = getgrnam(group)[2]
            except KeyError: pass

            if recursive:
                # Recursive chown
                if not os.path.isdir(path):
                    return False

                for root, dirs, files in os.walk(path):
                    os.chown(os.path.join(path, root), uid, gid)
                    for f in files:
                        os.chown(os.path.join(path, root, f), uid, gid)
            else:
                # Just file or path
                os.chown(path, uid, gid)

        except:
            return False

        return True

    def _install_package(self,packages,update = True):
        """ Install packages
        """
        envars = {}
        try:
            (distribution,version,tmp)=platform.dist()

            if distribution.lower() == 'debian' or distribution.lower() == 'ubuntu':
                envars['DEBIAN_FRONTEND'] = 'noninteractive'

                if update: self._execute_command(['apt-get','-y','-qq','update'])
                command = ['apt-get','-o','Dpkg::Options::=--force-confold',
                           '--allow-unauthenticated','--force-yes',
                           '-y','-qq','install',packages]

            elif distribution.lower() == 'centos' or distribution.lower() == 'redhat' or distribution.lower() == 'fedora':
                if update: self._execute_command(['yum','-y','clean','all'])
                command = ['yum','-y','--nogpgcheck','install',packages]

            elif distribution.lower() == 'arch':
                if update: self._execute_command(['pacman','-Sy'])
                if update: self._execute_command(['pacman','-S','--noconfirm','pacman'])
                command = ['pacman','-S','--noconfirm',packages]

            else:
                raise Exception("Distribution not supported: " + distribution)

            out,stdout,stderr = self._execute_command(command, envars=envars)
            return out,stdout,stderr

        except Exception as e:
            raise Exception("Error installing packages %s: %s" % packages,e)

    def _execute_command(self, command, stdin = None, runas=None, workdir = None, envars=None):
        """ Execute command and flush stdout/stderr using threads
        """
        self.stdout = ''
        self.stderr = ''

        # Create a full command line to split later
        if isinstance(command, list):
            command = ' '.join(command)

        if workdir:
            workdir = os.path.abspath(workdir)

        if runas:
            command = ['su','-',runas,'-c',command]
        else:
            command = split(command)

        # Get current env
        if not envars or not isinstance(envars, dict):
            envars = {}

        for env in os.environ.keys():
            envars[env] = os.environ[env]

        try:
            p = Popen(
                command,
                env = envars,
                bufsize=0, stdin = PIPE, stdout=PIPE, stderr=PIPE,
                cwd=workdir,
                universal_newlines=True,
                close_fds=(os.name=='posix')
            )

            # Write stdin
            if stdin: p.stdin.write(stdin)

            thread = Thread(target=self._flush_worker, args=[p.stdout,p.stderr])
            thread.daemon = True
            thread.start()
            thread.join(timeout=1)

            return p.wait(),self.stdout,self.stderr

        except Exception as e:
            return 255,'',e

    def _execute_file(self, file, stdin=None, runas=None, workdir = None, envars = None):
        """ Execute a script file and flush stdout/stderr using threads
        """

        self.stdout = ''
        self.stderr = ''

        # Get current env
        if not envars or not isinstance(envars, dict):
            envars = {}

        for env in os.environ.keys():
            envars[env] = os.environ[env]

        if workdir:
            workdir = os.path.abspath(workdir)

        try:
            if runas:
                command = ['su','-','-c',file]
                # Change file owner before execute
                self._chown(path=file,user=runas,group='root',recursive=True)

            # +x flag to file
            os.chmod(file,0700)
            command = [file]

            p = Popen(
                command,
                env = envars,
                bufsize=0,  stdin = PIPE, stdout=PIPE, stderr=PIPE,
                cwd=workdir,
                universal_newlines=True,
                close_fds=(os.name=='posix')
            )

            # Write stdin
            if stdin:
                p.stdin.write(stdin)

            thread = Thread(target=self._flush_worker, args=[p.stdout,p.stderr])
            thread.daemon = True
            thread.start()
            thread.join(timeout=1)

            return p.wait(),self.stdout,self.stderr

        except Exception as e:
            return 255,'',e

    def _flush_worker(self, stdout, stderr):
        ''' needs to be in a thread so we can read the stdout w/o blocking '''
        while True:
            # Avoid Exception in thread Thread-1 (most likely raised during interpreter shutdown):
            try:
                output = self._clean_stdout(self._non_block_read(stdout))
                if output:
                    self.stdout += output
                    sys.stdout.write(output)

                output = self._clean_stdout(self._non_block_read(stderr))
                if output:
                    self.stderr += output
                    sys.stderr.write(output)
            except:
                pass

    def _non_block_read(self, output):
        ''' even in a thread, a normal read with block until the buffer is full '''
        try:
            fd = output.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            return output.read()

        except:
            return ''

    def _envars_decode(self,coded_envars = None):
        ''' Decode base64/json envars '''
        envars = None
        try:
            if coded_envars:
                envars = b64decode(coded_envars)
                envars = json.loads(envars)
                for var in envars.keys():
                    if not envars[var]: envars[var] = ''
                    envars[var] = str(envars[var])

        except: pass
        return envars

    def _set_envars(self,envars):
        ''' Sets os environment variables '''
        if envars:
            try:
                for envar in envars:
                    os.environ[envar] = str(envars[envar])
            except: pass

    def _renice_me(self, nice):
        ''' Changes execution priority  '''
        if nice and self.is_number(nice):
            try:
                os.nice(int(nice))
                return(0)

            except:
                return(1)
        else:
            return(1)

    def is_number(self,s):
        ''' Helper function '''
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _output(self,string):
        ''' Helper function '''
        return '[' + str(time()) + '] ' + str(string) + "\n"

    def _format_output(self,out,stdout,stderr):
        ''' Helper function '''
        format_out = {}
        format_out['out'] = out
        format_out['stdout'] = stdout
        format_out['stderr'] = stderr

        return format_out

    def _mkdir_p(self,path):
        ''' Recursive Mkdir '''
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except OSError:
            pass

    def _utime(self):
        ''' Helper function: microtime '''
        str_time = str(time()).replace('.','_')
        return str_time
