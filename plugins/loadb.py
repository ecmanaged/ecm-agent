# -*- coding:utf-8 -*-

#####################################################
# 3th party
#####################################################

"""
    Copyright (C) 2008 Benjamin O'Steen

    This file is part of python-fedoracommons.

    python-fedoracommons is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    python-fedoracommons is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with python-fedoracommons.  If not, see <http://www.gnu.org/licenses/>.
"""

__license__ = 'GPL http://www.gnu.org/licenses/gpl.txt'
__author__ = "Benjamin O'Steen <bosteen@gmail.com>"
__version__ = '0.1'

import httplib2
import urlparse
import urllib

class Connection:
	def __init__(self, base_url, username=None, password=None):
		self.base_url = base_url
		self.username = username

		self.url = urlparse.urlparse(base_url)

		(scheme, netloc, path, query, fragment) = urlparse.urlsplit(base_url)

		self.scheme = scheme
		self.host = netloc
		self.path = path

		self.h = httplib2.Http(".cache")
		self.h.follow_all_redirects = True
		if username and password:
			self.h.add_credentials(username, password)

	def request_get(self, resource, args = None, headers={}):
		return self.request(resource, "get", args, headers=headers)

	def request_delete(self, resource, args = None, headers={}):
		return self.request(resource, "delete", args, headers=headers)

	def request_head(self, resource, args = None, headers={}):
		return self.request(resource, "head", args, headers=headers)

	def request_post(self, resource, args = None, body = None, headers={}):
		return self.request(resource, "post", args , body = body, headers=headers)

	def request_put(self, resource, args = None, body = None, headers={}):
		return self.request(resource, "put", args , body = body, headers=headers)

	def request(self, resource, method = "get", args = None, body = None, headers={}):
		params = None
		path = resource
		headers['User-Agent'] = 'Basic Agent'
		headers['Content-Type']='application/json'

		if args:
			path += u"?" + urllib.urlencode(args)

		request_path = []
		if self.path != "/":
			if self.path.endswith('/'):
				request_path.append(self.path[:-1])
			else:
				request_path.append(self.path)
			if path.startswith('/'):
				request_path.append(path[1:])
			else:
				request_path.append(path)

		resp, content = self.h.request(u"%s://%s%s" % (self.scheme, self.host, u'/'.join(request_path)), method.upper(), body=body, headers=headers )
		return {u'headers':resp, u'body':content.decode('UTF-8')}


from smplugin import SMPlugin
import simplejson as json

class ECMloadb(SMPlugin):
	def __init__(self, *argv, **kwargs):
		url			= kwargs.get('url',     None)
		username	= kwargs.get('username','admin')
		password	= kwargs.get('password',None)

		if not url: raise Exception("Invalid data")

		# Make connection
		self.conn = self._connect(url,username,password)

	def cmd_loadb_info(self, *argv, **kwargs):
		retval = self._get_resource('GET','/')
		return self._return(retval)

	def cmd_loadb_service_add(self, *argv, **kwargs):
		service_id		= kwargs.get('service_id',  None)
		service_ip		= kwargs.get('service_ip',  None)
		service_port	= kwargs.get('service_port',None)

		if not (service_id and service_ip and service_port):
			raise Exception("Invalid parameters")

		data = {'ip':service_ip,'port':service_port}
		retval = self._get_resource('POST','/service/' + service_id + '/',data)
		return self._return(retval)

	def cmd_loadb_service_delete(self, *argv, **kwargs):
		service_id		= kwargs.get('service_id',None)

		if not service_id:
			raise Exception("Invalid parameters")

		retval = self._get_resource('DELETE','/service/' + service_id + '/')
		return self._return(retval)

	def cmd_loadb_node_add(self, *argv, **kwargs):
		service_id	= kwargs.get('service_id',None)
		node_id		= kwargs.get('node_id',   None)
		node_ip		= kwargs.get('node_ip',   None)
		node_port	= kwargs.get('node_port', None)

		if not (service_id and node_id and node_ip and node_port):
			raise Exception("Invalid parameters")

		data = {'ip':node_ip,'port':node_port}
		retval = self._get_resource('POST','/service/' + service_id + '/' + node_id + '/',data)
		return self._return(retval)

	def cmd_loadb_node_delete(self, *argv, **kwargs):
		service_id	= kwargs.get('service_id',None)
		node_id		= kwargs.get('node_id',   None)

		if not (node_id and service_id):
			raise Exception("Invalid parameters")

		retval = self._get_resource('DELETE','/service/' + service_id + '/' + node_id + '/')
		return self._return(retval)

	def _connect(self,url,user,password):
		conn = Connection(url,user,password)
		return conn

	def _get_resource(self,method,resource,data = None):
		retval = None
		if method == 'GET':
			retval = self.conn.request_get(resource)
		elif method == 'DELETE':
			retval = self.conn.request_delete(resource)
		elif method == 'POST':
			data = json.dumps(data)
			retval = self.conn.request_post(resource,body=data)
		else:
			raise Exception("Invalid method requested")

		return retval

	def _return(self,body):
		retval = 'Unknown'
		try:
			retval = body['body']
			retval = json.loads(retval)
			if retval['status'] == 200:
				return retval['message']
			else:
				raise Exception("Error: %s" % retval['message'])
		except:
			raise Exception("Unknown response error: %s" % retval)

ECMloadb().run()

## Test
#test = ECMloadb(url='http://localhost:5002',password='*EQ%0O%C2R5DT7)HRHZA#%3R^UXL*D(OKDKK)#GS5NU#T0NGWWO8THA(RW0X')
#test_info_pre =  test.cmd_loadb_info()
#print test.cmd_loadb_service_add(service_id = 'www2', service_ip = '1.2.3.255', service_port = '99')
#print test.cmd_loadb_node_add(service_id = 'www2', node_id='maikel', node_ip = '1.2.3.255', node_port = '99')
#print test.cmd_loadb_node_delete(service_id = 'www2', node_id='maikel')
#print test.cmd_loadb_service_delete(service_id = 'www2')
#test_info_post = test.cmd_loadb_info()
#if test_info_pre == test_info_post:
#	print "OK: \n%s" % test_info_post


#cmd_loadb_service_delete




