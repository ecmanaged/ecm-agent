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

import logging

from pip.index import PackageFinder
from pip.req import InstallRequirement, RequirementSet
from pkg_resources import safe_name
from setuptools.package_index import distros_for_url
from pip.download import PipSession
from pip.exceptions import DistributionNotFound, BestVersionAlreadyInstalled
from packaging.version import parse
from pip.locations import src_prefix, site_packages, user_dir

logging.basicConfig()
session = PipSession()

pkg = 'google-api-python-client'
pkg_normalized = safe_name(pkg).lower()
req = InstallRequirement.from_line(pkg, None)
reqset = RequirementSet(build_dir=site_packages, src_dir=src_prefix, download_dir=None,session=session)
pf = PackageFinder(find_links=[], index_urls=['https://pypi.python.org/simple/'], session=session)

try:
    req.populate_link(pf, True)
except BestVersionAlreadyInstalled:
    print 'Best version already installed'
except DistributionNotFound:
    print 'No matching distribution found for '+pkg

if req.check_if_exists():
    print 'already installed'
    print 'satisfied by: '+str(req.satisfied_by)
    print 'conflicts with:'+str(req.conflicts_with)

    # check if update available
    update_version = None

    for dist in distros_for_url(req.link.url):
        if safe_name(dist.project_name).lower() == pkg_normalized and dist.version:
            update_version = dist.version
        break

    if parse(update_version) > parse(req.installed_version):
        print "update available"
        reqset.add_requirement(req)
        #reqset.prepare_files(pf)
        print reqset.upgrade
        #reqset.install(install_options=[], global_options=[])
        #reqset.cleanup_files()


else:
    print 'not installed'

    reqset.add_requirement(req)
    reqset.prepare_files(pf)

    reqset.install(install_options=[], global_options=[])
    reqset.cleanup_files()

    print req.install_succeeded
    if req.check_if_exists():
        print 'installation done'
        print 'satisfied by: '+str(req.satisfied_by)
        print 'conflicts with:'+str(req.conflicts_with)