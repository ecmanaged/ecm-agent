# -*- coding:utf-8 -*-

from smplugin import SMPlugin

import re
import base64

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
    __dep_RE = re.compile(\
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
                d = { 'name': parts['name'] }
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
                return { 'name': raw, 'version': None, 'arch': None }

        tl_deps = cls.__comma_sep_RE.split(raw.strip()) # top-level deps
        cnf = map(cls.__pipe_sep_RE.split, tl_deps)
        return [[parse_rel(or_dep) for or_dep in or_deps] for or_deps in cnf]

class ECMPackage(object):

    def cmd_packages_install(self, *argv, **kwargs):
        packages_b64 = kwargs.get('packages',None)

        if not packages_b64: raise Exception("Invalid argument")
        try: str_packages = base64.b64decode(packages_b64)
        except: raise Exception("Invalid b64 received")

        packages = self._parse_package_string(str_packages)

        for i in range(0,100):
            pending = False
            for depend in packages:
                if not depend[0]['installed']:
                    pending = True
                    try:
                        package_name = depend[i]['name']
                    except KeyError:
                        raise Exception("Unable to install all packages")

                    if not self._install_package(package_name):
                        depend[0]['installed'] = 1

            if not pending: break

        return True

    def _parse_package_string(self, packages):
        """ Parse packages like:
        'apache2-mpm-worker (= 2.2.16-6+squeeze7) | apache2-mpm-prefork (= 2.2.16-6+squeeze7) | apache2-mpm-ePvent (= 2.2.16-6+squeeze7) | apache2-mpm-itk (= 2.2.16-6+squeeze7), apache2.2-common (= 2.2.16-6+squeeze7)'
        and return structure
        """
        parsed = PkgRelation.parse_relations(packages)
        for pkg in parsed: pkg[0]['installed'] = 0

        return parsed


ECMPackage().run()

depend = 'apache2-mpm-worker (= 2.2.16-6+squeeze7) | apache2-mpm-prefork (= 2.2.16-6+squeeze7) | apache2-mpm-event (= 2.2.16-6+squeeze7) | apache2-mpm-itk (= 2.2.16-6+squeeze7), apache2.2-common (= 2.2.16-6+squeeze7)'
depend = 'joe | nano, pepe, apache2'
depend = 'debconf (>= 0.5) | debconf-2.0, python, lsb-base (>= 3.2-13), debconf, python-twisted-core, python-protocols, python-twisted-web, python-configobj, python-dmidecode, dmidecode, python-twisted-words, python-psutil, python-libxml2, python-simplejson, python-apt, collectd-core, puppet-common | puppet, git, subversion, python-httplib2'
ret = PkgRelation.parse_relations(depend)

import json
print(json.dumps(ret,indent=4))
