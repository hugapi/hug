"""tests/test_authentication.py.

Tests hugs built-in authentication helper methods

Copyright (C) 2016 Timothy Edmund Crosley

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
from base64 import b64encode

import falcon
import pytest

import hug

api = hug.API(__name__)


def test_basic_auth():
    """Test to ensure hug provides basic_auth handler works as expected"""
    @hug.get(requires=hug.authentication.basic(hug.authentication.verify('Tim', 'Custom password')))
    def hello_world():
        return 'Hello world!'

    assert '401' in hug.test.get(api, 'hello_world').status
    assert '401' in hug.test.get(api, 'hello_world', headers={'Authorization': 'Not correctly formed'}).status
    assert '401' in hug.test.get(api, 'hello_world', headers={'Authorization': 'Nospaces'}).status
    assert '401' in hug.test.get(api, 'hello_world', headers={'Authorization': 'Basic VXNlcjE6bXlwYXNzd29yZA'}).status

    token = b64encode('{0}:{1}'.format('Tim', 'Custom password').encode('utf8')).decode('utf8')
    assert hug.test.get(api, 'hello_world', headers={'Authorization': 'Basic {0}'.format(token)}).data == 'Hello world!'

    token = b'Basic ' + b64encode('{0}:{1}'.format('Tim', 'Custom password').encode('utf8'))
    assert hug.test.get(api, 'hello_world', headers={'Authorization': token}).data == 'Hello world!'

    token = b'Basic ' + b64encode('{0}:{1}'.format('Tim', 'Wrong password').encode('utf8'))
    assert '401' in hug.test.get(api, 'hello_world', headers={'Authorization': token}).status

def test_api_key():
    """Test the included api_key based header to ensure it works as expected to allow X-Api-Key based authentication"""
    @hug.authentication.api_key
    def api_key_authentication(api_key):
        if api_key == 'Bacon':
            return 'Timothy'

    @hug.get(requires=api_key_authentication)
    def hello_world():
        return 'Hello world!'

    assert hug.test.get(api, 'hello_world', headers={'X-Api-Key': 'Bacon'}).data == 'Hello world!'
    assert '401' in hug.test.get(api, 'hello_world').status
    assert '401' in hug.test.get(api, 'hello_world', headers={'X-Api-Key': 'Invalid'}).status
