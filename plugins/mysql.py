# -*- coding:utf-8 -*-

from ecmplugin import ECMPlugin

class ECMMysql(ECMPlugin):
    def cmd_mysql_exec(self, args):
        ' Syntax mysql.exec[hostname],[user],[password],[database],[query]'

        try:
            mysql = __import__("MySQLdb")
        except:
            return(2,"[UNSUPPORTED]")

        if len(args) < 4:
            return(1,self.cmd_mysql_exec.__doc__)
        try:
            conn = mysql.connect(args[0], args[1], args[2], args[3]);

            try: query = args[4]
            except IndexError: query = "SELECT VERSION()"

            cursor = conn.cursor()
            cursor.execute(query)

            retr = cursor.fetchall()

            cursor.close()
            conn.close()

            return(0,retr)

        except mysql.Error, e:

            return(2,"[ERROR] %s" % (e.args[1]))
