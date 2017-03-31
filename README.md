[![HUG](https://raw.github.com/timothycrosley/hug/develop/artwork/logo.png)](http://hug.rest)
===================

[![PyPI version](https://badge.fury.io/py/hug.svg)](http://badge.fury.io/py/hug)
[![Build Status](https://travis-ci.org/timothycrosley/hug.svg?branch=master)](https://travis-ci.org/timothycrosley/hug)
[![Windows Build Status](https://ci.appveyor.com/api/projects/status/0h7ynsqrbaxs7hfm/branch/master?svg=true)](https://ci.appveyor.com/project/TimothyCrosley/hug)
[![Coverage Status](https://coveralls.io/repos/timothycrosley/hug/badge.svg?branch=master&service=github)](https://coveralls.io/github/timothycrosley/hug?branch=master)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.python.org/pypi/hug/)
[![Join the chat at https://gitter.im/timothycrosley/hug](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/timothycrosley/hug?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

NOTE: For more in-depth documentation visit [hug's website](http://www.hug.rest)

hug aims to make developing Python driven APIs as simple as possible, but no simpler. As a result, it drastically simplifies Python API development.

hug's Design Objectives:

- Make developing a Python driven API as succinct as a written definition.
- The framework should encourage code that self-documents.
- It should be fast. Never should a developer feel the need to look somewhere else for performance reasons.
- Writing tests for APIs written on-top of hug should be easy and intuitive.
- Magic done once, in an API framework, is better than pushing the problem set to the user of the API framework.
- Be the basis for next generation Python APIs, embracing the latest technology.

As a result of these goals, hug is Python 3+ only and built upon [Falcon's](https://github.com/falconry/falcon) high performance HTTP library

[![HUG Hello World Example](https://raw.github.com/timothycrosley/hug/develop/artwork/example.gif)](https://github.com/timothycrosley/hug/blob/develop/examples/hello_world.py)


Installing hug
===================

Installing hug is as simple as:

```bash
pip3 install hug --upgrade
```

Ideally, within a [virtual environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/).


Getting Started
===================
Build an example API with a simple endpoint in just a few lines.

```py
# filename: happy_birthday.py
"""A basic (single function) API written using hug"""
import hug


@hug.get('/happy_birthday')
def happy_birthday(name, age:hug.types.number=1):
    """Says happy birthday to a user"""
    return "Happy {age} Birthday {name}!".format(**locals())
```

To run, from the command line type:

```bash
hug -f happy_birthday.py
```

You can access the example in your browser at: `localhost:8000/happy_birthday?name=hug&age=1`. Then check out the documentation for your API at `localhost:8000/documentation`


Using Docker
===================
If you like to develop in Docker and keep your system clean, you can do that but you'll need to first install [Docker Compose](https://docs.docker.com/compose/install/).

Once you've done that, you'll need to `cd` into the `docker` directory and run the web server (Gunicorn) specified in `./docker/gunicorn/Dockerfile`, after which you can preview the output of your API in the browser on your host machine.

```bash
$ cd ./docker
# This will run Gunicorn on port 8000 of the Docker container.
$ docker-compose up gunicorn

# From the host machine, find your Dockers IP address.
# For Windows & Mac:
$ docker-machine ip default

# For Linux:
$ ifconfig docker0 | grep 'inet' | cut -d: -f2 | awk '{ print $1}' | head -n1
```

By default, the IP is 172.17.0.1. Assuming that's the IP you see, as well, you would then go to `http://172.17.0.1:8000/` in your browser to view your API.

You can also log into a Docker container that you can consider your work space. This workspace has Python and Pip installed so you can use those tools within Docker. If you need to test the CLI interface, for example, you would use this.

```bash
$ docker-compose run workspace bash
```

On your Docker `workspace` container, the `./docker/templates` directory on your host computer is mounted to `/src` in the Docker container. This is specified under `services` > `app` of `./docker/docker-compose.yml`.

```bash
bash-4.3# cd /src
bash-4.3# tree
.
├── __init__.py
└── handlers
    ├── birthday.py
    └── hello.py

1 directory, 3 files
```


Versioning with hug
===================

```py
# filename: versioning_example.py
"""A simple example of a hug API call with versioning"""
import hug

@hug.get('/echo', versions=1)
def echo(text):
    return text


@hug.get('/echo', versions=range(2, 5))
def echo(text):
    return "Echo: {text}".format(**locals())
```

To run the example:

```bash
hug -f versioning_example.py
```

Then you can access the example from `localhost:8000/v1/echo?text=Hi` / `localhost:8000/v2/echo?text=Hi` Or access the documentation for your API from `localhost:8000`

Note: versioning in hug automatically supports both the version header as well as direct URL based specification.


Testing hug APIs
===================

hug's `http` method decorators don't modify your original functions. This makes testing hug APIs as simple as testing any other Python functions. Additionally, this means interacting with your API functions in other Python code is as straight forward as calling Python only API functions. Additionally, hug makes it easy to test the full Python stack of your API by using the `hug.test` module:

```py
import hug
import happy_birthday

hug.test.get(happy_birthday, 'happy_birthday', {'name': 'Timothy', 'age': 25}) # Returns a Response object
```


Running hug with other WSGI based servers
===================

hug exposes a `__hug_wsgi__` magic method on every API module automatically. Running your hug based API on any standard wsgi server should be as simple as pointing it to `module_name`: `__hug_wsgi__`.

For Example:

```bash
uwsgi --http 0.0.0.0:8000 --wsgi-file examples/hello_world.py --callable __hug_wsgi__
```

To run the hello world hug example API.


Building Blocks of a hug API
===================

When Building an API using the hug framework you'll use the following concepts:

**METHOD Decorators** `get`, `post`, `update`, etc HTTP method decorators that expose your Python function as an API while keeping your Python method unchanged

```py
@hug.get() # <- Is the hug METHOD decorator
def hello_world():
    return "Hello"
```

hug uses the structure of the function you decorate to automatically generate documentation for users of your API. hug always passes a request, response, and api_version variable to your function if they are defined params in your function definition.

**Type Annotations** functions that optionally are attached to your methods arguments to specify how the argument is validated and converted into a Python type

```py
@hug.get()
def math(number_1:int, number_2:int): #The :int after both arguments is the Type Annotation
    return number_1 + number_2
```

Type annotations also feed into hug's automatic documentation generation to let users of your API know what data to supply.


**Directives** functions that get executed with the request / response data based on being requested as an argument in your api_function.
These apply as input parameters only, and can not be applied currently as output formats or transformations.

```py
@hug.get()
def test_time(hug_timer):
    return {'time_taken': float(hug_timer)}
```

Directives may be accessed via an argument with a `hug_` prefix, or by using Python 3 type annotations. The latter is the more modern approach, and is recommended. Directives declared in a module can be accessed by using their fully qualified name as the type annotation (ex: `module.directive_name`).

Aside from the obvious input transformation use case, directives can be used to pipe data into your API functions, even if they are not present in the request query string, POST body, etc. For an example of how to use directives in this way, see the authentication example in the examples folder.

Adding your own directives is straight forward:

```py
@hug.directive()
def square(value=1, **kwargs):
    '''Returns passed in parameter multiplied by itself'''
    return value * value

@hug.get()
@hug.local()
def tester(value: square=10):
    return value

tester() == 100
```

For completeness, here is an example of accessing the directive via the magic name approach:

```py
@hug.directive()
def multiply(value=1, **kwargs):
    '''Returns passed in parameter multiplied by itself'''
    return value * value

@hug.get()
@hug.local()
def tester(hug_multiply=10):
    return hug_multiply

tester() == 100
```

**Output Formatters** a function that takes the output of your API function and formats it for transport to the user of the API.

```py
@hug.default_output_format()
def my_output_formatter(data):
    return "STRING:{0}".format(data)

@hug.get(output=hug.output_format.json)
def hello():
    return {'hello': 'world'}
```

as shown, you can easily change the output format for both an entire API as well as an individual API call


**Input Formatters** a function that takes the body of data given from a user of your API and formats it for handling.

```py
@hug.default_input_format("application/json")
def my_input_formatter(data):
    return ('Results', hug.input_format.json(data))
```

Input formatters are mapped based on the `content_type` of the request data, and only perform basic parsing. More detailed parsing should be done by the Type Annotations present on your `api_function`


**Middleware** functions that get called for every request a hug API processes

```py
@hug.request_middleware()
def process_data(request, response):
    request.env['SERVER_NAME'] = 'changed'

@hug.response_middleware()
def process_data(request, response, resource):
    response.set_header('MyHeader', 'Value')
```

You can also easily add any Falcon style middleware using:

```py
__hug__.http.add_middleware(MiddlewareObject())
```


Splitting APIs over multiple files
===================

hug enables you to organize large projects in any manner you see fit. You can import any module that contains hug decorated functions (request handling, directives, type handlers, etc) and extend your base API with that module.

For example:

`something.py`

```py
import hug

@hug.get('/')
def say_hi():
    return 'hello from something'
```

Can be imported into the main API file:

`__init__.py`

```py
import hug
from . import something

@hug.get('/')
def say_hi():
    return "Hi from root"

@hug.extend_api('/something')
def something_api():
    return [something]
```

Or alternatively - for cases like this - where only one module is being included per a URL route:

```py
#alternatively
hug.API(__name__).extend(something, '/something')
```


Configuring hug 404
===================

By default, hug returns an auto generated API spec when a user tries to access an endpoint that isn't defined. If you would not like to return this spec you can turn off 404 documentation:

From the command line application:

```bash
hug -nd -f {file} #nd flag tells hug not to generate documentation on 404
```

Additionally, you can easily create a custom 404 handler using the `hug.not_found` decorator:

```py
@hug.not_found()
def not_found_handler():
    return "Not Found"
```

This decorator works in the same manner as the hug HTTP method decorators, and is even version aware:

```py
@hug.not_found(versions=1)
def not_found_handler():
    return ""

@hug.not_found(versions=2)
def not_found_handler():
    return "Not Found"
```


Asyncio support
===============

When using the `get` and `cli` method decorator on coroutines, hug will schedule
the execution of the coroutine.

Using asyncio coroutine decorator
```py
@hug.get()
@asyncio.coroutine
def hello_world():
    return "Hello"
```

Using Python 3.5 async keyword.
```py
@hug.get()
async def hello_world():
    return "Hello"
```

NOTE: Hug is running on top Falcon which is not an asynchronous server. Even if using
asyncio, requests will still be processed synchronously.


Why hug?
===================

HUG simply stands for Hopefully Useful Guide. This represents the projects goal to help guide developers into creating well written and intuitive APIs.

--------------------------------------------

Thanks and I hope you find *this* hug helpful as you develop your next Python API!

~Timothy Crosley
