# -*- coding:utf-8 -*-

import os
import re

import psutil

from plugin import ECMPlugin

class ECMProc(ECMPlugin):
    def cmd_proc_mem_name(self, *argv, **kwargs):
        """Syntax: proc.mem_name ['name' = name]"""

        name = kwargs.get('name', None)
        total_rss = 0
        total_vms = 0

        if not name:
            raise Exception(self.cmd_proc_mem_name.__doc__)

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
            raise Exception(self.cmd_proc_mem_regex.__doc__)

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
            raise Exception(self.cmd_proc_num_regex.__doc__)

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
            raise Exception(self.cmd_proc_list_regex.__doc__)

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
            raise Exception(self.cmd_proc_kill_name.__doc__)

        killed = []
        proc_name_array = proc_list.split(',')

        for proc in psutil.process_iter():
            if proc.name in proc_name_array and proc.pid != os.getpid():
                proc.kill()
                killed.append(proc.pid)

        if not killed:
            return ('%s: no process found' % str(proc_list))
        else:
            return ('%s: Killed' % str(killed))

    def cmd_proc_kill_pid(self, *argv, **kwargs):
        """ Syntax: proc.kill.pid[pid],[pid],..."""

        proc_list = kwargs.get('pid', None)

        if not proc_list:
            raise Exception(self.cmd_proc_kill_pid.__doc__)

        killed = []
        proc_pid_array = proc_list.split(',')
        for proc in psutil.process_iter():
            if str(proc.pid) in proc_pid_array and proc.pid != os.getpid():
                proc.kill()
                killed.append(proc.pid)

        if not killed:
            return ('%s: no process found' % str(proc_list))
        else:
            return ('%s: Killed' % str(killed))

    def cmd_proc_kill_regex(self, *argv, **kwargs):
        """Syntax: proc.kill.regex[regex]"""

        regex = kwargs.get('regex', None)

        if not regex:
            raise Exception(self.cmd_proc_kill_regex.__doc__)

        # clean starting and ending slash
        regex = re.sub(r'(^\/)', r'', regex)
        regex = re.sub(r'(\/$)', r'', regex)

        killed = []
        for proc in psutil.process_iter():
            if re.search(regex, proc.name) and proc.pid != os.getpid():
                proc.kill()
                killed.append(proc.name)

        if not killed:
            return ('%s: no process found' % str(regex))
        else:
            return ('%s: Killed' % str(killed))

    def cmd_command_exists(self, *argv, **kwargs):
        """Syntax: command.exists[command]"""

        command = kwargs.get('command', None)

        if not command:
            raise Exception(self.cmd_command_exists.__doc__)

        cmd = 'type ' + command
        out, stdout, stderr = self._execute_command(cmd)

        return (out == 0)

    def cmd_proc_sem_clean(self, *argv, **kwargs):
        """Syntax: proc.sem.clean[user]"""

        # :TODO: This
        return False


ECMProc().run()
