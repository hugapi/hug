"""hug/decorators.py

Defines the method decorators at the core of Hug's approach to creating HTTP APIs

- Decorators for exposing python method as HTTP methods (get, post, etc)
- Decorators for setting the default output and input formats used throughout an API using the framework
- Decorator for registering a new directive method
- Decorator for including another API modules handlers into the current one, with opitonal prefix route

Copyright (C) 2016  Timothy Edmund Crosley

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
from __future__ import absolute_import

import functools
from collections import namedtuple

from falcon import HTTP_METHODS

import hug.api
import hug.defaults
import hug.output_format
from hug import introspect
from hug.format import underscore


def default_output_format(content_type='application/json', apply_globally=False, api=None):
    """A decorator that allows you to override the default output format for an API"""
    def decorator(formatter):
        formatter = hug.output_format.content_type(content_type)(formatter)
        if apply_globally:
            hug.defaults.output_format = formatter
        else:
            apply_to_api = hug.API(api) if api else hug.api.from_object(formatter)
            apply_to_api.http.output_format = formatter
        return formatter
    return decorator


def default_input_format(content_type='application/json', apply_globally=False, api=None):
    """A decorator that allows you to override the default output format for an API"""
    def decorator(formatter):
        formatter = hug.output_format.content_type(content_type)(formatter)
        if apply_globally:
            hug.defaults.input_format[content_type] = formatter
        else:
            apply_to_api = hug.API(api) if api else hug.api.from_object(formatter)
            apply_to_api.http.set_input_format(content_type, formatter)
        return formatter
    return decorator


def directive(apply_globally=False, api=None):
    """A decorator that registers a single hug directive"""
    def decorator(directive_method):
        if apply_globally:
            hug.defaults.directives[underscore(directive_method.__name__)] = directive_method
        else:
            apply_to_api = hug.API(api) if api else hug.api.from_object(directive_method)
            apply_to_api.add_directive(directive_method)
        directive_method.directive = True
        return directive_method
    return decorator


def startup(api=None):
    """Runs the provided function on startup, passing in an instance of the api"""
    def startup_wrapper(startup_function):
        apply_to_api = hug.API(api) if api else hug.api.from_object(startup_function)
        apply_to_api.http.add_startup_handler(startup_function)
        return startup_function
    return startup_wrapper


def request_middleware(api=None):
    """Registers a middleware function that will be called on every request"""
    def decorator(middleware_method):
        apply_to_api = hug.API(api) if api else hug.api.from_object(middleware_method)

        class MiddlewareRouter(object):
            __slots__ = ()

            def process_request(self, request, response):
                return middleware_method(request, response)

        apply_to_api.http.add_middleware(MiddlewareRouter())
        return middleware_method
    return decorator


def response_middleware(api=None):
    """Registers a middleware function that will be called on every response"""
    def decorator(middleware_method):
        apply_to_api = hug.API(api) if api else hug.api.from_object(middleware_method)

        class MiddlewareRouter(object):
            __slots__ = ()

            def process_response(self, request, response, resource):
                return middleware_method(request, response, resource)

        apply_to_api.http.add_middleware(MiddlewareRouter())
        return middleware_method
    return decorator


def middleware_class(api=None):
    """Registers a middleware class"""
    def decorator(middleware_class):
        apply_to_api = hug.API(api) if api else hug.api.from_object(middleware_class)
        apply_to_api.http.add_middleware(middleware_class())
        return middleware_class
    return decorator


def extend_api(route="", api=None, base_url=""):
    """Extends the current api, with handlers from an imported api. Optionally provide a route that prefixes access"""
    def decorator(extend_with):
        apply_to_api = hug.API(api) if api else hug.api.from_object(extend_with)
        for extended_api in extend_with():
            apply_to_api.extend(extended_api, route, base_url)
        return extend_with
    return decorator


def wraps(function):
    """Enables building decorators around functions used for hug routes without chaninging their function signature"""
    def wrap(decorator):
        decorator = functools.wraps(function)(decorator)
        if not hasattr(function, 'original'):
            decorator.original = function
        else:
            decorator.original = function.original
            delattr(function, 'original')
        return decorator
    return wrap


def auto_kwargs(function):
    """Modifies the provided function to support kwargs by only passing along kwargs for parameters it accepts"""
    supported = introspect.arguments(function)

    @wraps(function)
    def call_function(*args, **kwargs):
        return function(*args, **{key: value for key, value in kwargs.items() if key in supported})
    return call_function
