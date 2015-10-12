# -*- coding:utf-8 -*-

# Copyright (C) 2012 Juan Carlos Moreno <juancarlos.moreno at ecmanaged.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

RUN_AS_ROOT = True

import os
from commands import getstatusoutput
import time

DBUS = False

try:
    import dbus
    bus = dbus.SystemBus()
    systemd_object = bus.get_object(SYSTEMD_BUSNAME, SYSTEMD_PATH)
    systemd_manager = dbus.Interface(systemd_object, SYSTEMD_MANAGER_INTERFACE)
    DBUS = True

except:
    pass
    
# Local
from __plugin import ECMPlugin
import __helper as ecm

SVC_TIMEOUT = 120

# contants for init.d
RCD = '/etc/rc'
INITD = '/etc/init.d'
RUNLEVEL = '/sbin/runlevel'
HEARTBEAT = '/etc/heartbeat/haresources'

# contants for systemd
SYSTEMD_BUSNAME = 'org.freedesktop.systemd1'
SYSTEMD_PATH = '/org/freedesktop/systemd1'
SYSTEMD_MANAGER_INTERFACE = 'org.freedesktop.systemd1.Manager'
SYSTEMD_UNIT_INTERFACE = 'org.freedesktop.systemd1.Unit'
DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
class ECMLinuxSystemD(ECMPlugin):
    def cmd_service_control(self, *argv, **kwargs):
        """
        Syntax: service.control service ['start','stop','restart','status']
        """
        print str(kwargs)
        service = kwargs.get('service', None)
        action = kwargs.get('action', None)

        if not service or not action:
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)

        if action not in ['start', 'stop', 'restart']:
            raise ecm.InvalidParameters('unsupported action')

        try:
            bus = dbus.SystemBus()
            systemd_object = bus.get_object(SYSTEMD_BUSNAME, SYSTEMD_PATH)
            systemd_manager = dbus.Interface(systemd_object, SYSTEMD_MANAGER_INTERFACE)
        except dbus.DBusException:
            raise Exception("systemd dbus error")

        try:
            unit = systemd_manager.GetUnit(service)
        except dbus.DBusException:
            raise Exception("cannot find service file")

        try:
            unit_object = bus.get_object(SYSTEMD_BUSNAME, unit)
            prop_unit = dbus.Interface(unit_object, DBUS_PROPERTIES)
        except dbus.DBusException:
            raise Exception("unit dbus error")

        while list(systemd_manager.ListJobs()):
            time.sleep(2)
            # 'there are pending jobs, lets wait for them to finish.'

        if action == 'start':
            try:
                job = systemd_manager.StartUnit(service, 'replace')
            except dbus.DBusException:
                raise Exception("error starting")

        if action == 'stop':
            try:
                job = systemd_manager.StopUnit(service, 'replace')
            except dbus.DBusException:
                raise Exception("error stopping")

            # Ensure that the service has been stopped
            try: job = systemd_manager.KillUnit(service, 'main', 15)
            except: pass

        if action == 'restart':
            try:
                job = systemd_manager.RestartUnit(service, 'replace')
            except dbus.DBusException:
                raise Exception("error restarting")

        # wait for the job to finish
        while list(systemd_manager.ListJobs()):
            time.sleep(2)

        return True

    def cmd_service_state(self, *argv, **kwargs):
        """Syntax: service.state service"""

        service = kwargs.get('service', None)

        if not service:
            raise ecm.InvalidParameters(self.cmd_service_state.__doc__)

        try:
            bus = dbus.SystemBus()
            systemd_object = bus.get_object(SYSTEMD_BUSNAME, SYSTEMD_PATH)
            systemd_manager = dbus.Interface(systemd_object, SYSTEMD_MANAGER_INTERFACE)
        except dbus.DBusException:
            raise Exception("systemd dbus error")

        try:
            unit = systemd_manager.GetUnit(service)
        except dbus.DBusException:
            raise Exception("cannot find service file")

        try:
            unit_object = bus.get_object(SYSTEMD_BUSNAME, unit)
            prop_unit = dbus.Interface(unit_object, DBUS_PROPERTIES)
        except dbus.DBusException:
            raise Exception("unit dbus error")

        try:
            active_state = prop_unit.Get(SYSTEMD_UNIT_INTERFACE, 'ActiveState')
            sub_state = prop_unit.Get(SYSTEMD_UNIT_INTERFACE, 'SubState')
        except dbus.DBusException:
            raise Exception("error getting state")

        return active_state

    def cmd_service_exists(self, *argv, **kwargs):
        """Syntax: service.exists service"""

        service = kwargs.get('service', None)

        if not service:
            raise ecm.InvalidParameters(self.cmd_service_state.__doc__)

        try:
            self.cmd_service_state(service)
            return True

        except Exception:
            return False


