"""hug/test.py.

Defines utility function that aid in the round-trip testing of Hug APIs

Copyright (C) 2016  Timothy Edmund Crosley

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

import sys
from functools import partial
from io import BytesIO
from unittest import mock
from urllib.parse import urlencode

from falcon import HTTP_METHODS
from falcon.testing import StartResponseMock, create_environ
from hug import output_format
from hug.api import API
from hug.json_module import json


def call(method, api_or_module, url, body='', headers=None, params=None, query_string='', scheme='http', **kwargs):
    """Simulates a round-trip call against the given API / URL"""
    api = API(api_or_module).http.server()
    response = StartResponseMock()
    headers = {} if headers is None else headers
    if not isinstance(body, str) and 'json' in headers.get('content-type', 'application/json'):
        body = output_format.json(body)
        headers.setdefault('content-type', 'application/json')

    params = params if params else {}
    params.update(kwargs)
    if params:
        query_string = '{}{}{}'.format(query_string, '&' if query_string else '', urlencode(params, True))
    result = api(create_environ(path=url, method=method, headers=headers, query_string=query_string,
                                body=body, scheme=scheme), response)
    if result:
        try:
            response.data = result[0].decode('utf8')
        except TypeError:
            data = BytesIO()
            for chunk in result:
                data.write(chunk)
            data = data.getvalue()
            try:
                response.data = data.decode('utf8')
            except UnicodeDecodeError:   # pragma: no cover
                response.data = data
        except (UnicodeDecodeError, AttributeError):
            response.data = result[0]
        response.content_type = response.headers_dict['content-type']
        if 'application/json' in response.content_type:
            response.data = json.loads(response.data)

    return response


for method in HTTP_METHODS:
    tester = partial(call, method)
    tester.__doc__ = """Simulates a round-trip HTTP {0} against the given API / URL""".format(method.upper())
    globals()[method.lower()] = tester


def cli(method, *args, api=None, module=None, **arguments):
    """Simulates testing a hug cli method from the command line"""
    collect_output = arguments.pop('collect_output', True)
    if api and module:
        raise ValueError("Please specify an API OR a Module that contains the API, not both")
    elif api or module:
        method = API(api or module).cli.commands[method].interface._function

    command_args = [method.__name__] + list(args)
    for name, values in arguments.items():
        if not isinstance(values, (tuple, list)):
            values = (values, )
        for value in values:
            command_args.append('--{0}'.format(name))
            if not value in (True, False):
                command_args.append('{0}'.format(value))

    old_sys_argv = sys.argv
    sys.argv = [str(part) for part in command_args]

    old_output = method.interface.cli.output
    if collect_output:
        method.interface.cli.outputs = lambda data: to_return.append(data)
    to_return = []

    try:
        method.interface.cli()
    except Exception as e:
        to_return = (e, )

    method.interface.cli.output = old_output
    sys.argv = old_sys_argv
    return to_return and to_return[0] or None
