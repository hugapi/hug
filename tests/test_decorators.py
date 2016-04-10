"""tests/test_decorators.py.

Tests the decorators that power hugs core functionality

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
import os
import sys
from unittest import mock

import falcon
import pytest
from falcon.testing import StartResponseMock, create_environ

import hug

from .constants import BASE_DIRECTORY

api = hug.API(__name__)
module = sys.modules[__name__]

# Fix flake8 undefined names (F821)
__hug__ = __hug__  # noqa
__hug_wsgi__ = __hug_wsgi__  # noqa


def test_basic_call():
    """The most basic Happy-Path test for Hug APIs"""
    @hug.call()
    def hello_world():
        return "Hello World!"

    assert hello_world() == "Hello World!"
    assert hello_world.interface.http

    assert hug.test.get(api, '/hello_world').data == "Hello World!"
    assert hug.test.get(module, '/hello_world').data == "Hello World!"


def test_basic_call_on_method():
    """Test to ensure the most basic call still works if applied to a method"""
    class API(object):

        @hug.call()
        def hello_world(self=None):
            return "Hello World!"

    api_instance = API()
    assert api_instance.hello_world.interface.http
    assert api_instance.hello_world() == 'Hello World!'
    assert hug.test.get(api, '/hello_world').data == "Hello World!"

    class API(object):

        def hello_world(self):
            return "Hello World!"

    api_instance = API()

    @hug.call()
    def hello_world():
        return api_instance.hello_world()

    assert api_instance.hello_world() == 'Hello World!'
    assert hug.test.get(api, '/hello_world').data == "Hello World!"

    class API(object):

        def __init__(self):
            hug.call()(self.hello_world_method)

        def hello_world_method(self):
            return "Hello World!"

    api_instance = API()

    assert api_instance.hello_world_method() == 'Hello World!'
    assert hug.test.get(api, '/hello_world_method').data == "Hello World!"


def test_single_parameter():
    """Test that an api with a single parameter interacts as desired"""
    @hug.call()
    def echo(text):
        return text

    assert echo('Embrace') == 'Embrace'
    assert echo.interface.http
    with pytest.raises(TypeError):
        echo()

    assert hug.test.get(api, 'echo', text="Hello").data == "Hello"
    assert 'required' in hug.test.get(api, '/echo').data['errors']['text'].lower()


def test_on_invalid_transformer():
    """Test to ensure it is possible to transform data when data is invalid"""
    @hug.call(on_invalid=lambda data: 'error')
    def echo(text):
        return text
    assert hug.test.get(api, '/echo').data == 'error'


    def handle_error(data, request, response):
        return 'errored'

    @hug.call(on_invalid=handle_error)
    def echo2(text):
        return text
    assert hug.test.get(api, '/echo2').data == 'errored'


def test_on_invalid_format():
    """Test to ensure it's possible to change the format based on a validation error"""
    @hug.get(output_invalid=hug.output_format.json, output=hug.output_format.file)
    def echo(text):
        return text

    assert isinstance(hug.test.get(api, '/echo').data, dict)

    def smart_output_type(response, request):
        if response and request:
            return 'application/json'

    @hug.format.content_type(smart_output_type)
    def output_formatter(data, request, response):
        return hug.output_format.json((data, request and True, response and True))

    @hug.get(output_invalid=output_formatter, output=hug.output_format.file)
    def echo2(text):
        return text

    assert isinstance(hug.test.get(api, '/echo2').data, (list, tuple))


def test_smart_redirect_routing():
    """Test to ensure you can easily redirect to another method without an actual redirect"""
    @hug.get()
    def implementation_1():
        return 1

    @hug.get()
    def implementation_2():
        return 2

    @hug.get()
    def smart_route(implementation: int):
        if implementation == 1:
            return implementation_1
        elif implementation == 2:
            return implementation_2
        else:
            return "NOT IMPLEMENTED"

    assert hug.test.get(api, 'smart_route', implementation=1).data == 1
    assert hug.test.get(api, 'smart_route', implementation=2).data == 2
    assert hug.test.get(api, 'smart_route', implementation=3).data == "NOT IMPLEMENTED"


