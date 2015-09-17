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

from plugin_log import LoggerManager
log = LoggerManager.getLogger(__name__)

from pip.index import PackageFinder
from pip.req import InstallRequirement, RequirementSet
from pkg_resources import safe_name
from setuptools.package_index import distros_for_url
from pip.download import PipSession
from pip.exceptions import DistributionNotFound, BestVersionAlreadyInstalled
from pip.exceptions import PreviousBuildDirError, InstallationError
from pip.locations import src_prefix, site_packages, user_site
from pkg_resources import parse_version


from __plugin import ECMPlugin

class ECMPip(ECMPlugin):
    def cmd_pip_install(self, *argv, **kwargs):
        '''packagke: package name
           side_wide: boolean. if True package will be installed in site packages, else in user site
        '''


        session = PipSession()

        # site_wide is a boolean. if True package will be installed in site packages, else in user site
        install_site_wide = kwargs.get('site_wide', False)
        pkg = kwargs.get('package', None)

        log.info('installing %s using pip' %pkg)

        pkg_normalized = safe_name(pkg).lower()
        req = InstallRequirement.from_line(pkg, None)
        pf = PackageFinder(find_links=[], index_urls=['https://pypi.python.org/simple/'], session=session)

        try:
            req.populate_link(pf, True)
        except BestVersionAlreadyInstalled:
            log.info('Best version already installed')
            return True, 'Best version already installed'
        except DistributionNotFound:
            log.info('No matching distribution found for: %s '%pkg)
            return True, 'No matching distribution found for '+pkg

        if req.check_if_exists():
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
                #exit()
                log.info('can not update')
                return True, 'can not update'
            if parse_version(update_version) > parse_version(req.installed_version):
                if install_site_wide:
                    reqset = RequirementSet(build_dir=site_packages, src_dir=src_prefix, download_dir=None, session=session, use_user_site=False, upgrade= True)
                else:
                    reqset = RequirementSet(build_dir=user_site, src_dir=src_prefix, download_dir=None, session=session, use_user_site=True, upgrade= True)

                reqset.add_requirement(req)
                reqset._check_skip_installed(req, pf)

                try:
                    reqset.prepare_files(pf)
                except PreviousBuildDirError as error:
                    log.info('reqset.prepare_files PreviousBuildDirError')
                    log.info(error)
                    return False, 'PreviousBuildDirError'
                except InstallationError as error:
                    log.info('reqset.prepare_files InstallationError')
                    log.info(error)
                    return False, 'InstallationError'

                if install_site_wide:
                    try:
                        reqset.install(install_options=[], global_options=[])
                    except PreviousBuildDirError as error:
                        log.info('reqset.install PreviousBuildDirError')
                        log.info(error)
                        return False, 'PreviousBuildDirError'
                    except InstallationError as error:
                        log.info('reqset.install PreviousBuildDirError')
                        log.info(error)
                        return False, 'InstallationError'
                else:
                    try:
                        reqset.install(install_options=['--user'], global_options=[])
                    except PreviousBuildDirError as error:
                        log.info('reqset.install PreviousBuildDirError')
                        log.info(error)
                        return False, 'PreviousBuildDirError'
                    except InstallationError as error:
                        log.info('reqset.install PreviousBuildDirError')
                        log.info(error)
                        return False, 'InstallationError'

                reqset.cleanup_files()
            else:
                return True, 'installed version is up-to-date'
            return True, 'update available'

        else:
            log.info('installing: %s' %pkg)
            if install_site_wide:
                reqset = RequirementSet(build_dir=site_packages, src_dir=src_prefix, download_dir=None, session=session, use_user_site=False)
            else:
                reqset = RequirementSet(build_dir=user_site, src_dir=src_prefix, download_dir=None, session=session, use_user_site=True)

            reqset.add_requirement(req)

            try:
                reqset.prepare_files(pf)
            except PreviousBuildDirError as error:
                log.info('reqset.prepare_files PreviousBuildDirError')
                log.info(error)
                return False, 'PreviousBuildDirError'
            except InstallationError as error:
                log.info('reqset.prepare_files InstallationError')
                log.info(error)
                return False, 'InstallationError'

            if install_site_wide:
                try:
                    reqset.install(install_options=[], global_options=[])
                except PreviousBuildDirError as error:
                    log.info('reqset.install PreviousBuildDirError')
                    log.info(error)
                    return False, 'PreviousBuildDirError'
                except InstallationError as error:
                    log.info('reqset.install PreviousBuildDirError')
                    log.info(error)
                    return False, 'InstallationError'
            else:
                try:
                    reqset.install(install_options=['--user'], global_options=[])
                except PreviousBuildDirError as error:
                    log.info('reqset.install PreviousBuildDirError')
                    log.info(error)
                    return False, 'PreviousBuildDirError'
                except InstallationError as error:
                    log.info('reqset.install PreviousBuildDirError')
                    log.info(error)
                    return False, 'InstallationError'

            reqset.cleanup_files()

            log.info('checking installation status')

            if req.install_succeeded:
                req.check_if_exists()
                log.info('installed %s', req.satisfied_by)
                return True, req.satisfied_by
            else:
                log.info('installation of %s failed', pkg)
                return False, 'installation failed'

ECMPip().run()