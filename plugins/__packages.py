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

import types

from __logger import LoggerManager
log = LoggerManager.getLogger(__name__)


def check_system_restart():
    from platform import release, machine
    from gi.repository import PackageKitGlib
    from pkg_resources import parse_version

    working_kernel = release()

    client = PackageKitGlib.Client()
    client.refresh_cache(False, None, lambda p, t, d: True, None)
    res = client.resolve(PackageKitGlib.FilterEnum.INSTALLED, ['kernel'], None, lambda p, t, d: True, None)

    if res.get_exit_code() != PackageKitGlib.ExitEnum.SUCCESS:
        return False

    package_ids = res.get_package_array()

    if len(package_ids) == 0:
        return False

    installed_kernel = None

    for pkg in package_ids:
        if pkg.get_arch() == machine():
            if installed_kernel == None:
                installed_kernel = pkg
            else:
                if parse_version(pkg.get_version()) > parse_version(installed_kernel.get_version()):
                    installed_kernel = pkg

    installed_kernel = installed_kernel.get_version() + '.' +installed_kernel.get_arch()

    return parse_version(installed_kernel) > parse_version(working_kernel)

def packagekit_install_package(packages):
    if type(packages) is types.StringType:
        packages = packages.split(' ')

    for package in packages:
        packagekit_install_single_package(package)

def packagekit_install_single_package(package):
    try:
        from gi.repository import PackageKitGlib
    except ImportError:
        log.info('error importing PackageKitGlib')
        import sys
        sys.exit(0)
    from platform import machine
    from pkg_resources import parse_version


    client = PackageKitGlib.Client()

    log.info('refreshing cache')

    client.refresh_cache(False, None, lambda p, t, d: True, None)
    log.info('cache refreshed')

    log.info('resolving: %s', package)
    res = client.resolve(PackageKitGlib.FilterEnum.NONE, [package], None, lambda p, t, d: True, None)

    result = None

    if res.get_exit_code() != PackageKitGlib.ExitEnum.SUCCESS:
        log.info('resolve failed')
        return False, 'resolve failed'

    package_ids = res.get_package_array()

    if len(package_ids) == 0:
        log.info('resolved 0 packages')
        return False, 'resolved 0 packages'

    if len(package_ids) == 1:
        result = package_ids[0]

    else:
        for pkg in package_ids:
            log.info(pkg.get_id())
            if pkg.get_arch() == machine():
                if result == None:
                    result = pkg
                else:
                    if parse_version(pkg.get_version()) > parse_version(result.get_version()):
                        result = pkg
    if result.get_info() != PackageKitGlib.InfoEnum.INSTALLED:
        res = client.install_packages(False, [result.get_id()], None, lambda p, t, d: True, None)
        log.info('%s installed', result.get_id())
        return res.get_exit_code() == PackageKitGlib.ExitEnum.SUCCESS, 'installed'
    else:
        log.info('%s already installed', result.get_id())
        return True, 'already installed'

def pip_install_single_package(package, site_wide = False, isolated=False):
    try:
        from pip.commands import InstallCommand
    except ImportError:
        log.info('error importing InstallCommand')
        import sys
        sys.exit(0)
    try:
        from pip.exceptions import BadCommand, InstallationError, UninstallationError, CommandError, PreviousBuildDirError
    except ImportError:
        log.info('error importing pip.exceptions')
        import sys
        sys.exit(0)
    try:
        from pip.status_codes import ERROR, UNKNOWN_ERROR, PREVIOUS_BUILD_DIR_ERROR
    except ImportError:
        log.info('error importing pip status codes')
        import sys
        sys.exit(0)

    if site_wide:
        cmd_name, cmd_args = 'install', [package]
    else:
        cmd_name, cmd_args = 'install', [package, '--user']

    command = InstallCommand(isolated=isolated)
    options, args = command.parse_args(cmd_args)

    try:
        status = command.run(options, args)
        if isinstance(status, int):
            return status
    except PreviousBuildDirError as exc:
        log.critical(str(exc))
        log.debug('Exception information:', exc_info=True)
        log.info('PREVIOUS_BUILD_DIR_ERROR')
        return PREVIOUS_BUILD_DIR_ERROR
    except (InstallationError, UninstallationError, BadCommand) as exc:
        log.critical(str(exc))
        log.debug('Exception information:', exc_info=True)
        log.info('InstallationError, UninstallationError, BadCommand')
        return ERROR
    except CommandError as exc:
        log.critical('ERROR: %s', exc)
        log.debug('Exception information:', exc_info=True)
        log.info('CommandError')
        return ERROR
    except KeyboardInterrupt:
        log.critical('Operation cancelled by user')
        log.debug('Exception information:', exc_info=True)
        return ERROR
    except:
        log.info('Installation failed')
        log.critical('Exception:', exc_info=True)
        return UNKNOWN_ERROR
