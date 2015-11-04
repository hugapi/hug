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
import sys

import falcon
import pytest
from falcon.testing import StartResponseMock, create_environ

import hug

api = sys.modules[__name__]


def test_basic_call():
    '''The most basic Happy-Path test for Hug APIs'''
    @hug.call()
    def hello_world():
        return "Hello World!"

    assert hello_world() == "Hello World!"
    assert hello_world.interface

    assert hug.test.get(api, '/hello_world').data == "Hello World!"


def test_basic_call_on_method():
    '''Test to ensure the most basic call still works if applied to a method'''
    class API(object):

        @hug.call()
        def hello_world(self=None):
            return "Hello World!"

    api_instance = API()
    assert api_instance.hello_world.interface
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
    '''Test that an api with a single parameter interacts as desired'''
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
    '''Test to ensure that it's possible to have a route that differs from the function name'''
    @hug.call('/custom_route')
    def method_name():
        return 'works'

    assert hug.test.get(api, 'custom_route').data == 'works'


def test_api_auto_initiate():
    '''Test to ensure that Hug automatically exposes a wsgi server method'''
    assert isinstance(__hug_wsgi__(create_environ('/non_existant'), StartResponseMock()), (list, tuple))


def test_parameters():
    '''Tests to ensure that Hug can easily handle multiple parameters with multiple types'''
    @hug.call()
    def multiple_parameter_types(start, middle:hug.types.text, end:hug.types.number=5, **kwargs):
        return 'success'

    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end=7).data == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle').data == 'success'
    assert hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', other="yo").data == 'success'

    nan_test = hug.test.get(api, 'multiple_parameter_types', start='start', middle='middle', end='NAN').data
    assert 'Invalid' in nan_test['errors']['end']


def test_parameters_override():
    '''Test to ensure the parameters override is handled as expected'''
    @hug.get(parameters=('parameter1', 'parameter2'))
    def test_call(**kwargs):
        return kwargs

    assert hug.test.get(api, 'test_call', parameter1='one', parameter2='two').data == {'parameter1': 'one',
                                                                                       'parameter2': 'two'}


def test_parameter_injection():
    '''Tests that hug correctly auto injects variables such as request and response'''
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
    '''Test that all hugs HTTP routers correctly route methods to the correct handler'''
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


def test_not_found():
    '''Test to ensure the not_found decorator correctly routes 404s to the correct handler'''
    @hug.not_found()
    def not_found_handler():
        return "Not Found"

    result = hug.test.get(api, '/does_not_exist/yet')
    assert result.data == "Not Found"
    assert result.status == falcon.HTTP_NOT_FOUND

    @hug.not_found(versions=10)
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
    '''Ensure that Hug correctly routes API functions based on version'''
    @hug.get('/echo')
    def echo(text):
        return "Not Implemented"

    @hug.get('/echo', versions=1)
    def echo(text):
        return text

    @hug.get('/echo', versions=range(2, 4))
    def echo(text):
        return "Echo: {text}".format(**locals())

    @hug.get('/echo', versions=7)
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
    '''Test to ensure that the version injected sticks when calling other functions within an API'''
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
    '''Test to ensure all types of data correctly auto convert into json'''
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


def test_error_handling():
    '''Test to ensure Hug correctly handles Falcon errors that are thrown during processing'''
    @hug.get()
    def test_error():
        raise falcon.HTTPInternalServerError('Failed', 'For Science!')

    response = hug.test.get(api, 'test_error')
    assert 'errors' in response.data
    assert response.data['errors']['Failed'] == 'For Science!'


def test_return_modifer():
    '''Ensures you can modify the output of a HUG API using -> annotation'''
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
    '''Ensure that you can use Marshmallow style objects to control input and output validation and transformation'''
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
    def test_marshmallow_input(item:schema):
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
    def test_marshmallow_input(item:schema):
        return item

    assert hug.test.get(api, 'test_marshmallow_input', item='bacon').data == {'errors': {'item': {'type': 'invalid'}}}

    class MarshmallowStyleField(object):
        def deserialize(self, value):
            return str(value)

    @hug.get()
    def test_marshmallow_input_field(item:MarshmallowStyleField()):
        return item

    assert hug.test.get(api, 'test_marshmallow_input_field', item='bacon').data == 'bacon'


def test_stream_return():
    '''Test to ensure that its valid for a hug API endpoint to return a stream'''
    @hug.get(output=hug.output_format.text)
    def test():
        return open('README.md', 'rb')

    assert 'hug' in hug.test.get(api, 'test').data


def test_output_format():
    '''Test to ensure it's possible to quickly change the default hug output format'''
    old_formatter = api.__hug__.output_format

    @hug.default_output_format()
    def augmented(data):
        return hug.output_format.json(['Augmented', data])

    @hug.get()
    def hello():
        return "world"

    assert hug.test.get(api, 'hello').data == ['Augmented', 'world']

    @hug.default_output_format()
    def jsonify(data):
        return hug.output_format.json(data)


    api.__hug__.output_format = hug.output_format.text

    @hug.get()
    def my_method():
        return {'Should': 'work'}

    assert hug.test.get(api, 'my_method').data == "{'Should': 'work'}"
    api.__hug__.output_format = old_formatter


