"""hug/test.py.

Defines utility function that aid in the round-trip testing of Hug APIs

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
from io import BytesIO
import sys
import json
from functools import partial
from unittest import mock
from urllib.parse import urlencode

from falcon import HTTP_METHODS
from falcon.testing import StartResponseMock, create_environ

from hug import output_format
from hug.run import server


def call(method, api_module, url, body='', headers=None, **params):
    '''Simulates a round-trip call against the given api_module / url'''
    api = server(api_module)
    response = StartResponseMock()
    if not isinstance(body, str):
        body = output_format.json(body)
        headers = {} if headers is None else headers
        headers.setdefault('content-type', 'application/json')

    result = api(create_environ(path=url, method=method, headers=headers, query_string=urlencode(params), body=body),
                 response)
    if result:
        try:
            response.data = result[0].decode('utf8')
        except TypeError:
            response.data = []
            for chunk in result:
                response.data.append(chunk.decode('utf8'))
            response.data = "".join(response.data)
        except UnicodeDecodeError:
            response.data = result[0]
        response.content_type = response.headers_dict['content-type']
        if response.content_type == 'application/json':
            response.data = json.loads(response.data)

    return response


for method in HTTP_METHODS:
    tester = partial(call, method)
    tester.__doc__ = '''Simulates a round-trip HTTP {0} against the given api_module / url'''.format(method.upper())
    globals()[method.lower()] = tester


def cli(method, *kargs, **arguments):
    '''Simulates testing a hug cli method from the command line'''
    collect_output = arguments.pop('collect_output', True)

    command_args = [method.__name__] + list(kargs)
    for name, values in arguments.items():
        if not isinstance(values, (tuple, list)):
            values = (values, )
        for value in values:
            command_args.append('--{0}'.format(name))
            if not value in (True, False):
                command_args.append('{0}'.format(value))

    old_sys_argv = sys.argv
    sys.argv = [str(part) for part in command_args]

    old_output = method.cli.output
    if collect_output:
        method.cli.output = lambda data: to_return.append(data)
    to_return = []

    try:
        method.cli()
    except Exception as e:
        to_return = (e, )

    method.cli.output = old_output
    sys.argv = old_sys_argv
    return to_return and to_return[0] or None

