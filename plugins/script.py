# -*- coding:utf-8 -*-

from smplugin import SMPlugin

from subprocess import Popen, PIPE
from shlex import split
from tempfile import mkdtemp

from base64 import b64decode
from shutil import rmtree
from os import chmod, environ

import simplejson as json
import stat
	
class ECMscript(SMPlugin):
	def cmd_script_run(self, *argv, **kwargs):
	
		script_base64		= kwargs.get('script',None)
		script_executable	= kwargs.get('executable',None)
		script_envars		= kwargs.get('envars',None)
		
		if not script_base64:
			raise Exception("Invalid argument")

		try:
			# Write down
			tmp_dir = mkdtemp()
			tmp_file = tmp_dir + '/script'
			fh = open(tmp_file, "wb")
			fh.write(b64decode(script_base64))
			fh.close()

		except:
			rmtree(tmp_dir, ignore_errors = True)
			raise Exception("Unable to decode script")


		cmd = []
		if script_executable: 
			# Add executable to comand
			cmd = split(script_executable)
		else:
			# Set as executable by owner if not excplicit executable
			chmod(tmp_file, stat.S_IEXEC)
			
		# Add temp file as last argument (or first if not executable)
		cmd.append(tmp_file)
			
		# Set environment variables before execute
		try:
			if script_envars:
				script_envars = b64decode(script_envars)
				script_envars = json.loads(script_envars)
				for envar in script_envars:
					if not script_envars[envar]: script_envars[envar] = ''
					environ[envar] = script_envars[envar]
		except:
			# Ignore it
			pass
		
		# Execute but don't try/catch to get real error
		p = Popen(cmd,
			stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=tmp_dir)
		stdout, stderr = p.communicate()

		ret = {}
		ret['out'] = p.wait()
		ret['stdout'] = str(stdout)
		ret['stderr']  = str(stderr)
		
		# Clean
		rmtree(tmp_dir, ignore_errors = True)

		return ret

ECMscript().run()
