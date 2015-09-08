![HUG](https://raw.github.com/timothycrosley/hug/develop/logo.png)
===================

[![PyPI version](https://badge.fury.io/py/hug.png)](http://badge.fury.io/py/hug)
[![Build Status](https://travis-ci.org/timothycrosley/hug.png?branch=master)](https://travis-ci.org/timothycrosley/hug)
[![Coverage Status](https://coveralls.io/repos/timothycrosley/hug/badge.svg?branch=master&service=github)](https://coveralls.io/github/timothycrosley/hug?branch=master)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.python.org/pypi/hug/)
[![Join the chat at https://gitter.im/timothycrosley/hug](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/timothycrosley/hug?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

Hug aims to make developing Python driven APIs as simple as possible, but no simpler. As a result, it drastically simplifies Python API development.

Hug's Design Objectives:

- Make developing a Python driven API as succinct as a written definition.
- The framework should encourage code that self-documents.
- It should be fast. Never should a developer feel the need to look somewhere else for performance reasons.
- Writing tests for APIs written on-top of Hug should be easy and intuitive.
- Magic done once, in an API framework, is better then pushing the problem set to the user of the API framework.
- Be the basis for next generation Python APIs, embracing the latest technology.

As a result of these goals Hug is Python3+ only and uses Falcon under the cover to quickly handle requests.

![HUG Hello World Example](https://raw.github.com/timothycrosley/hug/develop/example.gif)

Installing Hug
===================

Installing Hug is as simple as:

    pip3 install hug --upgrade

Ideally, within a virtual environment.


Basic Example API
===================

happy_birthday.py

    """A basic (single function) API written using Hug"""
    import hug


    @hug.get('/happy_birthday')
    def happy_birthday(name, age:hug.types.number=1):
        """Says happy birthday to a user"""
        return "Happy {age} Birthday {name}!".format(**locals())

To run the example:

    hug -f happy_birthday.py

Then you can access the example from localhost:8000/happy_birthday?name=Hug&age=1
Or access the documentation for your API from localhost:8000/documentation


Versioning with Hug
===================

versioning_example.py

    """A simple example of a hug API call with versioning"""


    @hug.get('/echo', versions=1)
    def echo(text):
        return text


    @hug.get('/echo', versions=range(2, 5))
    def echo(text):
        return "Echo: {text}".format(**locals())

To run the example:

    hug -f versioning_example.py

Then you can access the example from localhost:8000/v1/echo?text=Hi / localhost:8000/v2/echo?text=Hi
Or access the documentation for your API from localhost:8000

Note: versioning in Hug automatically supports both the version header as well as direct URL based specification.


Testing Hug APIs
===================

Hugs http method decorators don't modify your original functions. This makes testing Hug APIs as simple as testing
any other Python functions. Additionally, this means interacting with your API functions in other Python code is as
straight forward as calling Python only API functions. Additionally, Hug makes it easy to test the full Python
stack of your API by using the hug.test module:

    import hug
    import happy_birthday

    hug.test.get(happy_birthday, 'happy_birthday', {'name': 'Timothy', 'age': 25}) # Returns a Response object


Running Hug with other WSGI based servers
===================

Hug exposes a `__hug_wsgi__` magic method on every API module automatically. Running your Hug based API on any
standard wsgi server should be as simple as pointing it to module_name:`__hug_wsgi__`.

For Example:

    uwsgi --http 0.0.0.0:8000 --wsgi-file examples/hello_world.py --callable __hug_wsgi__

To run the hello world Hug example API.


Building Blocks of a Hug API
===================
When Building an API using the Hug framework you'll use the following concepts:

**METHOD Decorators** get, post, update, etc HTTP method decorators that expose your Python function as an API while keeping your Python method unchanged

    @hug.get() # <- Is the Hug METHOD decorator
    def hello_world():
        return "Hello"

Hug uses the structure of the function you decorate to automatically generate documentation for users of your API. Hug always passes a request, response, and api_version
variable to your function if they are defined params in your function definition.

**Type Annotations** functions that optionally are attached to your methods arguments to specify how the argument is validated and converted into a Python type

    @hug.get()
    def math(number_1:int, number_2:int): #The :int after both arguments is the Type Annotation
        return number_1 + number_2

Type annotations also feed into Hug's automatic documentation generation to let users of your API know what data to supply.


**Directives** functions that get executed with the request / response data based on being requested as an argument in your api_function

    @hug.get()
    def test_time(hug_timer):
        return {'time_taken': float(hug_timer)}

Directives are always prefixed with 'hug_'. Adding your own directives is straight forward:

    @hug.directive()
    def multiply(default=1, **all_info):
        '''Returns passed in parameter multiplied by itself'''
        return default * default

    @hug.get()
    def tester(hug_multiply=10):
        return hug_multiply

    tester() == 100


**Output Formatters** a function that takes the output of your API function and formats it for transport to the user of the API.

    @hug.default_output_format()
    def my_output_formatter(data):
        return "STRING:{0}".format(data)

    @hug.get(output=hug.output_format.json)
    def hello():
        return {'hello': 'world'}

as shown, you can easily change the output format for both an entire API as well as an individual API call


**Input Formatters** a function that takes the body of data given from a user of your API and formats it for handling.

    @hug.default_input_formatter("application/json")
    def my_input_formatter(data):
        return ('Results', hug.input_format.json(data))

Input formatters are mapped based on the content_type of the request data, and only perform basic parsing. More detailed
parsing should be done by the Type Annotations present on your api_function


**Middleware** functions that get called for every request a Hug API processes

    @hug.request_middleware()
    def proccess_data(request, response):
        request.env['SERVER_NAME'] = 'changed'

    @hug.response_middleware()
    def proccess_data(request, response, resource):
        response.set_header('MyHeader', 'Value')

You can also easily add any Falcon style middleware using:

    __hug__.add_middleware(MiddlewareObject())



Splitting APIs over multiple files
===================

Hug enables you to organize large projects in any manner you see fit. You can import any module that contains Hug
decorated functions (request handling, directives, type handlers, etc) and extend your base API with that module.

For example:

`something.py`

    import hug

    @hug.get('/')
    def say_hi():
        return 'hello from something'

Can be imported into the main API file:

`__init__.py`

    import hug
    from . import something

    @hug.get('/')
    def say_hi():
        return "Hi from root"

    @hug.extend_api('/something')
    def something_api():
        return [something]

Or alternatively - for cases like this - where only one module is being included per a URL route:

    #alternatively
    __hug__.extend(something, '/something')


Configuring Hug 404
===================

By default, Hug returns an auto generated API spec when a user tries to access an endpoint that isn't defined.
If you would not like to return this spec you can turn off 404 documentation:

From the command line application:

   hug -nd -f {file} #nd flag tells Hug not to generate documentation on 404

Additionally, you can easily create a custom 404 handler using the `hug.not_found` decorator:

    @hug.not_found()
    def not_found_handler():
        return "Not Found"

This decorator works in the same manner as the Hug HTTP method decorators, and is even version aware:

    @hug.not_found(versions=1)
    def not_found_handler():
        return ""

    @hug.not_found(versions=2)
    def not_found_handler():
        return "Not Found"


Why Hug?
===================
HUG simply stands for Hopefully Useful Guide. This represents the projects goal to help guide developers into creating
well written and intuitive APIs.

--------------------------------------------

Thanks and I hope you find *this* hug helpful as you develop your next Python API!

~Timothy Crosley
