#===============================================================================
# Copyright 2014 ACKSTORM S.L.
# Name: ecmanaged-ecagent.spec 
#-------------------------------------------------------------------------------
# $Id: ecmanaged-ecagent.spec,v 0.9 2014/02/20 11:10:00 $
#-------------------------------------------------------------------------------
# Purpose: RPM Spec file for ecagent 
#===============================================================================

# No debuginfo:
%define debug_package %{nil}

%define name      ecmanaged-ecagent
%define ename     ecagentd
%define pname     ecmanaged
%define version   2.1.2

Name:             %{name}
Version:          %{version}       
Release:          109%{?dist}
Summary:          ECManaged  Agent - Monitoring and deployment agent
Group:            Applications/System
License:          GPLv3+
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

Requires:         systemd


Provides:         ecmanaged-ecagent

%description
ECManaged  Agent - Monitoring and deployment agent

%prep
%setup -qn %{name}

%build


%install

rm -rf %{buildroot}

mkdir -p %{buildroot}/opt/ecmanaged/ecagent
mkdir -p %{buildroot}%{_unitdir}/

rsync -av --exclude '*build*' %{_builddir}/%{name}/* %{buildroot}/opt/ecmanaged/ecagent/

cp %{_builddir}/%{name}/build/redhat/etc/systemd/system/ecagentd.service %{buildroot}%{_unitdir}/

%clean
rm -rf %{_buildroot}%{name}
rm -rf %{_source_path}%{name}

%post
systemctl daemon-reload
systemctl enable ecagentd.service
systemctl daemon-reload
systemctl start ecagentd.service >/dev/null 2>&1

%preun
systemctl stop ecagentd.service >/dev/null 2>&1
systemctl disable ecagentd.service
systemctl daemon-reload

%files
%defattr(755,root,root,-)
%dir /opt/ecmanaged/ecagent/
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

%attr(750,root,root) /usr/lib/systemd/system/ecagentd.service

%dir %attr(700,root,root) %config /opt/ecmanaged/ecagent/config
%attr(400,root,root) %config /opt/ecmanaged/ecagent/config/ecagent.init.cfg
%attr(400,root,root) %config /opt/ecmanaged/ecagent/config/xmpp_cert.pub

%exclude /opt/ecmanaged/ecagent/plugins/*.pyc
%exclude /opt/ecmanaged/ecagent/plugins/*.pyo
%exclude /opt/ecmanaged/ecagent/examples/*.pyc
%exclude /opt/ecmanaged/ecagent/examples/*.pyo
%exclude /opt/ecmanaged/ecagent/ecagent/*.pyc
%exclude /opt/ecmanaged/ecagent/ecagent/*.pyo
%exclude /opt/ecmanaged/ecagent/ecagent/*.pyc
%exclude /opt/ecmanaged/ecagent/ecagent/*.pyo
%exclude /opt/ecmanaged/ecagent/configure.pyc
%exclude /opt/ecmanaged/ecagent/configure.pyo

%changelog
* Wed Feb 25 2015 Arindam Choudhury <arindam@live.com> - 2.1.2-109
- updated for better systemd integration
