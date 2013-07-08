# -*- coding:utf-8 -*-

from ecplugin import ecplugin

from platform import platform
import time
import os, re

RCD         = '/etc/rc'
INITD       = '/etc/init.d'
RUNLEVEL    = '/sbin/runlevel'
HEARTBEAT   = '/etc/heartbeat/haresources'

SVC_TIMEOUT=120

class ECMLinux(ecplugin):
    def cmd_service_control(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""

        daemon = kwargs.get('daemon',None)
        action = kwargs.get('action',None)
        force = kwargs.get('force',0)

        if not force:
            # try to get init.d daemon
            initd = self._get_rcd(daemon)
            if not initd: raise Exception("Unable to find daemon: %s" % daemon)
            daemon = initd

        daemon=os.path.basename(daemon)
        self._renice_me(-19)
        out,stdout,stderr = self._execute_command(INITD + '/' + daemon + ' ' + action)
        self._renice_me(5)

        return  self._format_output(out, stdout, stderr)

    def cmd_service_runlevel(self, *argv, **kwargs):
        return self._get_runlevel()

    def cmd_service_initd_exists(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""

        daemon = kwargs.get('daemon',None)
        return self._get_rcd(daemon)

    def _get_runlevel(self):
        (exit,stdout,stderr) = self._execute_command(RUNLEVEL)
        if not exit:
            return str(stdout).split(' ')[1].rstrip()

        return 0

    def _get_rcd(self, daemon):
        runlevel = self._get_runlevel()
        if not runlevel: return False

        path = RCD + str(runlevel) + '.d'

        if os.path.exists(path):
            target=os.listdir(path)
            for path in (target):
                try:
                    m = re.match(r"^S\d+(.*)$", path)
                    init = m.group(1)
                    if init in daemon:
                        return str(init).rstrip()
                except:
                    pass

            # Not exists as default start on runlevel
            # its a heartbeat daemon?
            if(os.path.exists(HEARTBEAT)):
                for line in open(HEARTBEAT):
                    if daemon in line:
                        return self._get_init(daemon)

        else:
            return self._get_init(daemon)

        return False

    def _get_initd(self, daemon):
        file = INITD + '/' + daemon
        if os.path.exists(INITD) and os.path.exists(file):
            return daemon

        return False

class ECMWindows(ecplugin):
    def cmd_system_uptime(self, *argv, **kwargs):
        """Syntax: system.uptime """

        server = wmi.WMI('localhost')
        secs_up = int([uptime.SystemUpTime for uptime in server.Win32_PerfFormattedData_PerfOS_System()][0])
        return(secs_up)

    def cmd_service_control(self, *argv, **kwargs):
        """Syntax: service.control daemon action"""

        daemon = kwargs.get('daemon',None)
        action = kwargs.get('action',None)

        if not (daemon and action):
            raise Exception(self.cmd_service_control.__doc__)

        maxtime = time.time() + SVC_TIMEOUT

        scmhandle = ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)
        sserv, lserv = self._svc_getname(scmhandle,daemon)

        handle = ws.OpenService(scmhandle, sserv, ws.SERVICE_ALL_ACCESS)

        if action == 'start':
            ws.StartService(handle, None)
            stat = ws.QueryServiceStatus(handle)

            while (time.time() < maxtime):
                time.sleep(.5)
                if stat[1]==ws.SERVICE_RUNNING:
                    return(0,"Service %s is running ", lserv)
            raise Exception("Timeout starting service %s ", lserv)

        elif action == 'stop':
            ws.ControlService(handle, ws.SERVICE_CONTROL_STOP)
            stat = ws.QueryServiceStatus(handle)

            while (time.time() < maxtime):
                time.sleep(.5)
                if stat[1]==ws.SERVICE_STOPPED:
                    return(0,"Service %s is stopped ", lserv)
            raise Exception("Timeout stopping service %s ", lserv)

        elif action == 'restart':
            # stop
            ws.ControlService(handle, ws.SERVICE_CONTROL_STOP)
            stat = ws.QueryServiceStatus(handle)

            while (time.time() < maxtime):
                time.sleep(.5)
                if stat[1]==ws.SERVICE_STOPPED:
                    break
                    # start
            ws.StartService(handle, None)
            stat = ws.QueryServiceStatus(handle)

            while (time.time() < maxtime):
                time.sleep(.5)
                if stat[1]==ws.SERVICE_RUNNING:
                    return(0,"Service %s is running ", lserv)
            raise Exception("Timeout restarting service %s ", lserv)

    def cmd_system_dist(self, *argv, **kwargs):
        """"""
        return("NOT_SUPPORTED")

    def cmd_system_update(self, *argv, **kwargs):
        """Syntax: system.update[update command args]"""
        return("NOT_SUPPORTED")

    def _svc_getname(self, scmhandle, service):
        snames=ws.EnumServicesStatus(scmhandle)
        for i in snames:
            if i[0].lower() == service.lower():
                return i[0], i[1]; break
            if i[1].lower() == service.lower():
                return i[0], i[1]; break

        raise Exception("The %s service doesn't seem to exist." % service)

# Load class based on platform()
if platform().upper() == 'WINDOWS':
    win32pipe = __import__("win32pipe")
    wmi = __import__("wmi")
    ws = __import__("win32service")
    ECMWindows().run()

else:
    ECMLinux().run()
