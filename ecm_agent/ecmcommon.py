# -*- coding:utf-8 -*-

import os, string, random, re
import platform
import urllib2

from subprocess import call
from subprocess import Popen, PIPE
from time import time
from shlex import split

from threading import Thread
import sys
import fcntl

class ECMCommon():
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
        ''' Remove color chars from output
        '''
        r = re.compile("\033\[[0-9;]*m", re.MULTILINE)
        return r.sub('', output)

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
        """ Try to install packages
        """
        try:
            (distribution,version,tmp)=platform.dist()

            if distribution.lower() == 'debian' or distribution.lower() == 'ubuntu':
                os.environ['DEBIAN_FRONTEND'] = 'noninteractive'

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

            out,stdout,stderr = self._execute_command(command)
            return out

        except Exception as e:
            raise Exception("Error installing packages %s: %s" % packages,e)

    def _execute_command(self, command, stdin = None, runas=None, workdir = None, envars=None):
        """
        """
        self.stdout = ''
        self.stderr = ''

        # Create a full command line splited later
        if isinstance(command, list):
            command = ' '.join(command)

        if workdir: path = os.path.abspath(workdir)

        # Set environment variables
        if envars:
            try:
                for envar in envars:
                    if not envars[envar]: envars[envar] = ''
                    os.environ[envar] = str(envars[envar])
            except: pass

        if runas:
            command = ['su','-',runas,'-c',command]
        else:
            command = split(command)

        try:
            p = Popen(
                command,
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
        # set executable flag to file
        os.chmod(file,0700)
        command = [file]

        self.stdout = ''
        self.stderr = ''

        # Set environment variables
        if envars:
            try:
                for envar in envars:
                    if not envars[envar]: envars[envar] = ''
                    os.environ[envar] = str(envars[envar])
            except: pass


        try:
            if runas:
                command = ['su','-','-c',file]
                # Change file owner before execute
                self._chown(path=file,user=runas,group='root',recursive=True)

            p = Popen(
                command,
                bufsize=0,  stdin = PIPE, stdout=PIPE, stderr=PIPE,
                cwd=workdir, universal_newlines=True, close_fds=(os.name=='posix')
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

    def _flush_worker(self, stdout, stderr):
        ''' needs to be in a thread so we can read the stdout w/o blocking '''
        while True:
            output = self._clean_stdout(self._non_block_read(stdout))
            if output:
                self.stdout += output
                sys.stdout.write(output)
            output = self._clean_stdout(self._non_block_read(stderr))
            if output:
                self.stderr += output
                sys.stderr.write(output)

    def _non_block_read(self, output):
        ''' even in a thread, a normal read with block until the buffer is full '''
        fd = output.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return output.read()
        except:
            return ''

    def _renice_me(self, nice):
        if nice and self.is_number(nice):
            try:
                os.nice(int(nice))
                return(0)

            except:
                return(1)
        else:
            return(1)

    def is_number(self,s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _output(self,string):
        return '[' + str(time()) + '] ' + str(string) + "\n"

    def _format_output(self,out,stdout,stderr):
        format_out = {}
        format_out['out'] = out
        format_out['stdout'] = stdout
        format_out['stderr'] = stderr

        return format_out

    def _mkdir_p(self,path):
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except OSError as e:
            pass

    def _utime(self):
        str_time = str(time()).replace('.','_')
        return str_time
