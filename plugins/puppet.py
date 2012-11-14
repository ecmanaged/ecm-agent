# -*- coding:utf-8 -*-

from smplugin import SMPlugin

from subprocess import call, Popen, PIPE
from tempfile import mkdtemp
import urllib2

import tarfile
import platform
from shutil import rmtree
import base64

class ECMPuppet(SMPlugin):

    def cmd_puppet_available(self, *argv, **kwargs):
        if call(['which','puppet'], stdout=PIPE, stderr=PIPE):
            raise Exception("Not found")
        return True
    
    def cmd_puppet_apply(self, *argv, **kwargs):
    
        manifest_base64 = kwargs.get('manifest',None)
        manifest = None
        
        if not manifest_base64:
            raise Exception("Invalid argument")
        
        try:
            manifest = base64.b64decode(manifest_base64)
        except Exception as e:
            raise Exception("Unable to decode manifest")

        try:
            ret = {}
            p = Popen(['puppet', 'apply', '--detailed-exitcodes', '--debug'],
                stdin=PIPE, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate(input=manifest)

            ret['out'] = p.wait()
            ret['stdout'] = str(stdout)
            ret['stderr']  = str(stderr)

            # exit code of '2' means there were changes
            if ret['out'] == 2: ret['out'] = 0 
                
            if ret['out']: 
                raise Exception("Error applying manifest: %s" % ret['stderr'])
                    
            return ret
                
        except Exception as e:
            raise Exception("Error running puppet apply")

    def cmd_puppet_apply_pson(self, *argv, **kwargs):
    
        manifest_pson_base64 = kwargs.get('manifest_pson',None)
        manifest_file = None
        manifest_path = None
        
        if not manifest_pson_base64:
            raise Exception("Invalid argument")
        
        try:
            manifest_path = mkdtemp()
            manifest_file = manifest_path + '/manifest.pson'
            fh = open(manifest_file, "wb")
            fh.write(base64.b64decode(manifest_pson_base64))
            fh.close()

        except Exception as e:
            rmtree(manifest_path, ignore_errors = True)
            raise Exception("Unable to decode manifest")
           
        return self._run_puppet(manifest_file,manifest_path)

    def cmd_puppet_apply_file(self, *argv, **kwargs):

        manifest_url = kwargs.get('manifest_url',None)
        manifest_file = None
        manifest_path = None
        
        if not manifest_url:
            raise Exception("Invalid argument")
        
        try:
            # Download manifest url
            manifest_path = mkdtemp()
            tmp_file = manifest_path + '/manifest.tar.gz'
                
            if self._downloadfile(url=manifest_url,file=tmp_file):
                # decompress
                if tarfile.is_tarfile(tmp_file):
                    tar = tarfile.open(tmp_file)
                    tar.extractall(path=manifest_path)

                    for file_name in tar.getnames():
                       if  file_name.endswith('.catalog.pson'):
                           manifest_file = file_name
                    tar.close()
                    
                    # Apply puppet
                    return self._run_puppet(manifest_file,manifest_path)
                else:
                    raise Exception("Invalid manifest tgz file")
            else:
                raise Exception("Unable to download file")
                    
        except Exception as e:
            raise Exception("Unable get manifest")

        finally:
            rmtree(manifest_path, ignore_errors = True)
            
    def cmd_puppet_install(self, *argv, **kwargs):

        try:
            # raises an exception if not found
            if self.cmd_puppet_available(*argv, **kwargs):
                return False
        except Exception as e:
            pass
            
        try:
       	    (distrib,version,tmp)=platform.dist()
            ret_code = 2
       	
            if distrib.lower() == 'debian' or distrib.lower() == 'ubuntu':
                ret_code = call(['apt-get','-y','-qq','update'])
                ret_code = call(['apt-get','-y','-qq','install','puppet-common'])
                
            elif distrib.lower() == 'centos' or distrib.lower() == 'redhat':
                ret_code = call(['yum','-y','install','puppet'])
            
            elif distrib.lower() == 'arch':
                ret_code = call(['pacman','-y','install','puppet'])
            
            else:
                raise Exception("Distribution not supported: " + distrib)
        
            return ret_code
            
        except Exception as e:
            raise Exception("Error installing puppet")
            

    def _downloadfile(self,url,file):

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

    def _run_puppet(self,manifest_file,manifest_path,module_path='/etc/puppet/modules'):
    
        try:
            ret = {}
            p = Popen(['puppet', 'apply', '--detailed-exitcodes', '--debug',
                '--modulepath',module_path,
                '--catalog',  manifest_file], 
                cwd=manifest_path,
                stdin=None, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
                
            ret['out'] = p.wait()
            ret['stdout'] = str(stdout)
            ret['stderr']  = str(stderr)

            # exit code of '2' means there were changes
            if ret['out'] == 2: ret['out'] = 0 
                
            if ret['out']: 
                raise Exception("Error applying manifest: %s" % ret['stderr'])
                    
            return ret
                
        except Exception as e:
            # Try old --apply
            return self._run_puppet_old_apply(manifest_file,manifest_path,module_path)

        finally:
            # Clean working dir
            rmtree(manifest_path, ignore_errors = True)

    def _run_puppet_old_apply(self,manifest_file,manifest_path,module_path='/etc/puppet/modules'):
    
        try:
            ret = {}
            p = Popen(['puppet', 'apply', '--detailed-exitcodes', '--debug',
                '--modulepath',module_path,
                '--apply',  manifest_file], 
                cwd=manifest_path,
                stdin=None, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
                
            ret['out'] = p.wait()
            ret['stdout'] = str(stdout)
            ret['stderr']  = str(stderr)
            
            # exit code of '2' means there were changes
            if ret['out'] == 2: ret['out'] = 0 
                
            if ret['out']: 
                raise Exception("Error applying manifest: %s" % ret['stderr'])
                    
            return ret
                
        except Exception as e:
            raise Exception("Error running puppet apply")

        finally:
            # Clean working dir
            rmtree(manifest_path, ignore_errors = True)

ECMPuppet().run()
