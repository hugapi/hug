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

    assert hug.test.get(api, '/hello_world').data == "Hello World!"


def test_single_parameter():
    @hug.call()
    def echo(text):
        return text

    assert echo('Embrace') == 'Embrace'
    assert echo.interface
    with pytest.raises(TypeError):
        echo()

    assert hug.test.get(api, 'echo', text="Hello").data == "Hello"
    assert 'required' in hug.test.get(api, '/echo').data['errors']['text'].lower()


def test_custom_url():
    @hug.call('/custom_route')
    def method_name():
        return 'works'

    assert hug.test.get(api, 'custom_route').data == 'works'


def test_api_auto_initiate():
    assert isinstance(__hug_wsgi__(create_environ('/non_existant'), StartResponseMock()), (list, tuple))


def test_parameters():
    @hug.call()
    def multiple_parameter_types(start, middle:hug.types.text, end:hug.types.number=5, **kwargs):
        return 'success'

    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end=7).data == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle').data == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', other="yo").data == 'success'

    nan_test = hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end='NAN').data
    assert 'invalid' in nan_test['errors']['end']


def test_parameter_injection():
    @hug.call()
    def inject_request(request):
        return request and 'success'
    assert hug.test.get(api, 'inject_request').data == 'success'

    @hug.call()
    def inject_response(response):
        return response and 'success'
    assert hug.test.get(api, 'inject_response').data == 'success'

    @hug.call()
    def inject_both(request, response):
        return request and response and 'success'
    assert hug.test.get(api, 'inject_both').data == 'success'

    @hug.call()
    def wont_appear_in_kwargs(**kwargs):
        return 'request' not in kwargs and 'response' not in kwargs and 'success'
    assert hug.test.get(api, 'wont_appear_in_kwargs').data == 'success'


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

    assert hug.test.get(api, 'method').data == 'GET'
    assert hug.test.post(api, 'method').data == 'POST'
    assert hug.test.connect(api, 'method').data == 'CONNECT'
    assert hug.test.delete(api, 'method').data == 'DELETE'
    assert hug.test.options(api, 'method').data == 'OPTIONS'
    assert hug.test.put(api, 'method').data == 'PUT'
    assert hug.test.trace(api, 'method').data == 'TRACE'

    @hug.call(accept=('GET', 'POST'))
    def accepts_get_and_post():
        return 'success'

    assert hug.test.get(api, 'accepts_get_and_post').data == 'success'
    assert hug.test.post(api, 'accepts_get_and_post').data == 'success'
    assert 'method not allowed' in hug.test.trace(api, 'accepts_get_and_post').status.lower()


def test_versioning():
    @hug.get('/echo')
    def echo(text):
        return "Not Implemented"

    @hug.get('/echo', versions=1)
    def echo(text):
        return text

    @hug.get('/echo', versions=range(2, 4))
    def echo(text):
        return "Echo: {text}".format(**locals())

    assert hug.test.get(api, 'v1/echo', text="hi").data == 'hi'
    assert hug.test.get(api, 'v2/echo', text="hi").data == "Echo: hi"
    assert hug.test.get(api, 'v3/echo', text="hi").data == "Echo: hi"
    assert hug.test.get(api, 'echo', text="hi", api_version=3).data == "Echo: hi"
    assert hug.test.get(api, 'echo', text="hi", headers={'X-API-VERSION': '3'}).data == "Echo: hi"
    assert hug.test.get(api, 'v4/echo', text="hi").data == "Not Implemented"
    assert hug.test.get(api, 'echo', text="hi").data == "Not Implemented"
    assert hug.test.get(api, 'echo', text="hi", api_version=3, body={'api_vertion': 4}).data == "Echo: hi"

    with pytest.raises(ValueError):
        hug.test.get(api, 'v4/echo', text="hi", api_version=3)


def test_multiple_version_injection():
    @hug.get(versions=(1, 2, None))
    def my_api_function(hug_api_version):
        return hug_api_version

    assert hug.test.get(api, 'v1/my_api_function').data == 1
    assert hug.test.get(api, 'v2/my_api_function').data == 2
    assert hug.test.get(api, 'v3/my_api_function').data == 3

    @hug.get(versions=(None, 1))
    def call_other_function(hug_current_api):
        return hug_current_api.my_api_function()

    assert hug.test.get(api, 'v1/call_other_function').data == 1
    assert call_other_function() == 1

    @hug.get(versions=1)
    def one_more_level_of_indirection(hug_current_api):
        return hug_current_api.call_other_function()

    assert hug.test.get(api, 'v1/one_more_level_of_indirection').data == 1
    assert one_more_level_of_indirection() == 1


def test_json_auto_convert():
    @hug.get('/test_json')
    def test_json(text):
        return text
    assert hug.test.get(api, 'test_json', body={'text': 'value'}).data == "value"

    @hug.get('/test_json_body')
    def test_json_body(body):
        return body
    assert hug.test.get(api, 'test_json_body', body=['value1', 'value2']).data == ['value1', 'value2']

    @hug.get(parse_body=False)
    def test_json_body_stream_only(body=None):
        return body
    assert hug.test.get(api, 'test_json_body_stream_only', body=['value1', 'value2']).data == None


def test_output_format():
    @hug.default_output_format()
    def augmented(data):
        return hug.output_format.json(['Augmented', data])

    @hug.get()
    def hello():
        return "world"

    assert hug.test.get(api, 'hello').data == ['Augmented', 'world']

