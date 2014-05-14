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

# Local
from __plugin import ECMPlugin
import __helper as ecm

class ECMMysql(ECMPlugin):
    def cmd_mysql_exec(self, *argv, **kwargs):
        """ Syntax mysql.exec[hostname],[user],[password],[database],[query] """

        # Check required modules to connect
        _mysql = self._check_modules()

        user = kwargs.get('user', 'root')
        password = kwargs.get('password', '')
        database = kwargs.get('database', '')
        host = kwargs.get('host', 'localhost')
        query = kwargs.get('query', 'SELECT VERSION()')
        default_file = kwargs.get('default_file', '')

        if default_file == '/etc/mysql/debian.cnf':
            user = 'debian-sys-maint'

        try:
            if default_file:
                conn = _mysql.connect(host=host, user=user, db=database, read_default_file=default_file)
            else:
                conn = _mysql.connect(host=host, user=user, passwd=password, db=database)

        except Exception as e:
            raise Exception("Unable to connect: %s" % e[1])

        try:
            cursor = conn.cursor()
            cursor.execute(query)

            retval = cursor.fetchall()

            cursor.close()
            conn.close()

            return retval

        except _mysql.Error, e:
            print "Error %d: %s" % (e.args[0], e.args[1])

    def cmd_mysql_stats(self, *argv, **kwargs):
        """
        mysql.stats[]
        """

        # Check required modules to connect
        _mysql = self._check_modules()

        status_array = {}
        return status_array

    @staticmethod
    def _check_modules():
        try:
            _mysql = __import__("MySQLdb")
        except ImportError:
            # Try to install package and try again
            ecm.install_package('python-mysqldb')

            try:
                _mysql = __import__("MySQLdb")
            except:
                raise Exception("Unsupported MySQLdb")

        return _mysql


ECMMysql().run()
