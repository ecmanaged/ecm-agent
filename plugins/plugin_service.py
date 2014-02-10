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

from __ecm_plugin import ECMPlugin
import __ecm_helper as ecm

RCD = '/etc/rc'
INITD = '/etc/init.d'
RUNLEVEL = '/sbin/runlevel'
HEARTBEAT = '/etc/heartbeat/haresources'

SVC_TIMEOUT = 120

class ECMLinux(ECMPlugin):
    def cmd_service_control(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""

        daemon = kwargs.get('daemon', None)
        action = kwargs.get('action', None)
        force = kwargs.get('force', 0)

        if not (daemon and action):
            raise Exception(self.cmd_service_control.__doc__)

        if not force:
            # try to get init.d daemon
            initd = self._get_rcd(daemon)
            if not initd: raise Exception("Unable to find daemon: %s" % daemon)
            daemon = initd

        daemon = os.path.basename(daemon)
        ecm.renice_me(-19)
        out, stdout, stderr = ecm.execute_command(INITD + '/' + daemon + ' ' + action)
        ecm.renice_me(5)

        return ecm.format_output(out, stdout, stderr)

    def cmd_service_runlevel(self, *argv, **kwargs):
        return self._get_runlevel()

    def cmd_service_state(self, *argv, **kwargs):
        """Syntax: service.exists daemon"""

        name = kwargs.get('name', None)

        if not name:
            raise Exception(self.cmd_service_state.__doc__)

        daemon = os.path.basename(name)
        out, stdout, stderr = ecm.execute_command(INITD + '/' + name + ' status')

        return not bool(out)

    def cmd_service_exists(self, *argv, **kwargs):
        """Syntax: service.control daemon action <force: 0/1>"""

        daemon = kwargs.get('daemon', None)
        return bool(self._get_rcd(daemon))

    def _get_runlevel(self):
        (exit, stdout, stderr) = ecm.execute_command(RUNLEVEL)
        if not exit:
            return str(stdout).split(' ')[1].rstrip()

        return 0

    def _get_rcd(self, daemon):
        runlevel = self._get_runlevel()
        if not runlevel: return False

        path = RCD + str(runlevel) + '.d'

        if os.path.exists(path):
            target = os.listdir(path)
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
            if (os.path.exists(HEARTBEAT)):
                for line in open(HEARTBEAT):
                    if daemon in line:
                        return self._get_init(daemon)

        else:
            return self._get_init(daemon)

        return False

    def _get_init(self, daemon):
        file = INITD + '/' + daemon
        if os.path.exists(INITD) and os.path.exists(file):
            return daemon

        return False


class ECMWindows(ECMPlugin):
    def cmd_service_control(self, *argv, **kwargs):
        """Syntax: service.control daemon action"""

        daemon = kwargs.get('daemon', None)
        action = kwargs.get('action', None)
        force = kwargs.get('force', 0)

        if not (daemon and action):
            raise Exception(self.cmd_service_control.__doc__)

        maxtime = time.time() + SVC_TIMEOUT

        scmhandle = ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)
        sserv, lserv = self._svc_getname(scmhandle, daemon)

        handle = ws.OpenService(scmhandle, sserv, ws.SERVICE_ALL_ACCESS)

        if action == 'start':
            ws.StartService(handle, None)

            while (time.time() < maxtime):
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_RUNNING:
                    return (0, "Service %s is running " % lserv)
            raise Exception("Timeout starting service %s " % lserv)

        elif action == 'stop':
            ws.ControlService(handle, ws.SERVICE_CONTROL_STOP)

            while (time.time() < maxtime):
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_STOPPED:
                    return (0, "Service %s is stopped " % lserv)
            raise Exception("Timeout stopping service %s " % lserv)

        elif action == 'restart':
            # stop
            ws.ControlService(handle, ws.SERVICE_CONTROL_STOP)

            while (time.time() < maxtime):
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_STOPPED:
                    break

            # start
            ws.StartService(handle, None)

            while (time.time() < maxtime):
                stat = ws.QueryServiceStatus(handle)
                time.sleep(.5)
                if stat[1] == ws.SERVICE_RUNNING:
                    return (0, "Service %s is running " % lserv)
            raise Exception("Timeout restarting service %s " % lserv)

    def cmd_service_runlevel(self, *argv, **kwargs):
        return 0

    def cmd_service_state(self, *argv, **kwargs):
        """Syntax: service.exists daemon"""

        name = kwargs.get('name', None)

        if not name:
            raise Exception(self.cmd_service_state.__doc__)

        scmhandle = ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)
        sserv, lserv = self._svc_getname(scmhandle, name)

        handle = ws.OpenService(scmhandle, sserv, ws.SERVICE_ALL_ACCESS)
        stat = ws.QueryServiceStatus(handle)

        return stat[1]

    def cmd_service_exists(self, *argv, **kwargs):
        """Syntax: service.exists daemon"""

        daemon = kwargs.get('daemon', None)
        scmhandle = ws.OpenSCManager(None, None, ws.SC_MANAGER_ALL_ACCESS)
        sserv, lserv = self._svc_getname(scmhandle, daemon)

        return bool(lserv)

    def cmd_collectd_get(self, *argv, **kwargs):
        try:
            sf = StatFetcher(None, None, None)
            return self._collectd(sf)

        except Exception, e:
            raise Exception("error with wmi connection")

    def _collectd(self, sf):
        collector_map = {}
        collector_map['cpu_util'] = sf.get_cpu_util()
        collector_map['cpu_util_maxcore'] = sf.get_cpu_util_maxcore()
        collector_map['cpu_queue_length'] = sf.get_cpu_queue_length()
        collector_map['cpu_context_switches'] = sf.get_cpu_context_switches()
        collector_map['net_bits_total'] = sf.get_net_bits_total()
        collector_map['net_bits_in'] = sf.get_net_bits_in()
        collector_map['net_bits_out'] = sf.get_net_bits_out()
        collector_map['mem_available_bytes'] = sf.get_mem_available_bytes()
        collector_map['mem_cache_bytes'] = sf.get_mem_cache_bytes()
        collector_map['mem_committed_bytes'] = sf.get_mem_committed_bytes()
        collector_map['mem_pages'] = sf.get_mem_pages()
        collector_map['mem_page_faults'] = sf.get_mem_page_faults()
        collector_map['disk_queue_length_avg'] = sf.get_disk_queue_length_avg()
        collector_map['disk_queue_length_current'] = sf.get_disk_queue_length_current()
        collector_map['disk_bytes_transferred'] = sf.get_disk_bytes_transferred()

        return collector_map

    def _svc_getname(self, scmhandle, service):
        snames = ws.EnumServicesStatus(scmhandle)
        for i in snames:
            if i[0].lower() == service.lower():
                return i[0], i[1]

            if i[1].lower() == service.lower():
                return i[0], i[1]

        raise Exception("The %s service doesn't seem to exist." % service)


