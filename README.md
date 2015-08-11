![HUG](https://raw.github.com/timothycrosley/hug/develop/logo.png)
===================

[![PyPI version](https://badge.fury.io/py/hug.png)](http://badge.fury.io/py/hug)
[![Build Status](https://travis-ci.org/timothycrosley/hug.png?branch=master)](https://travis-ci.org/timothycrosley/hug)
[![Coverage Status](https://coveralls.io/repos/timothycrosley/hug/badge.svg?branch=master&service=github)](https://coveralls.io/github/timothycrosley/hug?branch=master)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.python.org/pypi/hug/)

Hug aims to make developing Python driven APIs as simple as possible, but no simpler. As a result, it drastically simplifies Python API development.

Hug's Design Objectives:

- Make developing a Python driven API as succint as a written definition.
- The framework should encourage code that self-documents.
- It should be fast. Never should a developer feel the need to look somewhere else for performance reasons.
- Writing tests for APIs written on-top of Hug should be easy and intuitive.
- Magic done once, in an API, is better then pushing the problem set to the user of the API.
- Be the basis for next generation Python APIs, embracing the latest technology.

As a result of these goals Hug is Python3+ only and uses Falcon under the cover to quickly handler requests.


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

Then you can access the example from localhost:8080/happy_birthday?name=Hug&age=1
Or access the documentation for your API from localhost:8080/documentation


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

Then you can access the example from localhost:8080/v1/echo?text=Hi / localhost:8080/v2/echo?text=Hi
Or access the documentation for your API from localhost:8080/documentation

Note: versioning in hug automatically supports both the version header as well as direct URL based specification.


Testing Hug APIs
===================

Hugs http method decorators don't modify your original functions. This makes testing Hug APIs as simple as testing
any other Python functions. Additionally, this means interacting with your API functions in other Python code is as
straight forward as calling Python only API functions.


Hug Directives
===================

Hug supports argument directives, which means you can defind behavior to automatically be executed by the existince
of an argument in the API definition.


Running hug with other WSGI based servers
===================

Hug exposes a `__hug_wsgi__` magic method on every API module automatically. Running your hug based API on any
standard wsgi server should be as simple as pointing it to module_name:`__hug_wsgi__`.

For Example:

    uwsgi --http 0.0.0.0:8080 --wsgi-file examples/hello_world.py --callable __hug_wsgi__

To run the hello world hug example API.


Why Hug?
===================
HUG simply stands for Hopefully Useful Guide. This represents the projects goal to help guide developers into creating
well written and intuitive APIs.

--------------------------------------------

Thanks and I hope you find *this* hug helpful as you develop your next Python API!

~Timothy Crosley