def test_custom_url():
    """Test to ensure that it's possible to have a route that differs from the function name"""
    @hug.call('/custom_route')
    def method_name():
        return 'works'

    assert hug.test.get(api, 'custom_route').data == 'works'


def test_api_auto_initiate():
    """Test to ensure that Hug automatically exposes a wsgi server method"""
    assert isinstance(__hug_wsgi__(create_environ('/non_existant'), StartResponseMock()), (list, tuple))


def test_parameters():
    """Tests to ensure that Hug can easily handle multiple parameters with multiple types"""
    @hug.call()
    def multiple_parameter_types(start, middle: hug.types.text, end: hug.types.number=5, **kwargs):
        return 'success'

    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end=7).data == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle').data == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', other="yo").data == 'success'

    nan_test = hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end='NAN').data
    assert 'Invalid' in nan_test['errors']['end']


def test_raise_on_invalid():
    """Test to ensure hug correctly respects a request to allow validations errors to pass through as exceptions"""
    @hug.get(raise_on_invalid=True)
    def my_handler(argument_1: int):
        return True

    with pytest.raises(Exception):
        hug.test.get(api, 'my_handler', argument_1='hi')

    assert hug.test.get(api, 'my_handler', argument_1=1)


def test_range_request():
    """Test to ensure that requesting a range works as expected"""
    @hug.get(output=hug.output_format.png_image)
    def image():
        return 'artwork/logo.png'

    assert hug.test.get(api, 'image', headers={'range': 'bytes=0-100'})
    assert hug.test.get(api, 'image', headers={'range': 'bytes=0--1'})

def test_parameters_override():
    """Test to ensure the parameters override is handled as expected"""
    @hug.get(parameters=('parameter1', 'parameter2'))
    def test_call(**kwargs):
        return kwargs

    assert hug.test.get(api, 'test_call', parameter1='one', parameter2='two').data == {'parameter1': 'one',
                                                                                       'parameter2': 'two'}


def test_parameter_injection():
    """Tests that hug correctly auto injects variables such as request and response"""
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
    """Test that all hugs HTTP routers correctly route methods to the correct handler"""
    @hug.get()
    def method_get():
        return 'GET'

    @hug.post()
    def method_post():
        return 'POST'

    @hug.connect()
    def method_connect():
        return 'CONNECT'

    @hug.delete()
    def method_delete():
        return 'DELETE'

    @hug.options()
    def method_options():
        return 'OPTIONS'

    @hug.put()
    def method_put():
        return 'PUT'

    @hug.trace()
    def method_trace():
        return 'TRACE'

    assert hug.test.get(api, 'method_get').data == 'GET'
    assert hug.test.post(api, 'method_post').data == 'POST'
    assert hug.test.connect(api, 'method_connect').data == 'CONNECT'
    assert hug.test.delete(api, 'method_delete').data == 'DELETE'
    assert hug.test.options(api, 'method_options').data == 'OPTIONS'
    assert hug.test.put(api, 'method_put').data == 'PUT'
    assert hug.test.trace(api, 'method_trace').data == 'TRACE'

    @hug.call(accept=('GET', 'POST'))
    def accepts_get_and_post():
        return 'success'

    assert hug.test.get(api, 'accepts_get_and_post').data == 'success'
    assert hug.test.post(api, 'accepts_get_and_post').data == 'success'
    assert 'method not allowed' in hug.test.trace(api, 'accepts_get_and_post').status.lower()


def test_not_found():
    """Test to ensure the not_found decorator correctly routes 404s to the correct handler"""
    @hug.not_found()
    def not_found_handler():
        return "Not Found"

    result = hug.test.get(api, '/does_not_exist/yet')
    assert result.data == "Not Found"
    assert result.status == falcon.HTTP_NOT_FOUND

    @hug.not_found(versions=10)  # noqa
    def not_found_handler(response):
        response.status = falcon.HTTP_OK
        return {'look': 'elsewhere'}

    result = hug.test.get(api, '/v10/does_not_exist/yet')
    assert result.data == {'look': 'elsewhere'}
    assert result.status == falcon.HTTP_OK

    result = hug.test.get(api, '/does_not_exist/yet')
    assert result.data == "Not Found"
    assert result.status == falcon.HTTP_NOT_FOUND


