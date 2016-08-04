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

go = True

try:
    from pip.commands import ListCommand
    from pip.utils import get_installed_distributions, get_installed_version
    from pip.utils.outdated import load_selfcheck_statefile
    from pip.compat import total_seconds
    from pip.index import PyPI
    from pkg_resources import parse_version
    import datetime
except ImportError:
    go = False

# Local
from __plugin import ECMPlugin
import __helper as ecm

SELFCHECK_DATE_FMT = "%Y-%m-%dT%H:%M:%SZ"


class ECMPipExtra(ECMPlugin):
    def cmd_pip_check_version(self, *argv, **kwargs):
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
            pass

        return 'pip', installed_version, str(pypi_version)

    def cmd_pip_outdated_packages(self, *argv, **kwargs):
        local = kwargs.get('local', False)
        user = kwargs.get('user', False)
        update_available = []

        list_command = ListCommand()
        options, args = list_command.parse_args([])

        options.local = local
        options.user = user

        for dist, version, typ in list_command.find_packages_latest_versions(options):
            if version > dist.parsed_version:
                update_available.append((dist.project_name, str(dist.version), str(version), typ))
        return update_available

    def cmd_pip_installed_packages(self, *argv, **kwargs):
        # returns a dictionary {'package name': 'package version'}
        available_packages = {}
        for dist in get_installed_distributions(local_only=True):
            available_packages [dist.project_name] = str(dist.parsed_version)
        return available_packages

if go:
    ECMPipExtra().run()
else:
    pass