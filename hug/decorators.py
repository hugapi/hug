"""hug/decorators.py

Defines the method decorators at the core of Hug's approach to creating HTTP APIs

- Decorators for exposing python method as HTTP methods (get, post, etc)
- Decorators for setting the default output and input formats used throughout an API using the framework
- Decorator for registering a new directive method
- Decorator for including another API modules handlers into the current one, with opitonal prefix route

Copyright (C) 2015  Timothy Edmund Crosley

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
from collections import namedtuple

import hug.api
import hug.defaults
import hug.output_format
from falcon import HTTP_METHODS
from hug.format import underscore


def default_output_format(content_type='application/json', apply_globally=False):
    """A decorator that allows you to override the default output format for an API"""
    def decorator(formatter):
        api = hug.api.from_object(formatter)
        formatter = hug.output_format.content_type(content_type)(formatter)
        if apply_globally:
            hug.defaults.output_format = formatter
        else:
            api.output_format = formatter
        return formatter
    return decorator


def default_input_format(content_type='application/json', apply_globally=False):
    """A decorator that allows you to override the default output format for an API"""
    def decorator(formatter):
        api = hug.api.from_object(formatter)
        formatter = hug.output_format.content_type(content_type)(formatter)
        if apply_globally:
            hug.defaults.input_format[content_type] = formatter
        else:
            api.set_input_format(content_type, formatter)
        return formatter
    return decorator


def directive(apply_globally=True):
    """A decorator that registers a single hug directive"""
    def decorator(directive_method):
        if apply_globally:
            hug.defaults.directives[underscore(directive_method.__name__)] = directive_method
        else:
            api = hug.api.from_object(directive_method)
            api.add_directive(directive_method)
        directive_method.directive = True
        return directive_method
    return decorator


def startup():
    """Runs the provided function on startup, passing in an instance of the api"""
    def startup_wrapper(startup_function):
        hug.api.from_object(startup_function).add_startup_handler(startup_function)
        return startup_function
    return startup_wrapper


def request_middleware():
    """Registers a middleware function that will be called on every request"""
    def decorator(middleware_method):
        api = hug.api.from_object(middleware_method)
        middleware_method.__self__ = middleware_method
        api.add_middleware(namedtuple('MiddlewareRouter', ('process_request', ))(middleware_method))
        return middleware_method
    return decorator


def response_middleware():
    """Registers a middleware function that will be called on every response"""
    def decorator(middleware_method):
        api = hug.api.from_object(middleware_method)
        middleware_method.__self__ = middleware_method
        api.add_middleware(namedtuple('MiddlewareRouter', ('process_response', ))(middleware_method))
        return middleware_method
    return decorator


def middleware_class():
    """Registers a middleware class"""
    def decorator(middleware_class):
        hug.api.from_object(middleware_class).add_middleware(middleware_class())
        return middleware_class
    return decorator


def extend_api(route=""):
    """Extends the current api, with handlers from an imported api. Optionally provide a route that prefixes access"""
    def decorator(extend_with):
        api = hug.api.from_object(extend_with)
        for extended_api in extend_with():
            api.extend(extended_api, route)
        return extend_with
    return decorator
