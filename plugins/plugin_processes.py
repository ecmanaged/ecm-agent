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
import re
import psutil

# Local
from __plugin import ECMPlugin
import __helper as ecm

class ECMProc(ECMPlugin):
    def cmd_proc_mem_name(self, *argv, **kwargs):
        """Syntax: proc.mem_name ['name' = name]"""

        name = kwargs.get('name', None)
        total_rss = 0
        total_vms = 0

        if not name:
            raise ecm.InvalidParameters(self.cmd_proc_mem_name.__doc__)

        try:
            for process in psutil.process_iter():
                if process.name == name:
                    p = psutil.Process(process.pid)
                    mem = p.get_memory_info()
                    total_rss += mem.rss
                    total_vms += mem.vms

            return [total_rss, total_vms]

        except:
            return 0


    def cmd_proc_mem_regex(self, *argv, **kwargs):
        """Syntax: proc.mem.regex <regex>"""

        regex = kwargs.get('regex', None)

        if not regex:
            raise ecm.InvalidParameters(self.cmd_proc_mem_regex.__doc__)

        # clean starting and ending slash
        regex = re.sub(r'(^\/)', r'', regex)
        regex = re.sub(r'(\/$)', r'', regex)

        total_rss = 0
        total_vms = 0

        for proc in psutil.process_iter():
            if re.search(regex, proc.name):
                p = psutil.Process(proc.pid)
                mem = p.get_memory_info()
                total_rss += mem.rss
                total_vms += mem.vms

        return [total_rss, total_vms]

    def cmd_proc_num_name(self, *argv, **kwargs):
        """Syntax: proc.num [name]"""

        proc_name = kwargs.get('name', None)

        if proc_name:
            try:
                return int(len(filter(lambda x: x.name == proc_name, psutil.process_iter())))
            except:
                return 0
        else:
            return len(psutil.get_pid_list())

    def cmd_proc_num_regex(self, *argv, **kwargs):
        """Syntax: proc.num.regex <regex>"""

        regex = kwargs.get('regex', None)

        if not regex:
            raise ecm.InvalidParameters(self.cmd_proc_num_regex.__doc__)

        # clean starting and ending slash
        regex = re.sub(r'(^\/)', r'', regex)
        regex = re.sub(r'(\/$)', r'', regex)

        num = 0
        for proc in psutil.process_iter():
            if re.search(regex, proc.name):
                num += 1

        return int(num)

    def cmd_proc_list_regex(self, *argv, **kwargs):
        """ Syntax: proc.num.regex <regex>"""

        regex = kwargs.get('regex', None)

        if not regex:
            raise ecm.InvalidParameters(self.cmd_proc_list_regex.__doc__)

        # clean starting and ending slash
        regex = re.sub(r'(^\/)', r'', regex)
        regex = re.sub(r'(\/$)', r'', regex)

        processes = []
        for proc in psutil.process_iter():
            if re.search(regex, proc.name):
                processes.append(proc.pid)

        if not processes:
            return 0
        else:
            return int(processes)

    def cmd_proc_kill_name(self, *argv, **kwargs):
        """Syntax: proc.kill.name[name],[name],..."""

        proc_list = kwargs.get('name', None)

        if not proc_list:
            raise ecm.InvalidParameters(self.cmd_proc_kill_name.__doc__)

        killed = []
        proc_name_array = proc_list.split(',')

        for proc in psutil.process_iter():
            if proc.name in proc_name_array and proc.pid != os.getpid():
                proc.kill()
                killed.append(proc.pid)

        if not killed:
            return '%s: no process found' % str(proc_list)
        else:
            return '%s: Killed' % str(killed)

    def cmd_proc_kill_pid(self, *argv, **kwargs):
        """ Syntax: proc.kill.pid[pid],[pid],..."""

        proc_list = kwargs.get('pid', None)

        if not proc_list:
            raise ecm.InvalidParameters(self.cmd_proc_kill_pid.__doc__)

        killed = []
        proc_pid_array = proc_list.split(',')
        for proc in psutil.process_iter():
            if str(proc.pid) in proc_pid_array and proc.pid != os.getpid():
                proc.kill()
                killed.append(proc.pid)

        if not killed:
            return '%s: no process found' % str(proc_list)
        else:
            return '%s: Killed' % str(killed)

    def cmd_proc_kill_regex(self, *argv, **kwargs):
        """Syntax: proc.kill.regex[regex]"""

        regex = kwargs.get('regex', None)

        if not regex:
            raise ecm.InvalidParameters(self.cmd_proc_kill_regex.__doc__)

        # clean starting and ending slash
        regex = re.sub(r'(^\/)', r'', regex)
        regex = re.sub(r'(\/$)', r'', regex)

        killed = []
        for process in psutil.process_iter():
            if re.search(regex, process.name) and process.pid != os.getpid():
                process.kill()
                killed.append(process.name)

        if not killed:
            return '%s: no process found' % str(regex)
        else:
            return '%s: Killed' % str(killed)

    def cmd_command_exists(self, *argv, **kwargs):
        """Syntax: command.exists[command]"""

        command = kwargs.get('command', None)

        if not command:
            raise ecm.InvalidParameters(self.cmd_command_exists.__doc__)

        return bool(ecm.which(command))

    def cmd_proc_sem_clean(self, *argv, **kwargs):
        """Syntax: proc.sem.clean[user]"""

        # :TODO: This
        return False


ECMProc().run()
