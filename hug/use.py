"""hug/use.py

Provides a mechanism for using external hug APIs both locally or remotely in a seamless fashion

Copyright (C) 2015  Timothy Edmund Crosley

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
import re
import socket
from collections import namedtuple
from io import BytesIO
from queue import Queue

import falcon
import requests

import hug._empty as empty
from hug.api import API
from hug.defaults import input_format
from hug.input_format import separate_encoding

Response = namedtuple('Response', ('data', 'status_code', 'headers'))
Request = namedtuple('Request', ('content_length', 'stream', 'params'))


class Service(object):
    """Defines the base concept of a consumed service.
        This is to enable encapsulating the logic of calling a service so usage can be independant of the interface
    """
    __slots__ = ('timeout', 'raise_on', 'version')

    def __init__(self, version=None, timeout=None, raise_on=(500, ), **kwargs):
        self.version = version
        self.timeout = timeout
        self.raise_on = raise_on if type(raise_on) in (tuple, list) else (raise_on, )

    def request(self, method, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "CALL" method"""
        raise NotImplementedError("Concrete services must define the request method")

    def get(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "GET" method"""
        return self.request('GET', url=url, headers=headers, timeout=timeout, **params)

    def post(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "POST" method"""
        return self.request('POST', url=url, headers=headers, timeout=timeout, **params)

    def delete(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "DELETE" method"""
        return self.request('DELETE', url=url, headers=headers, timeout=timeout, **params)

    def put(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "PUT" method"""
        return self.request('PUT', url=url, headers=headers, timeout=timeout, **params)

    def trace(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "TRACE" method"""
        return self.request('TRACE', url=url, headers=headers, timeout=timeout, **params)

    def patch(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "PATCH" method"""
        return self.request('PATCH', url=url, headers=headers, timeout=timeout, **params)

    def options(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "OPTIONS" method"""
        return self.request('OPTIONS', url=url, headers=headers, timeout=timeout, **params)

    def head(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "HEAD" method"""
        return self.request('HEAD', url=url, headers=headers, timeout=timeout, **params)

    def connect(self, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        """Calls the service at the specified URL using the "CONNECT" method"""
        return self.request('CONNECT', url=url, headers=headers, timeout=timeout, **params)


class HTTP(Service):
    __slots__ = ('endpoint', 'session')

    def __init__(self, endpoint, auth=None, version=None, headers=empty.dict, timeout=None, raise_on=(500, ), **kwargs):
        super().__init__(timeout=timeout, raise_on=raise_on, version=version, **kwargs)
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.auth = auth
        self.session.headers.update(headers)

    def request(self, method, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        url = "{0}/{1}".format(self.version, url.lstrip('/')) if self.version else url
        response = self.session.request(method, self.endpoint + url.format(url_params), headers=headers, params=params)

        data = BytesIO(response.content)
        (content_type, encoding) = separate_encoding(response.headers.get('content-type', ''), 'utf-8')
        if content_type in input_format:
            data = input_format[content_type](data, encoding)

        if response.status_code in self.raise_on:
            raise requests.HTTPError('{0} {1} occured for url: {2}'.format(response.status_code, response.reason, url))

        return Response(data, response.status_code, response.headers)


class Local(Service):
    __slots__ = ('api', 'headers')

    def __init__(self, api, version=None, headers=empty.dict, timeout=None, raise_on=(500, ), **kwargs):
        super().__init__(timeout=timeout, raise_on=raise_on, version=version, **kwargs)
        self.api = API(api)
        self.headers = headers

    def request(self, method, url, url_params=empty.dict, headers=empty.dict, timeout=None, **params):
        function = self.api.http.versioned.get(self.version, {}).get(url, None)
        if not function:
            function = self.api.http.versioned.get(None, {}).get(url, None)

        if not function:
            if 404 in self.raise_on:
                raise requests.HTTPError('404 Not Found occured for url: {0}'.format(url))
            return Response('Not Found', 404, {'content-type', 'application/json'})

        interface = function.interface.http
        response = falcon.Response()
        request = Request(None, None, empty.dict)
        interface.set_response_defaults(response)

        params.update(url_params)
        params = interface.gather_parameters(request, response, api_version=self.version, **params)
        errors = interface.validate(params)
        if errors:
            interface.render_errors(errors, request, response)
        else:
            interface.render_content(interface.call_function(**params), request, response)

        data = BytesIO(response.data)
        (content_type, encoding) = separate_encoding(response._headers.get('content-type', ''), 'utf-8')
        if content_type in input_format:
            data = input_format[content_type](data, encoding)

        status_code = int(''.join(re.findall('\d+', response.status)))
        if status_code in self.raise_on:
            raise requests.HTTPError('{0} occured for url: {1}'.format(response.status, url))

        return Response(data, status_code, response._headers)


class Socket(Service):
    __slots__ = ('connection_pool', 'timeout', 'connection', 'send_and_receive')

    Connection = namedtuple('Connection', ('connect_to', 'proto', 'sockopts'))
    protocols = {
        'tcp': (socket.AF_INET, socket.SOCK_STREAM),
        'unix_stream': (socket.AF_UNIX, socket.SOCK_STREAM),
        'udp': (socket.AF_INET, socket.SOCK_DGRAM),
        'unix_dgram': (socket.AF_UNIX, socket.SOCK_DGRAM)
    }
    streams = ('tcp', 'unix_stream')
    datagrams = ('udp', 'unix_dgram')

    def __init__(self, connect_to, proto, version=None,
                 headers=empty.dict, timeout=None, pool=0, raise_on=(500, ), **kwargs):
        super().__init__(timeout=timeout, raise_on=raise_on, version=version, **kwargs)
        self.timeout = timeout
        self.connection = Socket.Connection(connect_to, proto, set())
        self.connection_pool = Queue(maxsize=pool if pool else 1)

        if proto in Socket.streams:
            self.send_and_receive = self._stream_send_and_receive
        else:
            self.send_and_receive = self._dgram_send_and_receive

    def settimeout(self, timeout):
        """Set the default timeout"""
        self.timeout = timeout

    def setsockopt(self, *sockopts):
        """Add socket options to set"""
        if type(sockopts[0]) in (list, tuple):
            for sock_opt in sockopts[0]:
                level, option, value = sock_opt
                self.connection.sockopts.add((level, option, value))
        else:
            level, option, value = sockopts
            self.connection.sockopts.add((level, option, value))

    def _register_socket(self):
        """Create/Connect socket, apply options"""
        _socket = socket.socket(*Socket.protocols[self.connection.proto])
        _socket.settimeout(self.timeout)

        # Reconfigure original socket options.
        if self.connection.sockopts:
            for sock_opt in self.connection.sockopts:
                level, option, value = sock_opt
                _socket.setsockopt(level, option, value)

        _socket.connect(self.connection.connect_to)
        return _socket

    def _stream_send_and_receive(self, _socket, message, *args, **kwargs):
        """TCP/Stream sender and receiver"""
        data = BytesIO()

        _socket_fd = _socket.makefile(mode='rwb', encoding='utf-8')
        _socket_fd.write(message.encode('utf-8'))
        _socket_fd.flush()

        for received in _socket_fd:
            data.write(received)
        data.seek(0)

        _socket_fd.close()
        return data

    def _dgram_send_and_receive(self, _socket, message, buffer_size=4096, *args):
        """User Datagram Protocol sender and receiver"""
        _socket.sendto(message.encode('utf-8'), self.connection.connect_to)
        data, address = _socket.recvfrom(buffer_size)
        return BytesIO(data)

    def request(self, message, timeout=None, *args, **kwargs):
        """Populate connection pool, send message, return BytesIO, and cleanup"""
        if not self.connection_pool.full():
            self.connection_pool.put(self._register_socket())

        _socket = self.connection_pool.get()
        _socket.settimeout(timeout)

        data = self.send_and_receive(_socket, message, *args, **kwargs)

        if self.connection.proto in Socket.streams:
            _socket.shutdown(socket.SHUT_RDWR)

        return Response(data, None, None)
