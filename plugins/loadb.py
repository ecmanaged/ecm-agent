# -*- coding:utf-8 -*-

import httplib2
import urlparse
import urllib

class HTTPConnection:
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
        path = resource
        headers['User-Agent'] = 'Basic Agent'
        headers['Content-Type']='application/json'

        if args: path += u"?" + urllib.urlencode(args)

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


from ecmplugin import ECMPlugin
import simplejson as json
import inspect

class ECMLoadb(ECMPlugin):
    def __init__(self, *argv, **kwargs):
        url      = kwargs.get('url',     None)
        username = kwargs.get('username','admin')
        password = kwargs.get('password',None)

        # Make connection (but not for run())
        if not 'run()' in str(inspect.stack()[1][4]):
            self.conn = self._connect(url,username,password)

    def cmd_loadb_info(self, *argv, **kwargs):
        retval = self._get_resource('GET','/')

        return self._return(retval)

    def cmd_loadb_service_info(self, *argv, **kwargs):
        service_id = kwargs.get('service_id',  None)
            
        if not service_id: raise Exception("Invalid parameters")
        loadb_info = self.cmd_loadb_info()
        # TODO: filter it

    def cmd_loadb_service_add(self, *argv, **kwargs):
        service_id   = kwargs.get('service_id',  None)
        service_ip   = kwargs.get('service_ip',  None)
        service_port = kwargs.get('service_port',None)

        if not (service_id and service_ip and service_port):
            raise Exception("Invalid parameters")

        data = {'ip':service_ip,'port':service_port}
        retval = self._get_resource('POST','/service/' + service_id + '/',data)

        return self._return(retval)

    def cmd_loadb_service_delete(self, *argv, **kwargs):
        service_id = kwargs.get('service_id',None)

        if not service_id:
            raise Exception("Invalid parameters")

        retval = self._get_resource('DELETE','/service/' + service_id + '/')

        return self._return(retval)

    def cmd_loadb_node_info(self, *argv, **kwargs):
        node_id = kwargs.get('node_id',   None)

        if not node_id: raise Exception("Invalid parameters")

        loadb_info = self.cmd_loadb_info()
        # TODO: filter it

    def cmd_loadb_node_add(self, *argv, **kwargs):
        service_id = kwargs.get('service_id',None)
        node_id    = kwargs.get('node_id',   None)
        node_ip    = kwargs.get('node_ip',   None)
        node_port  = kwargs.get('node_port', None)

        if not (service_id and node_id and node_ip and node_port):
            raise Exception("Invalid parameters")

        data = {'ip':node_ip,'port':node_port}
        retval = self._get_resource('POST','/service/' + service_id + '/' + node_id + '/',data)

        return self._return(retval)

    def cmd_loadb_node_delete(self, *argv, **kwargs):
        service_id = kwargs.get('service_id',None)
        node_id    = kwargs.get('node_id',   None)

        if not (node_id and service_id):
            raise Exception("Invalid parameters")

        retval = self._get_resource('DELETE','/service/' + service_id + '/' + node_id + '/')

        return self._return(retval)

    def _connect(self,url,user,password):
        try:
            # connect and test get info
            conn = HTTPConnection(url,user,password)
            conn.cmd_loadb_info()
            return conn
        except:
            raise Exception("Unable to connect to %s" % url)

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

ECMLoadb().run()

## Test
#test = ECMloadb(url='http://localhost:5002',password='*EQ%0O%C2R5DT7)HRHZA#%3R^UXL*D(OKDKK)#GS5NU#T0NGWWO8THA(RW0X')
#test_info_pre =  test.cmd_loadb_info()
#print test.cmd_loadb_service_add(service_id = 'www2', service_ip = '1.2.3.255', service_port = '99')
#print test.cmd_loadb_node_add(service_id = 'www2', node_id='test', node_ip = '1.2.3.255', node_port = '99')
#print test.cmd_loadb_node_delete(service_id = 'www2', node_id='test')
#print test.cmd_loadb_service_delete(service_id = 'www2')
#test_info_post = test.cmd_loadb_info()
#if test_info_pre == test_info_post:
#    print "OK: \n%s" % test_info_post

