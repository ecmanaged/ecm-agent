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

import time
import sys
import os
import re
import dbus

# Local
from __plugin import ECMPlugin
import __helper as ecm

SVC_TIMEOUT = 120

SYSTEMD_BUSNAME = 'org.freedesktop.systemd1'
SYSTEMD_PATH = '/org/freedesktop/systemd1'
SYSTEMD_MANAGER_INTERFACE = 'org.freedesktop.systemd1.Manager'
SYSTEMD_UNIT_INTERFACE = 'org.freedesktop.systemd1.Unit'
DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
class ECMLinux(ECMPlugin):
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
            return False, 'systemd dbus error', 'NA'

        try:
            unit = systemd_manager.GetUnit(service)
        except dbus.DBusException:
            print 'can not find service file'
            return False, 'cannot find service file', 'NA'

        try:
            unit_object = bus.get_object(SYSTEMD_BUSNAME, unit)
            prop_unit = dbus.Interface(unit_object, DBUS_PROPERTIES)
        except dbus.DBusException:
            return False, 'unit dbus error', 'NA'

        while list(systemd_manager.ListJobs()):
            time.sleep(2)
            # 'there are pending jobs, lets wait for them to finish.'

        if action == 'start':
            try:
                job = systemd_manager.StartUnit(service, 'replace')
            except dbus.DBusException:
                return False, 'error starting', 'NA'

        if action == 'stop':
            try:
                job = systemd_manager.StopUnit(service, 'replace')
            except dbus.DBusException:
                return False, 'error stopping', 'NA'

            # Ensure that the service has been stopeed
            try: job = systemd_manager.KillUnit(service, 'replace')
            except: pass

        if action == 'restart':
            try:
                job = systemd_manager.RestartUnit(service, 'replace')
            except dbus.DBusException:
                return False, 'error restarting', 'NA'

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
            return False, 'systemd dbus error', 'NA'

        try:
            unit = systemd_manager.GetUnit(service)
        except dbus.DBusException:
            print 'can not find service file'
            return False, 'cannot find service file', 'NA'

        try:
            unit_object = bus.get_object(SYSTEMD_BUSNAME, unit)
            prop_unit = dbus.Interface(unit_object, DBUS_PROPERTIES)
        except dbus.DBusException:
            return False, 'unit dbus error', 'NA'

        try:
            active_state = prop_unit.Get(SYSTEMD_UNIT_INTERFACE, 'ActiveState')
            sub_state = prop_unit.Get(SYSTEMD_UNIT_INTERFACE, 'SubState')
        except dbus.DBusException:
            return False, 'error getting state', 'NA'

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
    ECMLinux().run()
