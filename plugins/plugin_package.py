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

import re
from base64 import b64decode

from __ecm_plugin import ECMPlugin
import __ecm_helper as ecm

class ECMPackage(ECMPlugin):
    def cmd_packages_install(self, *argv, **kwargs):
        """ Install packages received in csv or in debian packages "Depends" format
        """
        packages_b64 = kwargs.get('packages', None)

        if not packages_b64: raise Exception("Invalid argument")
        try:
            str_packages = b64decode(packages_b64)
        except:
            raise Exception("Invalid b64 received")

        packages = self._parse_package_string(str_packages)

        # Invalid package list
        if not packages: return False

        # apt-get update or yum clean on first time
        refresh_db = True
        ret = {
            'out': 0,
            'stdout': '',
            'stderr': '',
        }

        for i in range(0, 100):
            there_are_pending = False
            for pkg in packages:
                if not pkg[0]['installed']:
                    packages_pending = True
                    try:
                        package_name = pkg[i]['name']
                    except KeyError:
                        continue

                    out, stdout, stderr = ecm.install_package(package_name, refresh_db)
                    ret['stdout'] += stdout
                    ret['stderr'] += stderr
                    ret['out'] = out
                    if not out:
                        pkg[0]['installed'] = 1
                        refresh_db = False

            if not packages_pending: break

        return ret

    def _parse_package_string(self, packages):
        """ Parse packages like:
        'apache2-mpm-worker (= 2.2.16-6+squeeze7) | apache2-mpm-prefork (= 2.2.16-6+squeeze7) | apache2-mpm-ePvent (= 2.2.16-6+squeeze7) | apache2-mpm-itk (= 2.2.16-6+squeeze7), apache2.2-common (= 2.2.16-6+squeeze7)'
        and return structure
        """
        parsed = PkgRelation.parse_relations(packages)
        for pkg in parsed: pkg[0]['installed'] = 0

        return parsed


#####################################################
# 3th party - From  python-debian package project
#####################################################

class PkgRelation(object):
    """ From  python-debian package project
    Inter-package relationships

    Structured representation of the relationships of a package to another,
    i.e. of what can appear in a Deb882 field like Depends, Recommends,
    Suggests, ... (see Debian Policy 7.1).
    """

    # XXX *NOT* a real dependency parser, and that is not even a goal here, we
    # just parse as much as we need to split the various parts composing a
    # dependency, checking their correctness wrt policy is out of scope
    __dep_RE = re.compile( \
        r'^\s*(?P<name>[a-zA-Z0-9.+\-]{2,})(\s*\(\s*(?P<relop>[>=<]+)\s*(?P<version>[0-9a-zA-Z:\-+~.]+)\s*\))?(\s*\[(?P<archs>[\s!\w\-]+)\])?\s*$')
    __comma_sep_RE = re.compile(r'\s*,\s*')
    __pipe_sep_RE = re.compile(r'\s*\|\s*')
    __blank_sep_RE = re.compile(r'\s*')

    @classmethod
    def parse_relations(cls, raw):
        """Parse a package relationship string (i.e. the value of a field like
        Depends, Recommends, Build-Depends ...)
        """

        def parse_archs(raw):
            # assumption: no space beween '!' and architecture name
            archs = []
            for arch in cls.__blank_sep_RE.split(raw.strip()):
                if len(arch) and arch[0] == '!':
                    archs.append((False, arch[1:]))
                else:
                    archs.append((True, arch))
            return archs

        def parse_rel(raw):
            match = cls.__dep_RE.match(raw)
            if match:
                parts = match.groupdict()
                d = {'name': parts['name']}
                if not (parts['relop'] is None or parts['version'] is None):
                    d['version'] = (parts['relop'], parts['version'])
                else:
                    d['version'] = None
                if parts['archs'] is None:
                    d['arch'] = None
                else:
                    d['arch'] = parse_archs(parts['archs'])
                return d
            else:
                return {'name': raw, 'version': None, 'arch': None}

        tl_deps = cls.__comma_sep_RE.split(raw.strip()) # top-level deps
        cnf = map(cls.__pipe_sep_RE.split, tl_deps)
        return [[parse_rel(or_dep) for or_dep in or_deps] for or_deps in cnf]


ECMPackage().run()

