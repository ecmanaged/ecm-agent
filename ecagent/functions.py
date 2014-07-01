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

from os import getpid

try:
    import psutil
    from gc import collect

except ImportError:
    psutil = None
    collect = None
    pass

import ecagent.twlogging as log


def mem_usage():
    retval = 0
    if psutil:
        retval = (psutil.Process(getpid()).get_memory_info()[1])/1000000.0

    return retval


def mem_clean(where='', dolog=False):
    _collect = collect()

    if dolog:
        log.info("_mem_clean: %s collected %d objects. (current mem: %s MB) " % (where, _collect, str(mem_usage())))

    else:
        log.debug("_mem_clean: %s collected %d objects. (current mem: %s MB) " % (where, _collect, str(mem_usage())))

    del _collect, where, dolog
