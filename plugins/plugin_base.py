# -*- coding:utf-8 -*-

from ecplugin import ecplugin

import sys, os, platform, psutil
import socket

class ECMBase(ecplugin):
    def cmd_agent_ping(self, *argv, **kwargs):
        return True

    def cmd_set_info(self, *argv, **kwargs):
        """ Set ECManaged facts and environment variables """
        envars = kwargs.get('envars',None)
        facts  = kwargs.get('facts',None)
        if not envars:
            raise Exception('Invalid arguments')

        envars = self._envars_decode(envars)
        facts  = self._envars_decode(facts)

        if self._write_envars_facts(envars,facts):
            return True

        raise Exception('Unable to write environment file')

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
        retr['os']=str(platform.system())
        (retr['os_distrib'],retr['os_version'])=self._dist()
        retr['machine']=str(platform.machine())
        retr['uptime']=self._boottime()
        retr['hostname']=platform.node()
        retr['public_ip'] = self._get_ip()

        return retr

    def cmd_system_cpu_usage(self, *argv, **kwargs):
        'Syntax: load'
        try:
            return psutil.cpu_percent(interval=5,percpu=True)

        except:
            raise Exception("Unable to get info from psutil")

    def cmd_system_network_usage(self, *argv, **kwargs):
        'Syntax: system.network.usage[iface=eth0]'

        iface = kwargs.get('iface','eth0')
        retr = {}

        try:
            network = psutil.network_io_counters(pernic=True)
            if network[iface]:
                if hasattr(network[iface], 'bytes_sent'): retr['bytes_sent'] = network[iface].bytes_sent
                if hasattr(network[iface], 'bytes_recv'): retr['bytes_recv'] = network[iface].bytes_recv

        except: pass

        return retr

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
                # Ignore error on specific devices (CD-ROM)
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    strpart={}
                    if hasattr(part,  'mountpoint'): strpart['mountpoint'] = part.mountpoint
                    if hasattr(part,  'device'):     strpart['device'] = part.device
                    if hasattr(usage, 'total'):      strpart['total'] = self.aux_convert_bytes(usage.total)
                    if hasattr(usage, 'used'):       strpart['used'] = self.aux_convert_bytes(usage.used)
                    if hasattr(usage, 'free'):       strpart['free'] = self.aux_convert_bytes(usage.free)
                    if hasattr(usage, 'percent'):    strpart['percent'] = usage.percent
                    retr.append(strpart)

                except:
                    pass

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
            retr['system.net.usage']  = self.cmd_system_network_usage(*argv, **kwargs)
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



    def _boottime(self):
        'Server boottime'
        if sys.platform.startswith("win32"):
            return self._boottime_windows()

        return self._boottime_linux()

    def _boottime_linux(self):
        try:
            f = open('/proc/stat', 'r')
            for line in f:
                if line.startswith('btime'):
                    f.close()
                    return float(line.strip().split()[1])
            f.close()
            return 0

        except:
            raise Exception("Cannot open file: /proc/stat")

    def _boottime_windows(self):
        try:
            from time import time
            import uptime
            return int(time() - uptime.uptime())
        except:
            return 0

    def _get_ip(self):
        'Create dummy socket to get address'
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('my.ecmanaged.com', 0))
        return s.getsockname()[0]

    def _dist(self):
        'Server boottime'
        if sys.platform.startswith("win32"):
            os_distrib = platform.release()
            os_version = platform.version()
        else:
            (os_distrib,os_version,tmp)=platform.dist()

        return (os_distrib,os_version)

ECMBase().run()
