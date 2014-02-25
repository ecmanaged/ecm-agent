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
#%define	sname	  ecm-agent
%define	ename	  ecagentd
%define	pname	  ecmanaged	  
%define summary   EC Managed - Monitor and deploy agent
%define version   1.1.14
%define release   88
%define license   GPLv3+
%define group     Applications/System
%define user	`whoami` 
%define source_path /home/%{user}/rpmbuild/SOURCES/
%define source    %{pname}-%{version}.tar.gz
%define url       http://www.ecmanaged.com
%define vendor    Ackstorm
%define packager  Gonzalo Radio <gonzalo.radio@ackstorm.com> 
%define buildroot %{_tmppath}/%{pname}-%{version}
%define _prefix   /opt

Name:		%{name}
Summary:	%{summary}
Version:	%{version}
Release:	%{release}
License:	%{license}
Group:		%{group}
Source0:	%{source}
BuildArch:	noarch
#Requires:	redhat-lsb >= 3.2
Requires:       python
Requires:       python-twisted-core
Requires:       python-twisted-web
Requires:       python-protocols
Requires:       python-dmidecode
Requires:       dmidecode
Requires:       python-configobj
Requires:       python-twisted-words
Requires:       python-psutil
Requires:       libxml2-python
Requires:       python-simplejson
Requires:       rpm-python
Requires:	MySQL-python
Requires:	python-crypto
Requires:	python-httplib2
Provides:	%{name}
URL:		%{url}
Buildroot:	%{buildroot}

%description

EC Managed - Monitor and deploy agent

%prep
%setup -q -n %{pname}-%{version}

%build

%install
if [ "$RPM_BUILD_ROOT" = "%{_tmppath}/%{pname}-%{version}" ]; then
	rm -rf $RPM_BUILD_ROOT
	mkdir -p $RPM_BUILD_ROOT/opt
	mkdir -p $RPM_BUILD_ROOT/etc
	mkdir -p $RPM_BUILD_ROOT/etc/rc.d/init.d
	mkdir -p $RPM_BUILD_ROOT/etc/cron.d
	#mkdir -p $RPM_BUILD_ROOT/usr/share/doc/ecmanaged-ecagent/
	tar -xzf %{source_path}%{source} -C %{source_path}
	rsync -av --exclude '*build*' %{source_path}%{pname}-%{version}/* $RPM_BUILD_ROOT/opt
	install -m 755 %{source_path}%{pname}-%{version}/ecmanaged/ecagent/build/redhat/etc/init.d/%{ename} $RPM_BUILD_ROOT/etc/rc.d/init.d
	install -m 644 %{source_path}%{pname}-%{version}/ecmanaged/ecagent/build/redhat/etc/cron.d/ecmanaged-ecagent $RPM_BUILD_ROOT/etc/cron.d
	#cp -a /usr/share/doc/ecmanaged-ecagent/ $RPM_BUILD_ROOT/usr/share/doc/ecmanaged-ecagent/
	rm -rf %{source_path}%{pname}-%{version}/build
fi

%clean
if [ "$RPM_BUILD_ROOT" = "%{_tmppath}/%{pname}-%{version}" ]; then
	rm -rf $RPM_BUILD_ROOT
else
	echo "Invalid Build root "${RPM_BUILD_ROOT}"."
	exit 1
fi
if [ -e %{source_path}%{pname}-%{version} ]; then 
	rm -rf %{source_path}%{pname}-%{version}
fi

%post
if [ "$1" = "1" ]; then
	chkconfig --add %{ename}
	chkconfig --level 2345 %{ename} on
	service %{ename} start >/dev/null 2>&1
fi

%preun
if [ "$1" = "0" ]; then
	service %{ename} stop >/dev/null 2>&1
	chkconfig --del %{ename}
fi

%files
%defattr(-,root,root)
%attr(755,root,root) /etc/rc.d/init.d/%{ename}
%attr(644,root,root) /etc/cron.d/ecmanaged-ecagent
%attr(755,root,root) /opt/%{pname}
%attr(400,root,root) %config /opt/ecmanaged/ecagent/config/ecagent.cfg

%changelog
* Wed Feb 20 2014 %{packager} - init 
- Initialize %{name}-%{ver}.%{rel}.
