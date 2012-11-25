
class Http(object):
    """http class using one of python's built-in http libraries"""
    def __init__(self):
        try:
            # attemp to use httplib2 as it is 4x faster than urllib2!
            import httplib2
            self.http = httplib2.Http(timeout = 60)
        except:
            # default to urllib2
            import urllib2
            self.urllib2 = urllib2

    def send_http_request(self, url = '', req_xml = '', soap_action = ''):
        """sends a standard http request and returns xml/html/etc"""
        headers = {}
        data = None
        if req_xml and soap_action:
            # this is an API request...
            headers["SOAPAction"] = soap_action
            data = req_xml
        # send request
        try:
            # try httplib2. note: resp[0] = headers, [1] = xml/html
            return self.http.request(url, 'GET', data, headers)[1]
        except AttributeError:
            req = self.urllib2.Request(url, data, headers)
            return self.urllib2.urlopen(req, timeout = 60).read()