class ECMLinuxInitD(ECMPlugin):
    def run(self):
        a = self.cmd_service_state(service='nginx')
        print str(a)
        a = self.cmd_service_exists(service='nginx')
        print str(a)
        a = self.cmd_service_control(service='nginx', action='stop')
        print str(a)
        
        a = self.cmd_service_control(service='nginx', action='start')
        print str(a)
        a = self.cmd_service_control(service='nginx', action='restart')
        print str(a)
       
        
    def cmd_service_control(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""
        service = kwargs.get('service', None)
        action = kwargs.get('action', None)

        if not service or not action:
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)

        if action not in ['start', 'stop', 'restart']:
            raise ecm.InvalidParameters('unsupported action')

        status, result = getstatusoutput('service ' + service + ' '+action)

        return status == 0, result

    def cmd_service_state(self, *argv, **kwargs):
        """Syntax: service.exists daemon"""

        service = kwargs.get('service', None)
        if not service:
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)
                    
        status, result = getstatusoutput('service ' + service + ' status')

        return status == 0, result


    def cmd_service_exists(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""

        service = kwargs.get('service', None)
        if not service:
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)
            
        status, result = getstatusoutput('service ' + service + ' status')

        return result


class ECMWindows(ECMPlugin):
    def cmd_service_control(self, *argv, **kwargs):
        """
        Syntax: service.control name.service ['start','stop','restart','status']
        """

        service = kwargs.get('service', None)
        action = kwargs.get('action', None)

        if not (service and action):
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)

        maxtime = time.time() + SVC_TIMEOUT

        scmhandle = ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)
        sserv, lserv = self._svc_getname(scmhandle, service)

        handle = ws.OpenService(scmhandle, sserv, ws.SERVICE_ALL_ACCESS)

        if action == 'start':
            ws.StartService(handle, None)

            while time.time() < maxtime:
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_RUNNING:
                    return 0, "Service %s is running " % lserv
            raise Exception("Timeout starting service %s " % lserv)

        elif action == 'stop':
            ws.ControlService(handle, ws.SERVICE_CONTROL_STOP)

            while time.time() < maxtime:
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_STOPPED:
                    return 0, "Service %s is stopped " % lserv
            raise Exception("Timeout stopping service %s " % lserv)

        elif action == 'restart':
            ws.ControlService(handle, ws.SERVICE_CONTROL_STOP)

            while time.time() < maxtime:
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_STOPPED:
                    break

            ws.StartService(handle, None)

            while time.time() < maxtime:
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_RUNNING:
                    return 0, "Service %s is running " % lserv
            raise Exception("Timeout restarting service %s " % lserv)

    def cmd_service_state(self, *argv, **kwargs):
        """Syntax: service.exists service"""

        service = kwargs.get('service', None)

        if not service:
            raise ecm.InvalidParameters(self.cmd_service_state.__doc__)

        scmhandle = ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)
        sserv, lserv = self._svc_getname(scmhandle, service)

        handle = ws.OpenService(scmhandle, sserv, ws.SERVICE_ALL_ACCESS)
        stat = ws.QueryServiceStatus(handle)

        return stat[1]

    def cmd_service_exists(self, *argv, **kwargs):
        """Syntax: service.exists service"""

        service = kwargs.get('service', None)

        if not service:
            raise ecm.InvalidParameters(self.cmd_service_exists.__doc__)

        scmhandle = ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)
        sserv, lserv = self._svc_getname(scmhandle, service)

        return bool(lserv)

    def _svc_getname(self, scmhandle, service):
        snames = ws.EnumServicesStatus(scmhandle)
        for i in snames:
            if i[0].lower() == service.lower():
                return i[0], i[1]

            if i[1].lower() == service.lower():
                return i[0], i[1]

        raise Exception("The %s service doesn't seem to exist." % service)


# Load class based on platform()
if ecm.is_win():
    ws = __import__("win32service")
    ECMWindows().run()

else:
    if(DBUS):
        ECMLinuxSystemD().run()
    else:
        # Do our best with init.d
        ECMLinuxInitD().run()
