"""hug/class_based.py

Implements support for class based routing / handlers

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

from types import FunctionType, MethodType

from falcon import HTTP_METHODS

from hug.routing import URLRouter


class ClassBased(URLRouter):
    '''Defines a class based router'''

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
                    URLRouter(**self.where(**route).route)(argument)

        return method_or_class

    def auto_http_methods(self, urls=None, **route_data):
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
                            URLRouter(**router.accept(method).where(**route).route)(handler)
                    else:
                        URLRouter(**router.accept(method).route)(handler)
            return class_definition
        return decorator

classy = ClassBased()
