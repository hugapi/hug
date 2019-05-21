"""hug/route.py

Defines user usable routers

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

from functools import partial
from types import FunctionType, MethodType

from falcon import HTTP_METHODS

import hug.api
from hug.routing import CLIRouter as cli  # noqa:  N813
from hug.routing import ExceptionRouter as exception  # noqa:  N813
from hug.routing import LocalRouter as local  # noqa:  N813
from hug.routing import NotFoundRouter as not_found  # noqa:  N813
from hug.routing import SinkRouter as sink  # noqa:  N813
from hug.routing import StaticRouter as static  # noqa:  N813
from hug.routing import URLRouter as http  # noqa:  N813


class Object(http):
    """Defines a router for classes and objects"""

    def __init__(self, urls=None, accept=HTTP_METHODS, output=None, **kwargs):
        super().__init__(urls=urls, accept=accept, output=output, **kwargs)

    def __call__(self, method_or_class=None, **kwargs):
        if not method_or_class and kwargs:
            return self.where(**kwargs)

        if isinstance(method_or_class, (MethodType, FunctionType)):
            routes = getattr(method_or_class, "_hug_http_routes", [])
            routes.append(self.route)
            method_or_class._hug_http_routes = routes
            return method_or_class

        instance = method_or_class
        if isinstance(method_or_class, type):
            instance = method_or_class()

        for argument in dir(instance):
            argument = getattr(instance, argument, None)

            http_routes = getattr(argument, "_hug_http_routes", ())
            for route in http_routes:
                http(**self.where(**route).route)(argument)

            cli_routes = getattr(argument, "_hug_cli_routes", ())
            for route in cli_routes:
                cli(**self.where(**route).route)(argument)

        return method_or_class

    def http_methods(self, urls=None, **route_data):
        """Creates routes from a class, where the class method names should line up to HTTP METHOD types"""

        def decorator(class_definition):
            instance = class_definition
            if isinstance(class_definition, type):
                instance = class_definition()

            router = self.urls(
                urls if urls else "/{0}".format(instance.__class__.__name__.lower()), **route_data
            )
            for method in HTTP_METHODS:
                handler = getattr(instance, method.lower(), None)
                if handler:
                    http_routes = getattr(handler, "_hug_http_routes", ())
                    if http_routes:
                        for route in http_routes:
                            http(**router.accept(method).where(**route).route)(handler)
                    else:
                        http(**router.accept(method).route)(handler)

                    cli_routes = getattr(handler, "_hug_cli_routes", ())
                    if cli_routes:
                        for route in cli_routes:
                            cli(**self.where(**route).route)(handler)
            return class_definition

        return decorator

    def cli(self, method):
        """Registers a method on an Object as a CLI route"""
        routes = getattr(method, "_hug_cli_routes", [])
        routes.append(self.route)
        method._hug_cli_routes = routes
        return method


class API(object):
    """Provides a convient way to route functions to a single API independent of where they live"""

    __slots__ = ("api",)

    def __init__(self, api):
        if type(api) == str:
            api = hug.api.API(api)
        self.api = api

    def http(self, *args, **kwargs):
        """Starts the process of building a new HTTP route linked to this API instance"""
        kwargs["api"] = self.api
        return http(*args, **kwargs)

    def urls(self, *args, **kwargs):
        """DEPRECATED: for backwords compatibility with < hug 2.2.0. `API.http` should be used instead.

           Starts the process of building a new URL HTTP route linked to this API instance
        """
        return self.http(*args, **kwargs)

    def not_found(self, *args, **kwargs):
        """Defines the handler that should handle not found requests against this API"""
        kwargs["api"] = self.api
        return not_found(*args, **kwargs)

    def static(self, *args, **kwargs):
        """Define the routes to static files the API should expose"""
        kwargs["api"] = self.api
        return static(*args, **kwargs)

    def sink(self, *args, **kwargs):
        """Define URL prefixes/handler matches where everything under the URL prefix should be handled"""
        kwargs["api"] = self.api
        return sink(*args, **kwargs)

    def exception(self, *args, **kwargs):
        """Defines how this API should handle the provided exceptions"""
        kwargs["api"] = self.api
        return exception(*args, **kwargs)

    def cli(self, *args, **kwargs):
        """Defines a CLI function that should be routed by this API"""
        kwargs["api"] = self.api
        return cli(*args, **kwargs)

    def object(self, *args, **kwargs):
        """Registers a class based router to this API"""
        kwargs["api"] = self.api
        return Object(*args, **kwargs)

    def get(self, *args, **kwargs):
        """Builds a new GET HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("GET",)
        return http(*args, **kwargs)

    def post(self, *args, **kwargs):
        """Builds a new POST HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("POST",)
        return http(*args, **kwargs)

    def put(self, *args, **kwargs):
        """Builds a new PUT HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("PUT",)
        return http(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Builds a new DELETE HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("DELETE",)
        return http(*args, **kwargs)

    def connect(self, *args, **kwargs):
        """Builds a new CONNECT HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("CONNECT",)
        return http(*args, **kwargs)

    def head(self, *args, **kwargs):
        """Builds a new HEAD HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("HEAD",)
        return http(*args, **kwargs)

    def options(self, *args, **kwargs):
        """Builds a new OPTIONS HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("OPTIONS",)
        return http(*args, **kwargs)

    def patch(self, *args, **kwargs):
        """Builds a new PATCH HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("PATCH",)
        return http(*args, **kwargs)

    def trace(self, *args, **kwargs):
        """Builds a new TRACE HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("TRACE",)
        return http(*args, **kwargs)

    def get_post(self, *args, **kwargs):
        """Builds a new GET or POST HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("GET", "POST")
        return http(*args, **kwargs)

    def put_post(self, *args, **kwargs):
        """Builds a new PUT or POST HTTP route that is registered to this API"""
        kwargs["api"] = self.api
        kwargs["accept"] = ("PUT", "POST")
        return http(*args, **kwargs)


for method in HTTP_METHODS:
    method_handler = partial(http, accept=(method,))
    method_handler.__doc__ = "Exposes a Python method externally as an HTTP {0} method".format(
        method.upper()
    )
    globals()[method.lower()] = method_handler

get_post = partial(http, accept=("GET", "POST"))
get_post.__doc__ = "Exposes a Python method externally under both the HTTP POST and GET methods"

put_post = partial(http, accept=("PUT", "POST"))
put_post.__doc__ = "Exposes a Python method externally under both the HTTP POST and PUT methods"

object = Object()

# DEPRECATED: for backwords compatibility with hug 1.x.x
call = http
