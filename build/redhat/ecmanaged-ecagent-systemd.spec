#===============================================================================
# Copyright 2014 ACKSTORM S.L.
# Name: ecmanaged-ecagent-systemd.spec 
#-------------------------------------------------------------------------------
# $Id: ecmanaged-ecagent-systemd.spec,v 0.9 2014/02/20 11:10:00 $
#-------------------------------------------------------------------------------
# Purpose: RPM Spec file for ecagent on systemd systems
#===============================================================================

# No debuginfo:
%define debug_package %{nil}

%define name      ecmanaged-ecagent
%define ename     ecagentd
%define pname     ecmanaged
%define version   2.2

Name:             %{name}
Version:          %{version}       
Release:          1.systemd
Summary:          ECManaged  Agent - Monitoring and deployment agent (systemd)
Group:            Applications/System
License:          Apache v2
URL:              www.ecmanaged.com
Source0:          %{name}-%{version}.tar.gz
BuildArch:        noarch

Requires:         python2
Requires:         python-twisted-core
Requires:         python-twisted-web
Requires:         python-protocols
Requires:         python-configobj
Requires:         python-twisted-words
Requires:         python-psutil
Requires:         libxml2-python
Requires:         python-simplejson
Requires:         rpm-python
Requires:         python-crypto
Requires:         python-httplib2

Requires(pre):    shadow-utils

Requires:         systemd

Provides:         ecmanaged-ecagent

%description
ECManaged  Agent - Monitoring and deployment agent

%prep
getent group ecmanaged >/dev/null || groupadd -r ecmanaged
getent passwd ecmanaged >/dev/null || \
    useradd -r -g ecmanaged -d /opt/ecmanaged -s /sbin/nologin \
    -c "account for running ecagent" ecmanaged
%setup -qn %{name}-%{version}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/ecmanaged/ecagent
mkdir -p %{buildroot}/usr/lib/systemd/system
mkdir -p %{buildroot}/etc/cron.d
rsync -av --exclude '*build*' %{_builddir}/%{name}-%{version}/* %{buildroot}/opt/ecmanaged/ecagent/
cp %{_builddir}/%{name}-%{version}/build/redhat/etc/systemd/system/ecagentd.service %{buildroot}/usr/lib/systemd/system/
cp %{_builddir}/%{name}-%{version}/build/redhat/etc/cron.d/ecmanaged-ecagent-systemd %{buildroot}/etc/cron.d/ecmanaged-ecagent

%clean
rm -rf %{buildroot}

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


%files
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