class StatFetcher(object):
    def __init__(self, computer, user, password):
        wmi = __import__("wmi")
        self.c = wmi.WMI(find_classes=False, computer=computer, user=user, password=password)

    def get_cpu_util(self):
        cpu_utils = [cpu.LoadPercentage for cpu in self.c.Win32_Processor()]
        for i, item in enumerate(cpu_utils):
            if item is None:  # replace None's with zero
                cpu_utils[i] = 0
        cpu_util = int(sum(cpu_utils) / len(cpu_utils))  # avg all cores/processors
        return cpu_util

    def get_cpu_util_maxcore(self):
        cpu_max = max([int(cpu.LoadPercentage) for cpu in self.c.Win32_Processor()])  # max of all cores/processors
        return cpu_max

    def get_cpu_queue_length(self):
        cpu_queue_length = sum([int(cpu.ProcessorQueueLength) for cpu in self.c.Win32_PerfRawData_PerfOS_System()])
        return cpu_queue_length

    def get_cpu_context_switches(self):
        cpu_context_switches = sum([int(cpu.ContextSwitchesPerSec) for cpu in self.c.Win32_PerfRawData_PerfOS_System()])
        return cpu_context_switches

    def get_net_bits_total(self):
        total_bytes = sum([int(net_interface.BytesTotalPerSec) for net_interface in
                           self.c.Win32_PerfRawData_Tcpip_NetworkInterface()])
        total_bits = total_bytes * 8
        return total_bits

    def get_net_bits_in(self):
        recv_bytes = sum([int(net_interface.BytesReceivedPerSec) for net_interface in
                          self.c.Win32_PerfRawData_Tcpip_NetworkInterface()])
        recv_bits = recv_bytes * 8
        return recv_bits

    def get_net_bits_out(self):
        sent_bytes = sum(
            [int(net_interface.BytesSentPerSec) for net_interface in self.c.Win32_PerfRawData_Tcpip_NetworkInterface()])
        sent_bits = sent_bytes * 8
        return sent_bits

    def get_mem_available_bytes(self):
        mem_available_bytes = sum([int(mem.AvailableBytes) for mem in self.c.Win32_PerfRawData_PerfOS_Memory()])
        return mem_available_bytes

    def get_mem_cache_bytes(self):
        mem_cache_bytes = sum([int(mem.CacheBytes) for mem in self.c.Win32_PerfRawData_PerfOS_Memory()])
        return mem_cache_bytes

    def get_mem_committed_bytes(self):
        mem_committed_bytes = sum([int(mem.CommittedBytes) for mem in self.c.Win32_PerfRawData_PerfOS_Memory()])
        return mem_committed_bytes

    def get_mem_pages(self):
        mem_pages = sum([int(mem.PagesPerSec) for mem in self.c.Win32_PerfRawData_PerfOS_Memory()])
        return mem_pages

    def get_mem_page_faults(self):
        mem_page_faults = sum([int(mem.PageFaultsPerSec) for mem in self.c.Win32_PerfRawData_PerfOS_Memory()])
        return mem_page_faults

    def get_disk_queue_length_avg(self):
        disk_queue_length_avg = sum(
            [int(disk.AvgDiskQueueLength) for disk in self.c.Win32_PerfRawData_PerfDisk_PhysicalDisk()])
        return disk_queue_length_avg

    def get_disk_queue_length_current(self):
        disk_queue_length_current = sum(
            [int(disk.CurrentDiskQueueLength) for disk in self.c.Win32_PerfRawData_PerfDisk_PhysicalDisk()])
        return disk_queue_length_current

    def get_disk_bytes_transferred(self):
        disk_bytes_transferred = sum(
            [int(disk.DiskBytesPerSec) for disk in self.c.Win32_PerfRawData_PerfDisk_PhysicalDisk()])
        return disk_bytes_transferred

# Load class based on platform()
if sys.platform.startswith("win32"):
    ws = __import__("win32service")
    ECMWindows().run()

else:
    ECMLinux().run()
