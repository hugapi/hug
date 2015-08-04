"""tests/test_decorators.py.

Tests the decorators that power hugs core functionality

Copyright (C) 2015 Timothy Edmund Crosley

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
from falcon.testing import StartResponseMock, create_environ
import sys
import hug
import pytest

api = sys.modules[__name__]


def test_basic_call():
    @hug.call()
    def hello_world():
        return "Hello World!"

    assert hello_world() == "Hello World!"
    assert hello_world.interface

    assert hug.test.get(api, '/hello_world') == "Hello World!"


def test_single_parameter():
    @hug.call()
    def echo(text):
        return text

    assert echo('Embrace') == 'Embrace'
    assert echo.interface
    with pytest.raises(TypeError):
        echo()

    assert hug.test.get(api, 'echo', text="Hello") == "Hello"
    assert 'required' in hug.test.get(api, '/echo')['errors']['text'].lower()


def test_custom_url():
    @hug.call('/custom_route')
    def method_name():
        return 'works'

    assert hug.test.get(api, 'custom_route') == 'works'


def test_api_auto_initiate():
    assert isinstance(HUG(create_environ('/non_existant'), StartResponseMock()), (list, tuple))


def test_parameters():
    @hug.call()
    def multiple_parameter_types(start, middle:hug.types.text, end:hug.types.number=5, **kwargs):
        return 'success'

    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end=7) == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle') == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', other="yo") == 'success'

    nan_test = hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end='NAN')
    assert 'invalid' in nan_test['errors']['end']


def test_parameter_injection():
    @hug.call()
    def inject_request(request):
        return request and 'success'
    assert hug.test.get(api, 'inject_request') == 'success'

    @hug.call()
    def inject_response(response):
        return response and 'success'
    assert hug.test.get(api, 'inject_response') == 'success'

    @hug.call()
    def inject_both(request, response):
        return request and response and 'success'
    assert hug.test.get(api, 'inject_both') == 'success'

    @hug.call()
    def inject_in_kwargs(**kwargs):
        return 'request' in kwargs and 'response' in kwargs and 'success'
    assert hug.test.get(api, 'inject_in_kwargs') == 'success'


def test_method_routing():
    @hug.get()
    def method():
        return 'GET'

    @hug.post()
    def method():
        return 'POST'

    @hug.connect()
    def method():
        return 'CONNECT'

    @hug.delete()
    def method():
        return 'DELETE'

    @hug.options()
    def method():
        return 'OPTIONS'

    @hug.put()
    def method():
        return 'PUT'

    @hug.trace()
    def method():
        return 'TRACE'

    assert hug.test.get(api, 'method') == 'GET'
    assert hug.test.post(api, 'method') == 'POST'
    assert hug.test.connect(api, 'method') == 'CONNECT'
    assert hug.test.delete(api, 'method') == 'DELETE'
    assert hug.test.options(api, 'method') == 'OPTIONS'
    assert hug.test.put(api, 'method') == 'PUT'
    assert hug.test.trace(api, 'method') == 'TRACE'

    @hug.call(accept=('GET', 'POST'))
    def accepts_get_and_post():
        return 'success'

    assert hug.test.get(api, 'accepts_get_and_post') == 'success'
    assert hug.test.post(api, 'accepts_get_and_post') == 'success'
    assert 'method not allowed' in hug.test.trace(api, 'accepts_get_and_post').lower()


def test_versioning():
    @hug.version[1].get('/echo')
    def echo(text):
        return text

    @hug.version[2:].get('/echo')
    def echo(text):
        return "Echo: {text}".format(**locals())

    assert hug.test.get(api, 'v1/echo', text="hi") == 'hi'
    assert hug.test.get(api, 'v2/echo', text="hi") == "Echo: hi"
    assert hug.test.get(api, 'v3/echo', text="hi") == "Echo: hi"
    assert hug.test.get(api, 'echo', text="hi") == "Echo: hi"