def test_versioning():
    """Ensure that Hug correctly routes API functions based on version"""
    @hug.get('/echo')
    def echo(text):
        return "Not Implemented"

    @hug.get('/echo', versions=1)  # noqa
    def echo(text):
        return text

    @hug.get('/echo', versions=range(2, 4))  # noqa
    def echo(text):
        return "Echo: {text}".format(**locals())

    @hug.get('/echo', versions=7)  # noqa
    def echo(text, api_version):
        return api_version

    assert hug.test.get(api, 'v1/echo', text="hi").data == 'hi'
    assert hug.test.get(api, 'v2/echo', text="hi").data == "Echo: hi"
    assert hug.test.get(api, 'v3/echo', text="hi").data == "Echo: hi"
    assert hug.test.get(api, 'echo', text="hi", api_version=3).data == "Echo: hi"
    assert hug.test.get(api, 'echo', text="hi", headers={'X-API-VERSION': '3'}).data == "Echo: hi"
    assert hug.test.get(api, 'v4/echo', text="hi").data == "Not Implemented"
    assert hug.test.get(api, 'v7/echo', text="hi").data == 7
    assert hug.test.get(api, 'echo', text="hi").data == "Not Implemented"
    assert hug.test.get(api, 'echo', text="hi", api_version=3, body={'api_vertion': 4}).data == "Echo: hi"

    with pytest.raises(ValueError):
        hug.test.get(api, 'v4/echo', text="hi", api_version=3)


def test_multiple_version_injection():
    """Test to ensure that the version injected sticks when calling other functions within an API"""
    @hug.get(versions=(1, 2, None))
    def my_api_function(hug_api_version):
        return hug_api_version

    assert hug.test.get(api, 'v1/my_api_function').data == 1
    assert hug.test.get(api, 'v2/my_api_function').data == 2
    assert hug.test.get(api, 'v3/my_api_function').data == 3

    @hug.get(versions=(None, 1))
    @hug.local(version=1)
    def call_other_function(hug_current_api):
        return hug_current_api.my_api_function()

    assert hug.test.get(api, 'v1/call_other_function').data == 1
    assert call_other_function() == 1

    @hug.get(versions=1)
    @hug.local(version=1)
    def one_more_level_of_indirection(hug_current_api):
        return hug_current_api.call_other_function()

    assert hug.test.get(api, 'v1/one_more_level_of_indirection').data == 1
    assert one_more_level_of_indirection() == 1


def test_json_auto_convert():
    """Test to ensure all types of data correctly auto convert into json"""
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
    assert hug.test.get(api, 'test_json_body_stream_only', body=['value1', 'value2']).data is None


def test_error_handling():
    """Test to ensure Hug correctly handles Falcon errors that are thrown during processing"""
    @hug.get()
    def test_error():
        raise falcon.HTTPInternalServerError('Failed', 'For Science!')

    response = hug.test.get(api, 'test_error')
    assert 'errors' in response.data
    assert response.data['errors']['Failed'] == 'For Science!'


def test_error_handling_builtin_exception():
    """Test to ensure built in exception types errors are handled as expected"""
    def raise_error(value):
        raise KeyError('Invalid value')

    @hug.get()
    def test_error(data: raise_error):
        return True

    response = hug.test.get(api, 'test_error', data=1)
    assert 'errors' in response.data
    assert response.data['errors']['data'] == 'Invalid value'


def test_error_handling_custom():
    """Test to ensure custom exceptions work as expected"""
    class Error(Exception):

        def __str__(self):
            return 'Error'

    def raise_error(value):
        raise Error()

    @hug.get()
    def test_error(data: raise_error):
        return True

    response = hug.test.get(api, 'test_error', data=1)
    assert 'errors' in response.data
    assert response.data['errors']['data'] == 'Error'


