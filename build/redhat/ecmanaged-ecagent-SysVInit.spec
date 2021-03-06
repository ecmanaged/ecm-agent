#===============================================================================
# Copyright 2014 ACKSTORM S.L.
# Name: ecmanaged-ecagent-SysVInit.spec 
#-------------------------------------------------------------------------------
# $Id: ecmanaged-ecagent-SysVInit.spec,v 0.9 2014/02/20 11:10:00 $
#-------------------------------------------------------------------------------
# Purpose: RPM Spec file for ecagent on sysv init systems
#===============================================================================

# No debuginfo:
%define debug_package %{nil}

%define name      ecmanaged-ecagent
%define ename     ecagentd
%define pname     ecmanaged
%define version   2.2

Name:             %{name}
Version:          %{version}       
Release:          1.sysvinit
Summary:          ECManaged  Agent - Monitoring and deployment agent (sysvinit)
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

Requires(post):   chkconfig
Requires(preun):  chkconfig
# This is for /sbin/service
Requires(preun):  initscripts

Provides:         ecmanaged-ecagent

%description
ECManaged  Agent - Monitoring and deployment agent

%prep
%setup -qn %{name}-%{version}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/ecmanaged/ecagent
mkdir -p %{buildroot}/etc
mkdir -p %{buildroot}/etc/rc.d/init.d
mkdir -p %{buildroot}/etc/cron.d
rsync -av --exclude '*build*' %{_builddir}/%{name}-%{version}/* %{buildroot}/opt/ecmanaged/ecagent/
install -m 750 %{_builddir}/%{name}-%{version}/build/redhat/etc/init.d/%{ename} %{buildroot}/etc/rc.d/init.d
install -m 644 %{_builddir}/%{name}-%{version}/build/redhat/etc/cron.d/ecmanaged-ecagent-SysVinit %{buildroot}/etc/cron.d/ecmanaged-ecagent

%clean
rm -rf %{buildroot}

%pre
if [[ $1 == 2 ]]; then
  # Stop the service if we're upgrading
  service %{ename} stop >/dev/null 2>&1
fi

%post
chkconfig --add %{ename}
chkconfig --level 2345 %{ename} on
service %{ename} start >/dev/null 2>&1

%preun
if [[ $1 -eq 0 ]]; then
  # Stop and remove service on uninstall
  service %{ename} stop >/dev/null 2>&1
  chkconfig --del %{ename}
fi

%files
%defattr(755,root,root,-)

%doc LICENSE README.md
%doc /opt/ecmanaged/ecagent/LICENSE
%doc /opt/ecmanaged/ecagent/README.md

%attr(750,root,root) /etc/rc.d/init.d/ecagentd
%attr(640,root,root) /etc/cron.d/ecmanaged-ecagent

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

%dir %attr(700,root,root) %config /opt/ecmanaged/ecagent/config
%attr(400,root,root) %config /opt/ecmanaged/ecagent/config/ecagent.init.cfg
%attr(400,root,root) %config /opt/ecmanaged/ecagent/config/xmpp_cert.pub

%changelog
* Wed Feb 25 2015 Arindam Choudhury <arindam@live.com> - 2.1.2-109
- updated for better systemd integration
