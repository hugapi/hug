"""hug/middleware.py.

Defines middleware classes for various purposes.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

"""

import uuid


class SessionMiddleware:
    '''

    '''
    def __init__(self, store, cookie_name='sid', cookie_expires=None, cookie_max_age=None, cookie_domain=None,
                 cookie_path=None, cookie_secure=True, cookie_http_only=True):
        self.store = store
        self.cookie_name = cookie_name
        self.cookie_expires = cookie_expires
        self.cookie_max_age = cookie_max_age
        self.cookie_domain = cookie_domain
        self.cookie_path = cookie_path
        self.cookie_secure = cookie_secure
        self.cookie_http_only = cookie_http_only

    def generate_sid(self):
        '''Generate a UUID4 string.'''
        return str(uuid.uuid4())

    def process_request(self, request, response):
        '''
        Get session ID from cookie, load corresponding session data from coupled store and inject session data into
        the request context.
        '''
        sid = request.cookies.get(self.cookie_name, None)
        if sid is not None:
            try:
                data = self.store.get(sid)
            except SessionNotFound:
                return
            request.context.update(data)

    def process_response(self, request, response, resource):
        '''Save request context in coupled store object. Set cookie containing a session ID.'''
        sid = request.cookies.get(self.cookie_name, None)
        if sid is None:
            sid = self.generate_sid()

        self.store.set(sid, request.context)
        response.set_cookie(self.cookie_name, sid, expires=self.cookie_expires, max_age=self.cookie_max_age,
                            domain=self.cookie_domain, path=self.cookie_path, secure=self.cookie_secure,
                            http_only=self.cookie_http_only)