def test_return_modifer():
    """Ensures you can modify the output of a HUG API using -> annotation"""
    @hug.get()
    def hello() -> lambda data: "Hello {0}!".format(data):
        return "world"

    assert hug.test.get(api, 'hello').data == "Hello world!"
    assert hello() == 'world'

    @hug.get(transform=lambda data: "Goodbye {0}!".format(data))
    def hello() -> lambda data: "Hello {0}!".format(data):
        return "world"
    assert hug.test.get(api, 'hello').data == "Goodbye world!"
    assert hello() == 'world'

    @hug.get()
    def hello() -> str:
        return "world"
    assert hug.test.get(api, 'hello').data == "world"
    assert hello() == 'world'

    @hug.get(transform=False)
    def hello() -> lambda data: "Hello {0}!".format(data):
        return "world"

    assert hug.test.get(api, 'hello').data == "world"
    assert hello() == 'world'

    def transform_with_request_data(data, request, response):
        return (data, request and True, response and True)

    @hug.get(transform=transform_with_request_data)
    def hello():
        return "world"

    response = hug.test.get(api, 'hello')
    assert response.data == ['world', True, True]


def test_marshmallow_support():
    """Ensure that you can use Marshmallow style objects to control input and output validation and transformation"""
    class MarshmallowStyleObject(object):
        def dump(self, item):
            return 'Dump Success'

        def load(self, item):
            return ('Load Success', None)

        def loads(self, item):
            return self.load(item)

    schema = MarshmallowStyleObject()

    @hug.get()
    def test_marshmallow_style() -> schema:
        return "world"

    assert hug.test.get(api, 'test_marshmallow_style').data == "Dump Success"
    assert test_marshmallow_style() == 'world'


    @hug.get()
    def test_marshmallow_input(item: schema):
        return item

    assert hug.test.get(api, 'test_marshmallow_input', item='bacon').data == "Load Success"
    assert test_marshmallow_style() == 'world'

    class MarshmallowStyleObjectWithError(object):
        def dump(self, item):
            return 'Dump Success'

        def load(self, item):
            return ('Load Success', {'type': 'invalid'})

        def loads(self, item):
            return self.load(item)

    schema = MarshmallowStyleObjectWithError()

    @hug.get()
    def test_marshmallow_input2(item: schema):
        return item

    assert hug.test.get(api, 'test_marshmallow_input2', item='bacon').data == {'errors': {'item': {'type': 'invalid'}}}

    class MarshmallowStyleField(object):
        def deserialize(self, value):
            return str(value)

    @hug.get()
    def test_marshmallow_input_field(item: MarshmallowStyleField()):
        return item

    assert hug.test.get(api, 'test_marshmallow_input_field', item='bacon').data == 'bacon'


def test_stream_return():
    """Test to ensure that its valid for a hug API endpoint to return a stream"""
    @hug.get(output=hug.output_format.text)
    def test():
        return open(os.path.join(BASE_DIRECTORY, 'README.md'), 'rb')

    assert 'hug' in hug.test.get(api, 'test').data


def test_smart_outputter():
    """Test to ensure that the output formatter can accept request and response arguments"""
    def smart_output_type(response, request):
        if response and request:
            return 'application/json'

    @hug.format.content_type(smart_output_type)
    def output_formatter(data, request, response):
        return hug.output_format.json((data, request and True, response and True))

    @hug.get(output=output_formatter)
    def test():
        return True

    assert hug.test.get(api, 'test').data == [True, True, True]


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_output_format():
    """Test to ensure it's possible to quickly change the default hug output format"""
    old_formatter = api.http.output_format

    @hug.default_output_format()
    def augmented(data):
        return hug.output_format.json(['Augmented', data])

    @hug.get(suffixes=('.js', '/js'), prefixes='/text')
    def hello():
        return "world"

    assert hug.test.get(api, 'hello').data == ['Augmented', 'world']
    assert hug.test.get(api, 'hello.js').data == ['Augmented', 'world']
    assert hug.test.get(api, 'hello/js').data == ['Augmented', 'world']
    assert hug.test.get(api, 'text/hello').data == ['Augmented', 'world']

    @hug.default_output_format()
    def jsonify(data):
        return hug.output_format.json(data)


    api.http.output_format = hug.output_format.text

    @hug.get()
    def my_method():
        return {'Should': 'work'}

    assert hug.test.get(api, 'my_method').data == "{'Should': 'work'}"
    api.http.output_format = old_formatter


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_input_format():
    """Test to ensure it's possible to quickly change the default hug output format"""
    old_format = api.http.input_format('application/json')
    api.http.set_input_format('application/json', lambda a: {'no': 'relation'})

    @hug.get()
    def hello(body):
        return body

    assert hug.test.get(api, 'hello', body={'should': 'work'}).data == {'no': 'relation'}

    @hug.get()
    def hello2(body):
        return body

    assert not hug.test.get(api, 'hello2').data

    api.http.set_input_format('application/json', old_format)


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_content_type_with_parameter():
    """Test a Content-Type with parameter as `application/json charset=UTF-8`
    as described in https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7"""
    @hug.get()
    def demo(body):
        return body

    assert hug.test.get(api, 'demo', body={}, headers={'content-type': 'application/json'}).data == {}
    assert hug.test.get(api, 'demo', body={}, headers={'content-type': 'application/json; charset=UTF-8'}).data == {}


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_middleware():
    """Test to ensure the basic concept of a middleware works as expected"""
    @hug.request_middleware()
    def proccess_data(request, response):
        request.env['SERVER_NAME'] = 'Bacon'

    @hug.response_middleware()
    def proccess_data2(request, response, resource):
        response.set_header('Bacon', 'Yumm')

    @hug.get()
    def hello(request):
        return request.env['SERVER_NAME']

    result = hug.test.get(api, 'hello')
    assert result.data == 'Bacon'
    assert result.headers_dict['Bacon'] == 'Yumm'


