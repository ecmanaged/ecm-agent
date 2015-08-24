%define name ecmanaged-ecagent
%define version 2.2
%define unmangled_version 2.2
%define release 1

Summary: ECManaged  Agent - Monitoring and deployment agent
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: Apache v2
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Juan Carlos Moreno<juancarlos.moreno@ecmanaged.com>
Packager: Arindam Choudhury<arindam@live.com>
Provides: ecmanaged-ecagent
Requires: python2 python-devel python-twisted-core python-twisted-web python-protocols python-configobj python-twisted-words python-psutil libxml2-python python-simplejson rpm-python python-crypto python-httplib shadow-utils python-pip
Url: www.ecmanaged.com
BuildRequires: systemd

%description
ECManaged  Agent - Monitoring and deployment agent

%prep
getent group ecmanaged >/dev/null || groupadd -r ecmanaged
getent passwd ecmanaged >/dev/null || \
    useradd -r -g ecmanaged -d /opt/ecmanaged -s /sbin/nologin \
    -c "account for running ecagent" ecmanaged
%setup -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%pre
if [[ $1 == 2 ]]; then
  # Stop the service if we're upgrading
  systemctl stop ecagentd.service >/dev/null 2>&1
fi

%post
systemctl daemon-reload
systemctl enable ecagentd.service
systemctl daemon-reload
systemctl start ecagentd.service >/dev/null 2>&1

%preun
if [[ $1 -eq 0 ]]; then
  # Stop and remove service on uninstall
  systemctl stop ecagentd.service >/dev/null 2>&1
  systemctl disable ecagentd.service
  systemctl daemon-reload
fi

%postun
tr '\n' '\0' < INSTALLED_FILES | | xargs -0 rm -f --

%files -f INSTALLED_FILES
%defattr(755,ecmanaged,ecmanaged,-)
%dir /opt/ecmanaged/ecagent/
%dir /opt/ecmanaged/ecagent/ecagent
%dir /opt/ecmanaged/ecagent/monitor
%dir /opt/ecmanaged/ecagent/plugins
%dir /opt/ecmanaged/ecagent/examples
/opt/ecmanaged/ecagent/ecagent/*.py
/opt/ecmanaged/ecagent/configure.py
/opt/ecmanaged/ecagent/ecagent.bat
/opt/ecmanaged/ecagent/ecagent.sh
/opt/ecmanaged/ecagent/ecagentd.tac
/opt/ecmanaged/ecagent/examples/*.py
/opt/ecmanaged/ecagent/monitor/*
/opt/ecmanaged/ecagent/plugins/*.py

%doc LICENSE README.md
%doc /opt/ecmanaged/ecagent/LICENSE
%doc /opt/ecmanaged/ecagent/README.md

%attr(750,ecmanaged,ecmanaged) /usr/lib/systemd/system/ecagentd.service
%attr(640,ecmanaged,ecmanaged) /etc/cron.d/ecmanaged-ecagent

%dir %attr(700,ecmanaged,ecmanaged) %config /opt/ecmanaged/ecagent/config
%attr(600,ecmanaged,ecmanaged) %config /opt/ecmanaged/ecagent/config/ecagent.init.cfg
%attr(600,ecmanaged,ecmanaged) %config /opt/ecmanaged/ecagent/config/xmpp_cert.pub

%changelog
* Wed Feb 25 2015 Arindam Choudhury <arindam@live.com> - 2.1.2-109
- updated for better systemd integration