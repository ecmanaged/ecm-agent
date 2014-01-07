# -*- coding:utf-8 -*-

import os, string, random, re
import platform
import urllib2

from subprocess import Popen, PIPE
from time import time
from shlex import split
from base64 import b64decode
from threading import Thread
from time import sleep
from platform import system

import twisted.python.procutils as procutils

import simplejson as json
import sys

if not sys.platform.startswith("win32"):
    import fcntl

DIR = '/etc/ecmanaged'
ENV_FILE = DIR + '/ecm_env'
INFO_FILE = DIR + '/node_info'

FLUSH_WORKER_SLEEP_TIME = 0.2

DEFAULT_GROUP_LINUX = 'root'
DEFAULT_GROUP_WINDOWS = 'Administrators'

class ectools():
    def __init__(self):
        self.thread_stdout = ''
        self.thread_stderr = ''
        self.thread_run = 1

    def _is_windows(self):
        """ Returns True if is a windows system
        """
        if sys.platform.startswith("win32"):
            return True

        return False

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
        """ Reads a file and returns content
        """
        try:
            if os.path.isfile(file):
                f = open(file,'r')
                retval = f.read()
                f.close()
                return retval

        except:
            raise Exception("Unable to read file: %s" % file)

    def _secret_gen(self,length = 60):
        """ Generates random chars
        """
        chars = string.ascii_uppercase + string.digits  + '!@#$%^&*()'
        return ''.join(random.choice(chars) for x in range(length))

    def _clean_stdout(self,output):
        """ Remove color chars from output
        """
        try:
            r = re.compile("\033\[[0-9;]*m", re.MULTILINE)
            return r.sub('', output)
        except:
            return output

    def _download_file(self, url, file, user = None, passwd=None):
        """ Downloads remote file
        """

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

    def _chmod(self, file, mode):
        """ chmod a file
        """
        try:
            os.chmod(file,mode)
            return True

        except:
            return False

    def _which(self,command):
        """ search executable on path
        """
        found = procutils.which(command)

        try: cmd = found[0]
        except IndexError:
            return False

        return cmd

    def _chown(self, path, user, group, recursive = False):
        """ chown a file or path
        """
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

    def _execute_command(self, command, args=None, stdin=None, runas=None, workdir=None, envars=None):
        """ Execute command and flush stdout/stderr using threads
        """
        self.thread_stdout = ''
        self.thread_stderr = ''
        self.thread_run = 1

        # Create a full command line to split later
        if self.is_list(command):
            command = ' '.join(command)

        if workdir:
            workdir = os.path.abspath(workdir)

        # create command array and add args
        command = split(command)
        if args and self.is_list(args):
            for arg in args:
                command.append(arg)

        if runas:
            if not self._is_windows():
                command = ['su','-',runas,'-c',' '.join(map(str,command))]

            # :TODO: Runas for windows

        # Get current env
        if not envars or not self.is_dict(envars):
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

            # Write stdin if set
            if stdin:
                p.stdin.write(stdin)
                p.stdin.flush()
                p.stdin.close()

            if self._is_windows():
                stdout, stderr = p.communicate()
                return p.wait(),stdout,stderr

            else:
                thread = Thread(target=self._thread_flush_worker, args=[p.stdout,p.stderr])
                thread.daemon = True
                thread.start()

                # Wait for end
                retval = p.wait()

                # Ensure to get last output from Thread
                sleep(FLUSH_WORKER_SLEEP_TIME*2)

                # Stop Thread
                self.thread_run = 0
                thread.join(timeout=1)

                return retval,self.thread_stdout,self.thread_stderr

        except OSError, e:
            return e[0], '', "Execution failed: %s" % e[1]

        except Exception as e:
            return 255,'','Unknown error'

    def _execute_file(self, file,  args=None, stdin=None, runas=None, workdir = None, envars = None):
        """ Execute a script file and flush stdout/stderr using threads
        """
        self.thread_stdout = ''
        self.thread_stderr = ''
        self.thread_run = 1

        # Get current env
        if not envars or not self.is_dict(envars):
            envars = {}

        for env in os.environ.keys():
            envars[env] = os.environ[env]

        if workdir:
            workdir = os.path.abspath(workdir)

        try:
            # +x flag to file
            os.chmod(file,0700)
            command = [file]

            # Add command line args
            if args and self.is_list(args):
                for arg in args:
                    command.append(arg)

            if runas:
                if not self._is_windows():
                    # Change file owner before execute
                    self._chown(path=workdir,user=runas,group=DEFAULT_GROUP_LINUX,recursive=True)
                    command = ['su','-',runas,'-c',' '.join(map(str,command))]

                # :TODO: Runas for windows

            p = Popen(
                command,
                env = envars,
                bufsize=0,  stdin = PIPE, stdout=PIPE, stderr=PIPE,
                cwd=workdir,
                universal_newlines=True,
                close_fds=(os.name=='posix')
            )

            # Write stdin if set
            if stdin:
                p.stdin.write(stdin)
                p.stdin.flush()
                p.stdin.close()

            if self._is_windows():
                stdout, stderr = p.communicate()
                return p.wait(),stdout,stderr

            else:
                thread = Thread(target=self._thread_flush_worker, args=[p.stdout,p.stderr])
                thread.daemon = True
                thread.start()

                # Wait for end
                retval = p.wait()

                # Ensure to get last output from Thread
                sleep(FLUSH_WORKER_SLEEP_TIME*2)

                # Stop Thread
                self.thread_run = 0
                thread.join(timeout=1)
                
                return retval,self.thread_stdout,self.thread_stderr

        except OSError, e:
            return e[0], '', "Execution failed: %s" % e[1]

        except Exception as e:
            return 255,'','Unknown error'

    def _thread_flush_worker(self, stdout, stderr):
        """ needs to be in a thread so we can read the stdout w/o blocking """
        while self.thread_run:
            # Avoid Exception in thread Thread-1 (most likely raised during interpreter shutdown):
            try:
                output = self._clean_stdout(self._non_block_read(stdout))
                if output:
                    self.thread_stdout += output
                    sys.stdout.write(output)

                output = self._clean_stdout(self._non_block_read(stderr))
                if output:
                    self.thread_stderr += output
                    sys.stderr.write(output)

                sleep(FLUSH_WORKER_SLEEP_TIME)

            except:
                pass

    def _non_block_read(self, output):
        """ even in a thread, a normal read with block until the buffer is full """
        try:
            fd = output.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            return output.read()

        except:
            return ''

    def _envars_decode(self,coded_envars = None):
        """ Decode base64/json envars """
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

    def _write_envars_facts(self, envars=None, facts=None):
        """ Writes env and facts file variables """
        if envars and self.is_dict(envars):
            try:
                content_env = ''
                for var in sorted(envars.keys()):
                    content_env += "export " + str(var) + '="' + str(envars[var]) + "\"\n"
                self._file_write(ENV_FILE,content_env)

            except:
                return False

        if facts and self.is_dict(envars):
            try:
                content_facts= ''
                for var in sorted(facts.keys()):
                    content_facts += str(var) + ':' + str(facts[var]) + "\n"
                self._file_write(INFO_FILE,content_facts)

            except:
                return False

        return True

    def _renice_me(self, nice):
        """ Changes execution priority  """
        if nice and self._is_number(nice):
            try:
                os.nice(int(nice))
                return(0)

            except:
                return(1)
        else:
            return(1)

    def _is_number(self,s):
        """ Helper function """
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _output(self,string):
        """ Helper function """
        return '[' + str(time()) + '] ' + str(string) + "\n"

    def _format_output(self,out,stdout,stderr):
        """ Helper function """
        format_out = {}
        format_out['out'] = out
        format_out['stdout'] = stdout
        format_out['stderr'] = stderr

        return format_out

    def _mkdir_p(self,path):
        """ Recursive Mkdir """
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except OSError:
            pass

    def _utime(self):
        """ Helper function: microtime """
        str_time = str(time()).replace('.','_')
        return str_time

    def is_dict(self,obj):
        """Check if the object is a dictionary."""
        return isinstance(obj, dict)

    def is_list(self,obj):
        """Check if the object is a list"""
        return isinstance(obj, list)

    def is_string(self,obj):
        """Check if the object is a list"""
        if isinstance(obj, str) or isinstance(obj, unicode):
            return True

        return False