def test_requires():
    """Test to ensure only if requirements successfully keep calls from happening"""
    def user_is_not_tim(request, response, **kwargs):
        if request.headers.get('USER', '') != 'Tim':
            return True
        return 'Unauthorized'

    @hug.get(requires=user_is_not_tim)
    def hello(request):
        return 'Hi!'

    assert hug.test.get(api, 'hello').data == 'Hi!'
    assert hug.test.get(api, 'hello', headers={'USER': 'Tim'}).data == 'Unauthorized'


def test_extending_api():
    """Test to ensure it's possible to extend the current API from an external file"""
    @hug.extend_api('/fake')
    def extend_with():
        import tests.module_fake
        return (tests.module_fake, )

    assert hug.test.get(api, 'fake/made_up_api').data


def test_extending_api_simple():
    """Test to ensure it's possible to extend the current API from an external file with just one API endpoint"""
    @hug.extend_api('/fake_simple')
    def extend_with():
        import tests.module_fake_simple
        return (tests.module_fake_simple, )

    assert hug.test.get(api, 'fake_simple/made_up_hello').data == 'hello'


def test_cli():
    """Test to ensure the CLI wrapper works as intended"""
    @hug.cli('command', '1.0.0', output=str)
    def cli_command(name: str, value: int):
        return (name, value)

    assert cli_command('Testing', 1) == ('Testing', 1)
    assert hug.test.cli(cli_command, "Bob", 5) == ("Bob", 5)


def test_cli_requires():
    """Test to ensure your can add requirements to a CLI"""
    def requires_fail(**kwargs):
        return {'requirements': 'not met'}

    @hug.cli(output=str, requires=requires_fail)
    def cli_command(name: str, value: int):
        return (name, value)

    assert cli_command('Testing', 1) == ('Testing', 1)
    assert hug.test.cli(cli_command, 'Testing', 1) == {'requirements': 'not met'}


def test_cli_validation():
    """Test to ensure your can add custom validation to a CLI"""
    def contains_either(fields):
        if not fields.get('name', '') and not fields.get('value', 0):
            return {'name': 'must be defined', 'value': 'must be defined'}

    @hug.cli(output=str, validate=contains_either)
    def cli_command(name: str="", value: int=0):
        return (name, value)

    assert cli_command('Testing', 1) == ('Testing', 1)
    assert hug.test.cli(cli_command) == {'name': 'must be defined', 'value': 'must be defined'}
    assert hug.test.cli(cli_command, name='Testing') == ('Testing', 0)


