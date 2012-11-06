# -*- coding:utf-8 -*-

from smplugin import SMPlugin
from time import sleep

from sys import argv, exit, exc_info, stdin, stderr
import inspect
import simplejson as json

# for EC COMMANDS
import os, platform, psutil, re, hashlib

# :TODO: Move to config
PROTECTED_FILES = [
    '/etc/shadow',
]

class ECMBase(SMPlugin):
    def cmd_agent_ping(self, *argv, **kwargs):
        return True
        
    def cmd_file_cat(self, *argv, **kwargs):
        file = kwargs.get('file',None)
        if not file:
            raise Exception('Invalid arguments')
            
        file = os.path.abspath(file)
            
        if not os.path.exists(file):
            raise Exception('File not found')

        # don't cat protected files
        if file in PROTECTED_FILES:
            raise Exception('Not allowed')

        try:
            file = open(file,"r")
            filecontent = file.read()
            file.close()
            return(filecontent)
               
        except:
            raise Exception('Unable to read file')

    def cmd_system_hostname(self, *argv, **kwargs):
        return platform.node()
    
    def cmd_system_load(self, *argv, **kwargs):
        'Load average'

        load_average = ' '.join( [ str(x) for x in os.getloadavg() ] )
        return load_average

    def cmd_system_uname(self, *argv, **kwargs):
        #system,node,release,version,machine,processor
        return platform.uname()
        
    def cmd_system_info(self, *argv, **kwargs):
        'Syntax: system_info'
        
        retr={}
        retr['os']=str(platform.system());
        (retr['os_distrib'],retr['os_version'],tmp)=platform.dist();
        retr['machine']=str(platform.machine());
        
        return retr
    
    def cmd_system_cpu_usage(self, *argv, **kwargs):
        'Syntax: load'
        try:
            return psutil.cpu_percent(interval=5,percpu=True)
        except:
            raise Exception("Unable to get info from psutil")
    
    def cmd_system_uptime(self, *argv, **kwargs):
        'Server uptime'
        
        try:
            f = open('/proc/stat', 'r')
            for line in f:
                if line.startswith('btime'):
                    f.close()
                    return float(line.strip().split()[1])
	    return 0
        except:
            raise Exception("Cannot open uptime file: /proc/stat")

    def cmd_system_disk_partitions(self, *argv, **kwargs):
        try:
            retr=[]
            for part in psutil.disk_partitions(all=False):
               usage = psutil.disk_usage(part.mountpoint)
               strpart={}
               if hasattr(part, 'mountpoint'): strpart['mountpoint'] = part.mountpoint
               if hasattr(part, 'device'):     strpart['device'] = part.device
               if hasattr(part, 'fstype'):     strpart['fstype'] = part.fstype
               retr.append(strpart)
            return retr
        except:
            raise Exception("Unable to get info from psutil")
        
    def cmd_system_disk_usage(self, *argv, **kwargs):
        try:
            retr=[]
            for part in psutil.disk_partitions(all=False):
                usage = psutil.disk_usage(part.mountpoint)
                strpart={}
                if hasattr(part,  'mountpoint'): strpart['mountpoint'] = part.mountpoint
                if hasattr(part,  'device'):     strpart['device'] = part.device
                if hasattr(usage, 'total'):      strpart['total'] = self.aux_convert_bytes(usage.total)
                if hasattr(usage, 'used'):       strpart['used'] = self.aux_convert_bytes(usage.used)
                if hasattr(usage, 'free'):       strpart['free'] = self.aux_convert_bytes(usage.free)  
                if hasattr(usage, 'percent'):    strpart['percent'] = usage.percent
                retr.append(strpart)
            return retr
        except:
	    raise Exception("Unable to get info from psutil")

    def cmd_system_mem_usage(self, *argv, **kwargs):
        try: 
            strmem={}
            psmem = psutil.phymem_usage()
            strmem['total']   = psmem.total
            strmem['used']    = psmem.used
            strmem['free']    = psmem.free 
            strmem['percent'] = psmem.percent
            return strmem 
        except:
            raise Exception("Unable to get info from psutil")

    def cmd_system_capacity(self, *argv, **kwargs):
        try:
            retr={}
            retr['system.mem.usage']  = self.cmd_system_mem_usage(*argv, **kwargs)
            retr['system.disk.usage'] = self.cmd_system_disk_usage(*argv, **kwargs)
            retr['system.cpu.usage']  = self.cmd_system_cpu_usage(*argv, **kwargs)
            return retr
        except:
            raise Exception("Unable to get info from psutil")

    def aux_convert_bytes(self, n):
        if n == 0:
            return "0B"
        symbols = ('k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i+1)*10
        for s in reversed(symbols):
            if n >= prefix[s]:
                value = float(n) / prefix[s]
                return '%.1f%s' % (value, s)
 
    def aux_reniceme(self, nice):
        if nice and self.is_number(nice):
            try:
                retr=os.nice(int(nice))
                return(0)
            except:
                return(1)
        else:
            return(1)
            
    def cmd_command_exists(self, *argv, **kwargs):
    
        command = kwargs.get('command',None)
        if not command: raise Exceptio("Invalid params")
        
        return call(['type', command], 
            stdout=PIPE, stderr=PIPE) == 0

ECMBase().run()

