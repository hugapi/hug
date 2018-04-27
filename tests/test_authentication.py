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

from falcon import HTTPUnauthorized
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

    custom_context = dict(custom='context', username='Tim', password='Custom password')

    @hug.context_factory()
    def create_test_context(*args, **kwargs):
        return custom_context

    @hug.delete_context()
    def delete_custom_context(context, exception=None, errors=None, lacks_requirement=None):
        assert context == custom_context
        assert not errors
        context['exception'] = exception

    @hug.authentication.basic
    def context_basic_authentication(username, password, context):
        assert context == custom_context
        if username == context['username'] and password == context['password']:
            return True

    @hug.get(requires=context_basic_authentication)
    def hello_context():
        return 'context!'

    assert '401' in hug.test.get(api, 'hello_context').status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']
    assert '401' in hug.test.get(api, 'hello_context', headers={'Authorization': 'Not correctly formed'}).status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']
    assert '401' in hug.test.get(api, 'hello_context', headers={'Authorization': 'Nospaces'}).status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']
    assert '401' in hug.test.get(api, 'hello_context', headers={'Authorization': 'Basic VXNlcjE6bXlwYXNzd29yZA'}).status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']

    token = b64encode('{0}:{1}'.format('Tim', 'Custom password').encode('utf8')).decode('utf8')
    assert hug.test.get(api, 'hello_context', headers={'Authorization': 'Basic {0}'.format(token)}).data == 'context!'
    assert not custom_context['exception']
    del custom_context['exception']
    token = b'Basic ' + b64encode('{0}:{1}'.format('Tim', 'Custom password').encode('utf8'))
    assert hug.test.get(api, 'hello_context', headers={'Authorization': token}).data == 'context!'
    assert not custom_context['exception']
    del custom_context['exception']
    token = b'Basic ' + b64encode('{0}:{1}'.format('Tim', 'Wrong password').encode('utf8'))
    assert '401' in hug.test.get(api, 'hello_context', headers={'Authorization': token}).status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']


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

    custom_context = dict(custom='context')

    @hug.context_factory()
    def create_test_context(*args, **kwargs):
        return custom_context

    @hug.delete_context()
    def delete_custom_context(context, exception=None, errors=None, lacks_requirement=None):
        assert context == custom_context
        assert not errors
        context['exception'] = exception

    @hug.authentication.api_key
    def context_api_key_authentication(api_key, context):
        assert context == custom_context
        if api_key == 'Bacon':
            return 'Timothy'

    @hug.get(requires=context_api_key_authentication)
    def hello_context_world():
        return 'Hello context world!'

    assert hug.test.get(api, 'hello_context_world', headers={'X-Api-Key': 'Bacon'}).data == 'Hello context world!'
    assert not custom_context['exception']
    del custom_context['exception']
    assert '401' in hug.test.get(api, 'hello_context_world').status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']
    assert '401' in hug.test.get(api, 'hello_context_world', headers={'X-Api-Key': 'Invalid'}).status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']


def test_token_auth():
    """Test JSON Web Token"""
    #generated with jwt.encode({'user': 'Timothy','data':'my data'}, 'super-secret-key-please-change', algorithm='HS256')
    precomptoken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjoibXkgZGF0YSIsInVzZXIiOiJUaW1vdGh5In0.' \
                   '8QqzQMJUTq0Dq7vHlnDjdoCKFPDAlvxGCpc_8XF41nI'

    @hug.authentication.token
    def token_authentication(token):
        if token == precomptoken:
            return 'Timothy'

    @hug.get(requires=token_authentication)
    def hello_world():
        return 'Hello World!'

    assert hug.test.get(api, 'hello_world', headers={'Authorization': precomptoken}).data == 'Hello World!'
    assert '401' in hug.test.get(api, 'hello_world').status
    assert '401' in hug.test.get(api, 'hello_world', headers={'Authorization': 'eyJhbGci'}).status

    custom_context = dict(custom='context')

    @hug.context_factory()
    def create_test_context(*args, **kwargs):
        return custom_context

    @hug.delete_context()
    def delete_custom_context(context, exception=None, errors=None, lacks_requirement=None):
        assert context == custom_context
        assert not errors
        context['exception'] = exception

    @hug.authentication.token
    def context_token_authentication(token, context):
        assert context == custom_context
        if token == precomptoken:
            return 'Timothy'

    @hug.get(requires=context_token_authentication)
    def hello_context_world():
        return 'Hello context!'

    assert hug.test.get(api, 'hello_context_world', headers={'Authorization': precomptoken}).data == 'Hello context!'
    assert not custom_context['exception']
    del custom_context['exception']
    assert '401' in hug.test.get(api, 'hello_context_world').status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']
    assert '401' in hug.test.get(api, 'hello_context_world', headers={'Authorization': 'eyJhbGci'}).status
    assert isinstance(custom_context['exception'], HTTPUnauthorized)
    del custom_context['exception']


def test_documentation_carry_over():
    """Test to ensure documentation correctly carries over - to address issue #252"""
    authentication = hug.authentication.basic(hug.authentication.verify('User1', 'mypassword'))
    assert authentication.__doc__ == 'Basic HTTP Authentication'


def test_missing_authenticator_docstring():

    @hug.authentication.authenticator
    def custom_authenticator(*args, **kwargs):
        return None

    authentication = custom_authenticator(None)

    @hug.get(requires=authentication)
    def hello_world():
        return 'Hello World!'

    hug.test.get(api, 'hello_world')
