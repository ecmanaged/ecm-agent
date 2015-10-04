%define _unpackaged_files_terminate_build 0
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
Requires(pre): shadow-utils
Requires: python2 python-devel pygobject3 PackageKit PolicyKit dbus-python python-twisted python-protocols python-configobj python-psutil libxml2-python python-simplejson rpm-python python-crypto python-httplib2 python-pip
Url: www.ecmanaged.com
BuildRequires: systemd

%description
ECManaged  Agent - Monitoring and deployment agent

%prep
%setup -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%pre
getent group ecmanaged >/dev/null || groupadd -r ecmanaged
getent passwd ecmanaged >/dev/null || \
    useradd -r -g ecmanaged -d /opt/ecmanaged -s /sbin/nologin \
    -c "account for running ecagent" ecmanaged
if [[ $1 == 2 ]]; then
  # Stop the service if we're upgrading
  systemctl stop ecagentd.service >/dev/null 2>&1
fi

%post
systemctl daemon-reload
systemctl enable ecagentd.service
systemctl daemon-reload

chown -R ecmanaged:ecmanaged /opt/ecmanaged
mkdir -p /etc/ecmanaged
chown -R ecmanaged:ecmanaged /etc/ecmanaged

systemctl start ecagentd.service >/dev/null 2>&1

%preun
if [[ $1 -eq 0 ]]; then
  # Stop and remove service on uninstall
  systemctl stop ecagentd.service >/dev/null 2>&1
  systemctl disable ecagentd.service
  systemctl daemon-reload
fi

%files -f INSTALLED_FILES
%defattr(760,ecmanaged,ecmanaged,-)