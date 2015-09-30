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


from __future__ import absolute_import

import types
import datetime

from pip.commands import commands_dict, ListCommand
from pip.exceptions import BadCommand, InstallationError, UninstallationError, CommandError, PreviousBuildDirError
from pip.status_codes import ERROR, UNKNOWN_ERROR, PREVIOUS_BUILD_DIR_ERROR
from pip.utils import get_installed_distributions, get_installed_version
from pip.utils.outdated import load_selfcheck_statefile
from pip.compat import total_seconds
from pip.index import PyPI

from pkg_resources import parse_version, safe_name

from __logger import LoggerManager
log = LoggerManager.getLogger(__name__)

SELFCHECK_DATE_FMT = "%Y-%m-%dT%H:%M:%SZ"


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
    from gi.repository import PackageKitGlib
    from platform import machine

    from __logger import LoggerManager
    log = LoggerManager.getLogger(__name__)

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

def canonicalize_name(name):
    """Convert an arbitrary string to a canonical name used for comparison"""
    return safe_name(name).lower()

def pip_check_version():
    list_command = ListCommand()
    options, args = list_command.parse_args([])
    session = list_command._build_session(options, retries=0, timeout=min(5, options.timeout))

    installed_version = get_installed_version("pip")

    if installed_version is None:
        return

    pypi_version = None

    try:
        state = load_selfcheck_statefile()
        current_time = datetime.datetime.utcnow()
        if "last_check" in state.state and "pypi_version" in state.state:
            last_check = datetime.datetime.strptime(
                state.state["last_check"],
                SELFCHECK_DATE_FMT
            )
            if total_seconds(current_time - last_check) < 7 * 24 * 60 * 60:
                pypi_version = state.state["pypi_version"]

        # Refresh the version if we need to or just see if we need to warn
        if pypi_version is None:
            resp = session.get(
                PyPI.pip_json_url,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            pypi_version = [
                v for v in sorted(
                    list(resp.json()["releases"]),
                    key=parse_version,
                )
                if not parse_version(v).is_prerelease
            ][-1]

            state.save(pypi_version, current_time)
    except Exception:
        log.info("There was an error checking the latest version of pip",
            exc_info=True,)

    return 'pip', installed_version, str(pypi_version)

def pip_outdated_packages(local=False, user=False):
    update_available = []

    list_command = ListCommand()
    options, args = list_command.parse_args([])

    options.local = local
    options.user = user

    for dist, version, typ in list_command.find_packages_latest_versions(options):
        if version > dist.parsed_version:
            update_available.append((dist.project_name, str(dist.version), str(version), typ))
    return update_available

def pip_installed_packages(package, site_wide = False):
    # returns a dictionary {'package name': 'package version'}
    available_packages = {}
    for dist in get_installed_distributions(local_only=True):
        available_packages [dist.project_name] = str(dist.parsed_version)
    return available_packages

def pip_install_single_package(package, site_wide = False, isolated=False):

    if site_wide:
        cmd_name, cmd_args = 'install', [package]
    else:
        cmd_name, cmd_args = 'install', [package, '--user']

    command = commands_dict[cmd_name](isolated=isolated)
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
