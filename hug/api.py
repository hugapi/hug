"""hug/api.py

Defines the dynamically generated Hug API object that is responsible for storing all routes and state within a module

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
import sys
from collections import OrderedDict
from itertools import chain
from wsgiref.simple_server import make_server

import hug.defaults
import hug.output_format
from hug.run import INTRO, server


class HugAPI(object):
    '''Stores the information necessary to expose API calls within this module externally'''
    __slots__ = ('module', 'versions', 'routes', '_output_format', '_input_format', '_directives', 'versioned',
                 '_middleware', '_not_found_handlers', '_startup_handlers', 'sinks', '_exception_handlers')

    def __init__(self, module):
        self.module = module
        self.versions = set()
        self.routes = OrderedDict()
        self.sinks = OrderedDict()
        self.versioned = OrderedDict()

    @property
    def output_format(self):
        return getattr(self, '_output_format', hug.defaults.output_format)

    @output_format.setter
    def output_format(self, formatter):
        self._output_format = formatter

    def input_format(self, content_type):
        '''Returns the set input_format handler for the given content_type'''
        return getattr(self, '_input_format', {}).get(content_type, hug.defaults.input_format.get(content_type, None))

    def set_input_format(self, content_type, handler):
        '''Sets an input format handler for this Hug API, given the specified content_type'''
        if getattr(self, '_input_format', None) is None:
            self._input_format = {}
        self._input_format[content_type] = handler

    def directives(self):
        '''Returns all directives applicable to this Hug API'''
        directive_sources = chain(hug.defaults.directives.items(), getattr(self, '_directives', {}).items())
        return {'hug_' + directive_name: directive for directive_name, directive in directive_sources}

    def directive(self, name, default=None):
        '''Returns the loaded directive with the specified name, or default if passed name is not present'''
        return getattr(self, '_directives', {}).get(name,  hug.defaults.directives.get(name, default))

    def add_directive(self, directive):
        self._directives = getattr(self, '_directives', {})
        self._directives[directive.__name__] = directive

    @property
    def middleware(self):
        return getattr(self, '_middleware', None)

    def add_middleware(self, middleware):
        '''Adds a middleware object used to process all incoming requests against the API'''
        if self.middleware is None:
            self._middleware = []
        self.middleware.append(middleware)

    def add_sink(self, sink, url):
        self.sinks[url] = sink

    def extend(self, module, route=""):
        '''Adds handlers from a different Hug API module to this one - to create a single API'''
        self.versions.update(module.__hug__.versions)

        for item_route, handler in module.__hug__.routes.items():
            self.routes[route + item_route] = handler

        for (url, sink) in module.__hug__.sinks.items():
            self.add_sink(sink, url)

        for directive in getattr(module.__hug__, '_directives', {}).values():
            self.add_directive(directive)

        for middleware in (module.__hug__.middleware or ()):
            self.add_middleware(middleware)

        for startup_handler in (module.__hug__.startup_handlers or ()):
            self.add_startup_handler(startup_handler)

        for input_format, input_format_handler in getattr(module.__hug__, '_input_format', {}).items():
            if not input_format in getattr(self, '_input_format', {}):
                self.set_input_format(input_format, input_format_handler)

    @property
    def not_found_handlers(self):
        return getattr(self, '_not_found_handlers', {})

    def set_not_found_handler(self, handler, version=None):
        '''Sets the not_found handler for the specified version of the api'''
        if not self.not_found_handlers:
            self._not_found_handlers = {}

        self.not_found_handlers[version] = handler

    @property
    def startup_handlers(self):
        return getattr(self, '_startup_handlers', ())

    def add_startup_handler(self, handler):
        '''Adds a startup handler to the hug api'''
        if not self.startup_handlers:
            self._startup_handlers = []

        self.startup_handlers.append(handler)

    def exception_handlers(self, version=None):
        if not hasattr(self, '_exception_handlers'):
            return None

        return self._exception_handlers.get(version, self._exception_handlers.get(None, None))

    def add_exception_handler(self, exception_type, error_handler, versions=(None, )):
        '''Adds a error handler to the hug api'''
        versions = (versions, ) if not isinstance(versions, (tuple, list)) else versions
        if not hasattr(self, '_exception_handlers'):
            self._exception_handlers = {}

        for version in versions:
            self._exception_handlers.setdefault(version, OrderedDict())[exception_type] = error_handler

    def serve(self, port=8000, no_documentation=False):
        '''Runs the basic hug development server against this API'''
        if no_documentation:
            api = server(self.module, sink=None)
        else:
            api = server(self.module)

        print(INTRO)
        httpd = make_server('', port, api)
        print("Serving on port {0}...".format(port))
        httpd.serve_forever()


def from_module(module_name):
    '''Returns a Hug API instance from a given module_name'''
    module = sys.modules[module_name]
    if not '__hug__' in module.__dict__:
        def api_auto_instantiate(*kargs, **kwargs):
            if not hasattr(module, '__hug_serving__'):
                module.__hug_wsgi__ = server(module)
                module.__hug_serving__ = True
            return module.__hug_wsgi__(*kargs, **kwargs)
        module.__hug__ = HugAPI(module)
        module.__hug_wsgi__ = api_auto_instantiate
    return module.__hug__


def from_object(obj):
    '''Returns a Hug API instance from a given object (function, class, instance)'''
    return from_module(obj.__module__)
