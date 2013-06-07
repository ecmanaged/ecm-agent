# -*- coding:utf-8 -*-

import os, string, random, re
import platform
import urllib2

from subprocess import call
from subprocess import Popen, PIPE
from time import time
from shlex import split

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
        r = re.compile("\033\[[0-9;]+m", re.MULTILINE)
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

                if update: call(['apt-get','-y','-qq','update'])
                ret_code = call(['apt-get','-o','Dpkg::Options::=--force-confold',
                                '--allow-unauthenticated','--force-yes',
                                 '-y','-qq','install',packages])

            elif distribution.lower() == 'centos' or distribution.lower() == 'redhat' or distribution.lower() == 'fedora':
                if update: call(['yum','-y','clean','all'])
                ret_code = call(['yum','-y','--nogpgcheck','install',packages])

            elif distribution.lower() == 'arch':
                if update: call(['pacman','-Sy'])
                if update: call(['pacman','-S','--noconfirm','pacman'])
                ret_code = call(['pacman','-S','--noconfirm',packages])

            else:
                raise Exception("Distribution not supported: " + distribution)

            return ret_code

        except Exception as e:
            raise Exception("Error installing packages %s: %s" % packages,e)

    def _execute_command(self, command, runas=None, workdir = None, envars=None):
        """
        """
        if workdir: path = os.path.abspath(workdir)

        # Set environment variables
        if envars:
            try:
                for envar in envars:
                    if not envars[envar]: envars[envar] = ''
                    os.environ[envar] = str(envars[envar])
            except: pass

        try:
            if(runas):
                p = Popen(['su', runas],
                            stdin=PIPE,
                            stdout=PIPE,
                            stderr=PIPE,
                            cwd=workdir,
                            close_fds=(os.name=='posix')
                )
                stdout, stderr = p.communicate(command)

            else:
                p = Popen(split(command),
                            stdin=PIPE,
                            stdout=PIPE,
                            stderr=PIPE,
                            cwd=workdir,
                            close_fds=(os.name=='posix')
                )
                stdout, stderr = p.communicate()

            return p.wait(),stdout,stderr

        except Exception as e:
            return 255,'',e

    def _execute_file(self, file, runas=None, workdir = None):
        cmd = []
        cmd.append(file)

        # set executable flag to file
        os.chmod(file,0700)

        try:
            if(runas):
                # Change owner and execute
                self._chown(path=file,user=runas,group='root',recursive=True)
                p = Popen(['su', runas],
                          stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=workdir)
                stdout, stderr = p.communicate(' '.join(cmd))

            else:
                p = Popen(cmd,
                          stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=workdir)
                stdout, stderr = p.communicate()

            return p.wait(),stdout,stderr

        except Exception as e:
            return 255,'',e

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

    def _mkdir_p(self,path):
        try:
            if not os.path.isdir(path):
                os.makedirs(path)
        except OSError as e:
            pass

    def _utime(self):
        str_time = str(time()).replace('.','_')
        return str_time