def test_cli_with_defaults():
    """Test to ensure CLIs work correctly with default values"""
    @hug.cli()
    def happy(name: str, age: int, birthday: bool=False):
        if birthday:
            return "Happy {age} birthday {name}!".format(**locals())
        else:
            return "{name} is {age} years old".format(**locals())

    assert happy('Hug', 1) == "Hug is 1 years old"
    assert happy('Hug', 1, True) == "Happy 1 birthday Hug!"
    assert hug.test.cli(happy, "Bob", 5) == "Bob is 5 years old"
    assert hug.test.cli(happy, "Bob", 5, birthday=True) == "Happy 5 birthday Bob!"


def test_cli_with_hug_types():
    """Test to ensure CLIs work as expected when using hug types"""
    @hug.cli()
    def happy(name: hug.types.text, age: hug.types.number, birthday: hug.types.boolean=False):
        if birthday:
            return "Happy {age} birthday {name}!".format(**locals())
        else:
            return "{name} is {age} years old".format(**locals())

    assert happy('Hug', 1) == "Hug is 1 years old"
    assert happy('Hug', 1, True) == "Happy 1 birthday Hug!"
    assert hug.test.cli(happy, "Bob", 5) == "Bob is 5 years old"
    assert hug.test.cli(happy, "Bob", 5, birthday=True) == "Happy 5 birthday Bob!"

    @hug.cli()
    def succeed(success: hug.types.smart_boolean=False):
        if success:
            return 'Yes!'
        else:
            return 'No :('

    assert hug.test.cli(succeed) == 'No :('
    assert hug.test.cli(succeed, success=True) == 'Yes!'
    assert 'succeed' in str(__hug__.cli)

    @hug.cli()
    def succeed(success: hug.types.smart_boolean=True):
        if success:
            return 'Yes!'
        else:
            return 'No :('

    assert hug.test.cli(succeed) == 'Yes!'
    assert hug.test.cli(succeed, success='false') == 'No :('

    @hug.cli()
    def all_the(types: hug.types.multiple=[]):
        return types or ['nothing_here']

    assert hug.test.cli(all_the) == ['nothing_here']
    assert hug.test.cli(all_the, types=('one', 'two', 'three')) == ['one', 'two', 'three']

    @hug.cli()
    def all_the(types: hug.types.multiple):
        return types or ['nothing_here']

    assert hug.test.cli(all_the) == ['nothing_here']
    assert hug.test.cli(all_the, 'one', 'two', 'three') == ['one', 'two', 'three']

    @hug.cli()
    def one_of(value: hug.types.one_of(['one', 'two'])='one'):
        return value

    assert hug.test.cli(one_of, value='one') == 'one'
    assert hug.test.cli(one_of, value='two') == 'two'


def test_cli_with_conflicting_short_options():
    """Test to ensure that it's possible to expose a CLI with the same first few letters in option"""
    @hug.cli()
    def test(abe1="Value", abe2="Value2", helper=None):
        return (abe1, abe2)

    assert test() == ('Value', 'Value2')
    assert test('hi', 'there') == ('hi', 'there')
    assert hug.test.cli(test) == ('Value', 'Value2')
    assert hug.test.cli(test, abe1='hi', abe2='there') == ('hi', 'there')


def test_cli_with_directives():
    """Test to ensure it's possible to use directives with hug CLIs"""
    @hug.cli()
    @hug.local()
    def test(hug_timer):
        return float(hug_timer)

    assert isinstance(test(), float)
    assert test(hug_timer=4) == 4
    assert isinstance(hug.test.cli(test), float)


def test_cli_with_named_directives():
    """Test to ensure you can pass named directives into the cli"""
    @hug.cli()
    @hug.local()
    def test(timer: hug.directives.Timer):
        return float(timer)

    assert isinstance(test(), float)
    assert test(timer=4) == 4
    assert isinstance(hug.test.cli(test), float)


def test_cli_with_output_transform():
    """Test to ensure it's possible to use output transforms with hug CLIs"""
    @hug.cli()
    def test() -> int:
        return '5'

    assert isinstance(test(), str)
    assert isinstance(hug.test.cli(test), int)


    @hug.cli(transform=int)
    def test():
        return '5'

    assert isinstance(test(), str)
    assert isinstance(hug.test.cli(test), int)


