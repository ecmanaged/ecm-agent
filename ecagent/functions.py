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

import ecagent.twlogging as log
import resource
import gc


def mem_usage(point=''):
    usage = resource.getrusage(resource.RUSAGE_SELF)

    return '''%s: usertime=%s systime=%s mem=%s mb''' % (point, usage[0], usage[1],
           (usage[2]*resource.getpagesize())/1000000.0)


def mem_clean(where='', dolog=False):
    if dolog:
        log.info("_mem_clean: %s collected %d objects." % (where, gc.collect()))
        log.info("_mem_clean: " + mem_usage(where))
    else:
        log.debug("_mem_clean: %s collected %d objects." % (where, gc.collect()))
        log.debug("_mem_clean: " + mem_usage(where))