def test_input_format():
    '''Test to ensure it's possible to quickly change the default hug output format'''
    old_format = api.__hug__.input_format('application/json')
    api.__hug__.set_input_format('application/json', lambda a: {'no': 'relation'})

    @hug.get()
    def hello(body):
        return body

    assert hug.test.get(api, 'hello', body={'should': 'work'}).data == {'no': 'relation'}
    api.__hug__.set_input_format('application/json', old_format)


def test_middleware():
    '''Test to ensure the basic concept of a middleware works as expected'''
    @hug.request_middleware()
    def proccess_data(request, response):
        request.env['SERVER_NAME'] = 'Bacon'

    @hug.response_middleware()
    def proccess_data(request, response, resource):
        response.set_header('Bacon', 'Yumm')

    @hug.get()
    def hello(request):
        return request.env['SERVER_NAME']

    result = hug.test.get(api, 'hello')
    assert result.data == 'Bacon'
    assert result.headers_dict['Bacon'] == 'Yumm'


def test_requires():
    '''Test to ensure only if requirements successfully keep calls from happening'''
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
    '''Test to ensure it's possible to extend the current API from an external file'''
    @hug.extend_api('/fake')
    def extend_with():
        import tests.module_fake
        return (tests.module_fake, )

    assert hug.test.get(api, 'fake/made_up_api').data == True


def test_extending_api_simple():
    '''Test to ensure it's possible to extend the current API from an external file with just one API endpoint'''
    @hug.extend_api('/fake_simple')
    def extend_with():
        import tests.module_fake_simple
        return (tests.module_fake_simple, )

    assert hug.test.get(api, 'fake_simple/made_up_hello').data == 'hello'


def test_cli():
    '''Test to ensure the CLI wrapper works as intended'''
    @hug.cli('command', '1.0.0', output=str)
    def cli_command(name:str, value:int):
        return (name, value)

    assert cli_command('Testing', 1) == ('Testing', 1)
    assert hug.test.cli(cli_command, name="Bob", value=5) == ("Bob", 5)


def test_cli_with_defaults():
    '''Test to ensure CLIs work correctly with default values'''
    @hug.cli()
    def happy(name:str, age:int, birthday:bool=False):
        if birthday:
            return "Happy {age} birthday {name}!".format(**locals())
        else:
            return "{name} is {age} years old".format(**locals())

    assert happy('Hug', 1) == "Hug is 1 years old"
    assert happy('Hug', 1, True) == "Happy 1 birthday Hug!"
    assert hug.test.cli(happy, name="Bob", age=5) ==  "Bob is 5 years old"
    assert hug.test.cli(happy, name="Bob", age=5, birthday=True) ==  "Happy 5 birthday Bob!"


def test_cli_with_conflicting_short_options():
    '''Test to ensure that it's possible to expose a CLI with the same first few letters in option'''
    @hug.cli()
    def test(abe1="Value", abe2="Value2"):
        return (abe1, abe2)

    assert test() == ('Value', 'Value2')
    assert test('hi', 'there') == ('hi', 'there')
    assert hug.test.cli(test) == ('Value', 'Value2')
    assert hug.test.cli(test, abe1='hi', abe2='there') == ('hi', 'there')


def test_cli_with_directives():
    '''Test to ensure it's possible to use directives with hug CLIs'''
    @hug.cli()
    def test(hug_timer):
        return float(hug_timer)

    assert isinstance(test(), float)
    assert test(hug_timer=4) == 4
    assert isinstance(hug.test.cli(test), float)


def test_cli_with_named_directives():
    '''Test to ensure you can pass named directives into the cli'''
    @hug.cli()
    def test(timer:hug.directives.Timer):
        return float(timer)

    assert isinstance(test(), float)
    assert test(timer=4) == 4
    assert isinstance(hug.test.cli(test), float)


def test_cli_with_output_transform():
    '''Test to ensure it's possible to use output transforms with hug CLIs'''
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
    '''Test to ensure that it's possible to expose a CLI with 2 very short and similar options'''
    @hug.cli()
    def test(a1="Value", a2="Value2"):
        return (a1, a2)

    assert test() == ('Value', 'Value2')
    assert test('hi', 'there') == ('hi', 'there')
    assert hug.test.cli(test) == ('Value', 'Value2')
    assert hug.test.cli(test, a1='hi', a2='there') == ('hi', 'there')


def test_cli_file_return():
    '''Test to ensure that its possible to return a file stream from a CLI'''
    @hug.cli()
    def test():
        return open('README.md', 'rb')

    assert 'hug' in hug.test.cli(test)


def test_cli_with_string_annotation():
    '''Test to ensure CLI's work correctly with string annotations'''
    @hug.cli()
    def test(value_1:'The first value', value_2:'The second value'=None):
        return True

    assert hug.test.cli(test, value_1=True) == True


def test_cli_with_kargs():
    '''Test to ensure CLI's work correctly when taking kargs'''
    @hug.cli()
    def test(*values):
        return values

    assert test(1, 2, 3) == (1, 2, 3)
    assert hug.test.cli(test, 1, 2, 3) == (1, 2, 3)


def test_cli_using_method():
    '''Test to ensure that attaching a cli to a class method works as expected'''
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
