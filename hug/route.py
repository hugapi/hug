"""hug/route.py

Defines user usable routers

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
from __future__ import absolute_import

from functools import partial
from types import FunctionType, MethodType

import hug.api
from falcon import HTTP_METHODS
from hug.routing import CLIRouter as cli
from hug.routing import ExceptionRouter as exception
from hug.routing import NotFoundRouter as not_found
from hug.routing import SinkRouter as sink
from hug.routing import StaticRouter as static
from hug.routing import URLRouter as call


class Object(call):
    '''Defines a router for classes and objects'''

    def __init__(self, **route):
        if 'requires' in route:
            requires = route['requires']
            route['requires'] = (requires, ) if not isinstance(requires, (tuple, list)) else requires
        self.route = route

    def __call__(self, method_or_class):
        if isinstance(method_or_class, (MethodType, FunctionType)):
            routes = getattr(method_or_class, '_hug_routes', [])
            routes.append(self.route)
            method_or_class._hug_routes = routes
            return method_or_class

        instance = method_or_class
        if isinstance(method_or_class, type):
            instance = method_or_class()

        for argument in dir(instance):
            argument = getattr(instance, argument, None)
            routes = getattr(argument, '_hug_routes', None)
            if routes:
                for route in routes:
                    call(**self.where(**route).route)(argument)

        return method_or_class

    def http_methods(self, urls=None, **route_data):
        '''Creates routes from a class, where the class method names should line up to HTTP METHOD types'''
        def decorator(class_definition):
            instance = class_definition
            if isinstance(class_definition, type):
                instance = class_definition()

            router = self.urls(urls if urls else "/{0}".format(instance.__class__.__name__.lower()), **route_data)
            for method in HTTP_METHODS:
                handler = getattr(instance, method.lower(), None)
                if handler:
                    routes = getattr(handler, '_hug_routes', None)
                    if routes:
                        for route in routes:
                            call(**router.accept(method).where(**route).route)(handler)
                    else:
                        call(**router.accept(method).route)(handler)
            return class_definition
        return decorator


class API(object):
    '''Provides a convient way to route functions to a single API independant of where they live'''
    __slots__ = ('api', )

    def __init__(self, api):
        if type(api) == str:
            api = hug.api.API(api)
        self.api = api

    def urls(self, *kargs, **kwargs):
        '''Starts the process of building a new URL route linked to this API instance'''
        kwargs['api'] = self.api
        return call(*kargs, **kwargs)

    def not_found(self, *kargs, **kwargs):
        '''Defines the handler that should handle not found requests against this API'''
        kwargs['api'] = self.api
        return not_found(*kargs, **kwargs)

    def static(self, *kargs, **kwargs):
        '''Define the routes to static files the API should expose'''
        kwargs['api'] = self.api
        return static(*kargs, **kwargs)

    def sink(self, *kargs, **kwargs):
        '''Define URL prefixes/handler matches where everything under the URL prefix should be handled'''
        kwargs['api'] = self.api
        return sink(*kargs, **kwargs)

    def exceptions(self, *kargs, **kwargs):
        '''Defines how this API should handle the provided exceptions'''
        kwargs['api'] = self.api
        return exception(*kargs, **kwargs)

    def cli(self, *kargs, **kwargs):
        '''Defines a CLI function that should be routed by this API'''
        kwargs['api'] = self.api
        return cli(*kargs, **kwargs)

    def object(self, *kargs, **kwargs):
        '''Registers a class based router to this API'''
        kwargs['api'] = self.api
        return Object(*kargs, **kwargs)


for method in HTTP_METHODS:
    method_handler = partial(call, accept=(method, ))
    method_handler.__doc__ = "Exposes a Python method externally as an HTTP {0} method".format(method.upper())
    globals()[method.lower()] = method_handler

get_post = partial(call, accept=('GET', 'POST'))
get_post.__doc__ = "Exposes a Python method externally under both the HTTP POST and GET methods"

object = Object()
