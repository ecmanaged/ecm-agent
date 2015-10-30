%define _unpackaged_files_terminate_build 0
%define name ecmanaged-ecagent
%define version 3.0
%define unmangled_version 3.0
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
#fedora
Requires:  python2 python-devel python-twisted python-protocols python-configobj python-psutil libxml2-python python-simplejson rpm-python python-crypto python-httplib2 shadow-utils dbus-python sudo
#centos
Requires:  python2 python-devel python-twisted-core python-twisted-web python-twisted-words python-configobj python-psutil libxml2-python python-simplejson rpm-python python-crypto python-httplib2 shadow-utils dbus-python sudo
Url: www.ecmanaged.com


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
if [ $1 -eq 2 ]; then
    if [ -f /opt/ecmanaged/ecagent/init ]; then
        /opt/ecmanaged/ecagent/init stop > /dev/null 2>&1
    fi

    if [ -f /etc/init.d/ecagentd ]; then
        /etc/init.d/ecagentd stop
        chkconfig ecagentd off
        chkconfig --del ecagentd
        rm -f /etc/init.d/ecagentd
    fi

    if which systemctl >/dev/null 2>&1; then
        if systemctl list-units | grep ecagentd >/dev/null 2>&1; then
            systemctl stop ecagentd.service
            systemctl disable ecagentd.service
            if [ -f /usr/lib/systemd/system/ecagentd.service ]; then
                rm -f /usr/lib/systemd/system/ecagentd.service
            fi

            if [ -f /lib/systemd/system/ecagentd.service ]; then
                rm -f /lib/systemd/system/ecagentd.service
            fi
            systemctl daemon-reload
        fi
    fi
fi

%post
if getent passwd ecmanaged >/dev/null 2>&1; then
    chown -R ecmanaged:ecmanaged /opt/ecmanaged
    mkdir -p /etc/ecmanaged
    chown -R ecmanaged:ecmanaged /etc/ecmanaged
fi

if [ $1 -eq 2 ]; then
    /opt/ecmanaged/ecagent/init start > /dev/null 2>&1
fi

%preun
if [ $1 -eq 0 ]; then
    if [ -f /opt/ecmanaged/ecagent/init ]; then
        /opt/ecmanaged/ecagent/init stop > /dev/null 2>&1
    fi

    if [ -f /etc/init.d/ecagentd ]; then
        /etc/init.d/ecagentd stop
        chkconfig ecagentd off
        chkconfig --del ecagentd
    fi

    if which systemctl >/dev/null 2>&1; then
        if systemctl list-units | grep ecagentd >/dev/null 2>&1; then
            systemctl stop ecagentd.service
            systemctl disable ecagentd.service
            systemctl daemon-reload
        fi
    fi
fi

%files -f INSTALLED_FILES
%defattr(760,ecmanaged,ecmanaged,-)
%attr(640,root,root) /etc/cron.d/ecmanaged-ecagent
%attr(440,root,root) /etc/sudoers.d/ecmanaged