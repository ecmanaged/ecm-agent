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
from pip._vendor.packaging.version import parse
from pip.locations import src_prefix, site_packages, user_site

logging.basicConfig()

# Local
import __helper as ecm
from __plugin import ECMPlugin
from __mplugin import MPlugin


class ECMPip(ECMPlugin):
    def cmd_pip_install(self, *argv, **kwargs):
        session = PipSession()

        # site_wide is a boolean. if True package will be installed in site packages, else in user site
        install_site_wide = kwargs.get('site_wide', None)

        pkg = kwargs.get('package', None)

        pkg_normalized = safe_name(pkg).lower()
        req = InstallRequirement.from_line(pkg, None)
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

            if req.link.is_wheel:
                from pip.wheel import Wheel
                update_version = Wheel(req.link.filename).version
            else:
                for dist in distros_for_url(req.link.url):
                    if safe_name(dist.project_name).lower() == pkg_normalized and dist.version:
                        update_version = dist.version
                    break
            if not update_version:
                print 'Could not obtain the updated version number'
                exit()
            if parse(update_version) > parse(req.installed_version):
                print "update available"
                if install_site_wide:
                    reqset = RequirementSet(build_dir=site_packages, src_dir=src_prefix, download_dir=None, session=session, use_user_site=False, upgrade= True)
                else:
                    reqset = RequirementSet(build_dir=user_site, src_dir=src_prefix, download_dir=None, session=session, use_user_site=True, upgrade= True)
                reqset.add_requirement(req)
                print reqset.build_dir
                print reqset.src_dir
                reqset._check_skip_installed(req, pf)
                reqset.prepare_files(pf)
                if install_site_wide:
                    reqset.install(install_options=[], global_options=[])
                else:
                    reqset.install(install_options=['--user'], global_options=[])
                reqset.cleanup_files()
                print 'updated'
            else:
                print 'installed version is up-to-date'

        else:
            print 'not installed'

            if install_site_wide:
                reqset = RequirementSet(build_dir=site_packages, src_dir=src_prefix, download_dir=None, session=session, use_user_site=False)
            else:
                reqset = RequirementSet(build_dir=user_site, src_dir=src_prefix, download_dir=None, session=session, use_user_site=True)

            reqset.add_requirement(req)
            print reqset.build_dir
            print reqset.src_dir

            reqset.prepare_files(pf)

            if install_site_wide:
                reqset.install(install_options=[], global_options=[])
            else:
                reqset.install(install_options=['--user'], global_options=[])
            reqset.cleanup_files()

            if req.install_succeeded:
                req.check_if_exists()
                print 'installation done'
                print 'satisfied by: '+str(req.satisfied_by)
                print 'conflicts with:'+str(req.conflicts_with)

ECMPip().run()