def test_cli_with_short_short_options():
    """Test to ensure that it's possible to expose a CLI with 2 very short and similar options"""
    @hug.cli()
    def test(a1="Value", a2="Value2"):
        return (a1, a2)

    assert test() == ('Value', 'Value2')
    assert test('hi', 'there') == ('hi', 'there')
    assert hug.test.cli(test) == ('Value', 'Value2')
    assert hug.test.cli(test, a1='hi', a2='there') == ('hi', 'there')


def test_cli_file_return():
    """Test to ensure that its possible to return a file stream from a CLI"""
    @hug.cli()
    def test():
        return open(os.path.join(BASE_DIRECTORY, 'README.md'), 'rb')

    assert 'hug' in hug.test.cli(test)


def test_local_type_annotation():
    """Test to ensure local type annotation works as expected"""
    @hug.local(raise_on_invalid=True)
    def test(number: int):
        return number

    assert test(3) == 3
    with pytest.raises(Exception):
        test('h')

    @hug.local(raise_on_invalid=False)
    def test(number: int):
        return number

    assert test('h')['errors']

    @hug.local(raise_on_invalid=False, validate=False)
    def test(number: int):
        return number

    assert test('h') == 'h'


def test_local_transform():
    """Test to ensure local type annotation works as expected"""
    @hug.local(transform=str)
    def test(number: int):
        return number

    assert test(3) == '3'


def test_local_on_invalid():
    """Test to ensure local type annotation works as expected"""
    @hug.local(on_invalid=str)
    def test(number: int):
        return number

    assert isinstance(test('h'), str)


def test_local_requires():
    """Test to ensure only if requirements successfully keep calls from happening locally"""
    global_state = False

    def requirement(**kwargs):
        return global_state and 'Unauthorized'

    @hug.local(requires=requirement)
    def hello():
        return 'Hi!'

    assert hello() == 'Hi!'
    global_state = True
    assert hello() == 'Unauthorized'


def test_static_file_support():
    """Test to ensure static file routing works as expected"""
    @hug.static('/static')
    def my_static_dirs():
        return (BASE_DIRECTORY, )

    assert 'hug' in hug.test.get(api, '/static/README.md').data
    assert 'Index' in hug.test.get(api, '/static/tests/data').data
    assert '404' in hug.test.get(api, '/static/NOT_IN_EXISTANCE.md').status


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_sink_support():
    """Test to ensure sink URL routers work as expected"""
    @hug.sink('/all')
    def my_sink(request):
        return request.path.replace('/all', '')

    assert hug.test.get(api, '/all/the/things').data == '/the/things'


def test_cli_with_string_annotation():
    """Test to ensure CLI's work correctly with string annotations"""
    @hug.cli()
    def test(value_1: 'The first value', value_2: 'The second value'=None):
        return True

    assert hug.test.cli(test, True)


def test_cli_with_kargs():
    """Test to ensure CLI's work correctly when taking kargs"""
    @hug.cli()
    def test(*values):
        return values

    assert test(1, 2, 3) == (1, 2, 3)
    assert hug.test.cli(test, 1, 2, 3) == ('1', '2', '3')


def test_cli_using_method():
    """Test to ensure that attaching a cli to a class method works as expected"""
    class API(object):

        def __init__(self):
            hug.cli()(self.hello_world_method)

        def hello_world_method(self):
            variable = 'Hello World!'
            return variable

    api_instance = API()
    assert api_instance.hello_world_method() == 'Hello World!'
    assert hug.test.cli(api_instance.hello_world_method) == 'Hello World!'
    assert hug.test.cli(api_instance.hello_world_method, collect_output=False) is None


def test_cli_with_nested_variables():
    """Test to ensure that a cli containing multiple nested variables works correctly"""
    @hug.cli()
    def test(value_1=None, value_2=None):
        return 'Hi!'

    assert hug.test.cli(test) == 'Hi!'


