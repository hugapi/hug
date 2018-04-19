"""hug/middleware.py

A collection of useful middlewares to automate common hug functionality

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
from __future__ import absolute_import

import logging
import re
import uuid
from datetime import datetime


class SessionMiddleware(object):
    """Simple session middleware.

    Injects a session dictionary into the context of a request, sets a session cookie,
    and stores/restores data via a coupled store object.

    A session store object must implement the following methods:
    * get(session_id) - return session data
    * exists(session_id) - return boolean if session ID exists or not
    * set(session_id, session_data) - save session data for given session ID

    The name of the context key can be set via the 'context_name' argument.
    The cookie arguments are the same as for falcons set_cookie() function, just prefixed with 'cookie_'.
    """
    __slots__ = ('store', 'context_name', 'cookie_name', 'cookie_expires', 'cookie_max_age', 'cookie_domain',
                 'cookie_path', 'cookie_secure', 'cookie_http_only')

    def __init__(self, store, context_name='session', cookie_name='sid', cookie_expires=None, cookie_max_age=None,
                 cookie_domain=None, cookie_path=None, cookie_secure=True, cookie_http_only=True):
        self.store = store
        self.context_name = context_name
        self.cookie_name = cookie_name
        self.cookie_expires = cookie_expires
        self.cookie_max_age = cookie_max_age
        self.cookie_domain = cookie_domain
        self.cookie_path = cookie_path
        self.cookie_secure = cookie_secure
        self.cookie_http_only = cookie_http_only

    def generate_sid(self):
        """Generate a UUID4 string."""
        return str(uuid.uuid4())

    def process_request(self, request, response):
        """Get session ID from cookie, load corresponding session data from coupled store and inject session data into
            the request context.
        """
        sid = request.cookies.get(self.cookie_name, None)
        data = {}
        if sid is not None:
            if self.store.exists(sid):
                data = self.store.get(sid)
        request.context.update({self.context_name: data})

    def process_response(self, request, response, resource):
        """Save request context in coupled store object. Set cookie containing a session ID."""
        sid = request.cookies.get(self.cookie_name, None)
        if sid is None or not self.store.exists(sid):
            sid = self.generate_sid()

        self.store.set(sid, request.context.get(self.context_name, {}))
        response.set_cookie(self.cookie_name, sid, expires=self.cookie_expires, max_age=self.cookie_max_age,
                            domain=self.cookie_domain, path=self.cookie_path, secure=self.cookie_secure,
                            http_only=self.cookie_http_only)


class LogMiddleware(object):
    """A middleware that logs all incoming requests and outgoing responses that make their way through the API"""
    __slots__ = ('logger', )

    def __init__(self, logger=None):
        self.logger = logger if logger is not None else logging.getLogger('hug')

    def _generate_combined_log(self, request, response):
        """Given a request/response pair, generate a logging format similar to the NGINX combined style."""
        current_time = datetime.utcnow()
        data_len = '-' if response.data is None else len(response.data)
        return '{0} - - [{1}] {2} {3} {4} {5} {6}'.format(request.remote_addr, current_time, request.method,
                                                        request.relative_uri, response.status,
                                                        data_len, request.user_agent)

    def process_request(self, request, response):
        """Logs the basic endpoint requested"""
        self.logger.info('Requested: {0} {1} {2}'.format(request.method, request.relative_uri, request.content_type))

    def process_response(self, request, response, resource):
        """Logs the basic data returned by the API"""
        self.logger.info(self._generate_combined_log(request, response))


class CORSMiddleware(object):
    """A middleware for allowing cross-origin request sharing (CORS)

    Adds appropriate Access-Control-* headers to the HTTP responses returned from the hug API,
    especially for HTTP OPTIONS responses used in CORS preflighting.
    """
    __slots__ = ('api', 'allow_origins', 'allow_credentials', 'max_age')

    def __init__(self, api, allow_origins: list=['*'], allow_credentials: bool=True, max_age: int=None):
        self.api = api
        self.allow_origins = allow_origins
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def match_route(self, reqpath):
        """Match a request with parameter to it's corresponding route"""
        route_dicts = [routes for _, routes in self.api.http.routes.items()][0]
        routes = [route for route, _ in route_dicts.items()]
        if reqpath not in routes:
            for route in routes:  # replace params in route with regex
                reqpath = re.sub('^(/v\d*/?)', '/', reqpath)
                base_url = getattr(self.api.http, 'base_url', '')
                reqpath = reqpath.replace(base_url, '', 1) if base_url else reqpath
                if re.match(re.sub(r'/{[^{}]+}', '/\w+', route) + '$', reqpath):
                    return route

        return reqpath

    def process_response(self, request, response, resource):
        """Add CORS headers to the response"""
        response.set_header('Access-Control-Allow-Origin', ', '.join(self.allow_origins))
        response.set_header('Access-Control-Allow-Credentials', str(self.allow_credentials).lower())

        if request.method == 'OPTIONS': # check if we are handling a preflight request
            allowed_methods = set(
                method
                for _, routes in self.api.http.routes.items()
                for method, _ in routes[self.match_route(request.path)].items()
            )
            allowed_methods.add('OPTIONS')

            # return allowed methods
            response.set_header('Access-Control-Allow-Methods', ', '.join(allowed_methods))
            response.set_header('Allow', ', '.join(allowed_methods))

            # get all requested headers and echo them back
            requested_headers = request.get_header('Access-Control-Request-Headers')
            response.set_header('Access-Control-Allow-Headers', requested_headers or '')

            # return valid caching time
            if self.max_age:
                response.set_header('Access-Control-Max-Age', self.max_age)
