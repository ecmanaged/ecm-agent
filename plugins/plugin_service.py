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

import os
import re
import time
import dbus

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
        Syntax: service.control name.service ['start','stop','restart','status']
        """
        service = kwargs.get('service', None)
        action = kwargs.get('action', None)

        if not service or not action:
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)

        if not service.split('.')[-1] == 'service':
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)

        if action not in ['start', 'stop', 'restart']:
            raise ecm.InvalidParameters('unsupported action')

        # proxy = bus.get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')
        # authority = dbus.Interface(proxy, dbus_interface='org.freedesktop.PolicyKit1.Authority')
        # system_bus_name = bus.get_unique_name()
        #
        # subject = ('system-bus-name', {'name' : system_bus_name})
        # action_id = 'org.freedesktop.systemd1.manage-units'
        # details = {}
        # flags = 1            # AllowUserInteraction flag
        # cancellation_id = '' # No cancellation id
        #
        # result = authority.CheckAuthorization(subject, action_id, details, flags, cancellation_id)
        #
        #
        # if result[1] != 0:
        #     return False, 'Need administrative privilege', 'NA'

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

            # Ensure that the service has been stopeed
            try: job = systemd_manager.KillUnit(service, 'replace')
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
    def cmd_service_control(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""

        daemon = kwargs.get('daemon', None)
        action = kwargs.get('action', None)
        force = kwargs.get('force', 0)

        if not (daemon and action):
            raise ecm.InvalidParameters(self.cmd_service_control.__doc__)

        if not force:
            # try to get init.d daemon
            initd = self._get_rcd(daemon)
            if not initd:
                raise Exception("Unable to find daemon: %s" % daemon)
            daemon = initd

        daemon = os.path.basename(daemon)
        ecm.renice_me(-19)
        out, stdout, stderr = ecm.run_command(INITD + '/' + daemon + ' ' + action)
        ecm.renice_me(5)

        return ecm.format_output(out, stdout, stderr)

    def cmd_service_runlevel(self, *argv, **kwargs):
        return self._get_runlevel()

    def cmd_service_state(self, *argv, **kwargs):
        """Syntax: service.exists daemon"""

        name = kwargs.get('name', None)

        if not name:
            raise ecm.InvalidParameters(self.cmd_service_state.__doc__)

        daemon = os.path.basename(name)
        out, stdout, stderr = ecm.run_command(INITD + '/' + daemon + ' status')

        return not bool(out)

    def cmd_service_exists(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""

        daemon = kwargs.get('daemon', None)
        return bool(self._get_rcd(daemon))

    def _get_runlevel(self):
        (out, stdout, stderr) = ecm.run_command(RUNLEVEL)
        if not out:
            return str(stdout).split(' ')[1].rstrip()

        return 0

    def _get_rcd(self, daemon):
        runlevel = self._get_runlevel()
        if not runlevel: return False

        path = RCD + str(runlevel) + '.d'

        if os.path.exists(path):
            target = os.listdir(path)
            for path in target:
                try:
                    m = re.match(r"^S\d+(.*)$", path)
                    init = m.group(1)
                    if init in daemon:
                        return str(init).rstrip()
                except:
                    pass

            # Not exists as default start on runlevel
            # its a heartbeat daemon?
            if os.path.exists(HEARTBEAT):
                for line in open(HEARTBEAT):
                    if daemon in line:
                        return self._get_init(daemon)

        else:
            return self._get_init(daemon)

        return False

    def _get_init(self, daemon):
        filename = INITD + '/' + daemon
        if os.path.exists(INITD) and os.path.exists(filename):
            return daemon

        return False


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
            # stop
            ws.ControlService(handle, ws.SERVICE_CONTROL_STOP)

            while time.time() < maxtime:
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_STOPPED:
                    break

            # start
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
    try:
        # Try systemd
        bus = dbus.SystemBus()
        systemd_object = bus.get_object(SYSTEMD_BUSNAME, SYSTEMD_PATH)
        systemd_manager = dbus.Interface(systemd_object, SYSTEMD_MANAGER_INTERFACE)

        ECMLinuxSystemD().run()

    except:
        # Do our best with init.d
        ECMLinuxInitD().run()