def test_cli_with_exception():
    """Test to ensure that a cli with an exception is correctly handled"""
    @hug.cli()
    def test():
        raise ValueError()
        return 'Hi!'

    assert hug.test.cli(test) != 'Hi!'


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_wraps():
    """Test to ensure you can safely apply decorators to hug endpoints by using @hug.wraps"""
    def my_decorator(function):
        @hug.wraps(function)
        def decorated(*kargs, **kwargs):
            kwargs['name'] = 'Timothy'
            return function(*kargs, **kwargs)
        return decorated

    @hug.get()
    @my_decorator
    def what_is_my_name(hug_timer=None, name="Sam"):
        return {'name': name, 'took': hug_timer}

    result = hug.test.get(api, 'what_is_my_name').data
    assert result['name'] == 'Timothy'
    assert result['took']

    def my_second_decorator(function):
        @hug.wraps(function)
        def decorated(*kargs, **kwargs):
            kwargs['name'] = "Not telling"
            return function(*kargs, **kwargs)
        return decorated

    @hug.get()
    @my_decorator
    @my_second_decorator
    def what_is_my_name2(hug_timer=None, name="Sam"):
        return {'name': name, 'took': hug_timer}

    result = hug.test.get(api, 'what_is_my_name2').data
    assert result['name'] == "Not telling"
    assert result['took']



def test_cli_with_empty_return():
    """Test to ensure that if you return None no data will be added to sys.stdout"""
    @hug.cli()
    def test_empty_return():
        pass

    assert not hug.test.cli(test_empty_return)


def test_startup():
    """Test to ensure hug startup decorators work as expected"""
    @hug.startup()
    def happens_on_startup(api):
        pass

    assert happens_on_startup in api.http.startup_handlers


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_adding_headers():
    """Test to ensure it is possible to inject response headers based on only the URL route"""
    @hug.get(response_headers={'name': 'Timothy'})
    def endpoint():
        return ''

    result = hug.test.get(api, 'endpoint')
    assert result.data == ''
    assert result.headers_dict['name'] == 'Timothy'


def test_on_demand_404():
    """Test to ensure it's possible to route to a 404 response on demand"""
    @hug.get()
    def my_endpoint(hug_api):
        return hug_api.http.not_found

    assert '404' in hug.test.get(api, 'my_endpoint').status


    @hug.get()
    def my_endpoint2(hug_api):
        raise hug.HTTPNotFound()

    assert '404' in hug.test.get(api, 'my_endpoint2').status

    @hug.get()
    def my_endpoint3(hug_api):
        """Test to ensure base 404 handler works as expected"""
        del hug_api.http._not_found
        return hug_api.http.not_found

    assert '404' in hug.test.get(api, 'my_endpoint3').status


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_exceptions():
    """Test to ensure hug's exception handling decorator works as expected"""
    @hug.get()
    def endpoint():
        raise ValueError('hi')

    with pytest.raises(ValueError):
        hug.test.get(api, 'endpoint')

    @hug.exception()
    def handle_exception(exception):
        return 'it worked'

    assert hug.test.get(api, 'endpoint').data == 'it worked'

    @hug.exception(ValueError)  # noqa
    def handle_exception(exception):
        return 'more explicit handler also worked'

    assert hug.test.get(api, 'endpoint').data == 'more explicit handler also worked'


@pytest.mark.skipif(sys.platform == 'win32', reason='Currently failing on Windows build')
def test_validate():
    """Test to ensure hug's secondary validation mechanism works as expected"""
    def contains_either(fields):
        if not 'one' in fields and not 'two' in fields:
            return {'one': 'must be defined', 'two': 'must be defined'}

    @hug.get(validate=contains_either)
    def my_endpoint(one=None, two=None):
        return True


    assert hug.test.get(api, 'my_endpoint', one=True).data
    assert hug.test.get(api, 'my_endpoint', two=True).data
    assert hug.test.get(api, 'my_endpoint').status
    assert hug.test.get(api, 'my_endpoint').data == {'errors': {'one': 'must be defined', 'two': 'must be defined'}}


def test_cli_api(capsys):
    """Ensure that the overall CLI Interface API works as expected"""
    @hug.cli()
    def my_cli_command():
        print("Success!")

    with mock.patch('sys.argv', ['/bin/command', 'my_cli_command']):
        __hug__.cli()
        out, err = capsys.readouterr()
        assert "Success!" in out

    with mock.patch('sys.argv', []):
        with pytest.raises(SystemExit):
            __hug__.cli()


def test_cli_api_return():
    """Ensure returning from a CLI API works as expected"""
    @hug.cli()
    def my_cli_command():
        return "Success!"

    my_cli_command.interface.cli()
