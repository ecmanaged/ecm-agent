# -*- coding:utf-8 -*-

from ecmplugin import ECMPlugin
import simplejson as json

class ECMMysql(ECMPlugin):
    def cmd_mysql_exec(self, *argv, **kwargs):
        ' Syntax mysql.exec[hostname],[user],[password],[database],[query]'

        try:
            _mysql = __import__("MySQLdb")

        except:
            raise Exception("Unsupported MySQLdb")

        user                = kwargs.get('user','root')
        password            = kwargs.get('password','')
        database            = kwargs.get('database','')
        host                = kwargs.get('host','localhost')
        query               = kwargs.get('query','SELECT VERSION()')
        default_file        = kwargs.get('default_file','')

        if default_file == '/etc/mysql/debian.cnf':
            user = 'debian-sys-maint'

        try:
            conn = _mysql.connect(host=host,user=user,passwd=password,db=database,read_default_file=default_file)

        except Exception as e:
            raise Exception("Unable to connect: %s" % e[1])

        try:
            cursor = conn.cursor()
            cursor.execute(query)

            retval = cursor.fetchall()

            cursor.close()
            conn.close()

            return(json.dumps(retval))

        except _mysql.Error, e:
            print "Error %d: %s" % (e.args[0], e.ags[1])


ECMMysql.run()
