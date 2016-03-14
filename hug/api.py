"""hug/api.py

Defines the dynamically generated Hug API object that is responsible for storing all routes and state within a module

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

import json
import sys
from collections import OrderedDict, namedtuple
from functools import partial
from itertools import chain
from wsgiref.simple_server import make_server

import falcon
from falcon import HTTP_METHODS

import hug.defaults
import hug.output_format
from hug._version import current


INTRO = """
/#######################################################################\\
          `.----``..-------..``.----.
         :/:::::--:---------:--::::://.
        .+::::----##/-/oo+:-##----:::://
        `//::-------/oosoo-------::://.       ##    ##  ##    ##    #####
          .-:------./++o/o-.------::-`   ```  ##    ##  ##    ##  ##
             `----.-./+o+:..----.     `.:///. ########  ##    ## ##
   ```        `----.-::::::------  `.-:::://. ##    ##  ##    ## ##   ####
  ://::--.``` -:``...-----...` `:--::::::-.`  ##    ##  ##   ##   ##    ##
  :/:::::::::-:-     `````      .:::::-.`     ##    ##    ####     ######
   ``.--:::::::.                .:::.`
         ``..::.                .::         EMBRACE THE APIs OF THE FUTURE
             ::-                .:-
             -::`               ::-                   VERSION {0}
             `::-              -::`
              -::-`           -::-
\########################################################################/

 Copyright (C) 2016 Timothy Edmund Crosley
 Under the MIT License

""".format(current)


class InterfaceAPI(object):
    """Defines the per-interface API which defines all shared information for a specific interface, and how it should
        be exposed
    """
    __slots__ = ('api', )

    def __init__(self, api):
        self.api = api


class HTTPInterfaceAPI(InterfaceAPI):
    """Defines the HTTP interface specific API"""
    __slots__ = ('routes', 'versions', 'base_url', '_output_format', '_input_format', 'versioned', '_middleware',
                 '_not_found_handlers', '_startup_handlers', 'sinks', '_not_found', '_exception_handlers')

    def __init__(self, api, base_url=''):
        super().__init__(api)
        self.versions = set()
        self.routes = OrderedDict()
        self.sinks = OrderedDict()
        self.versioned = OrderedDict()
        self.base_url = base_url

    @property
    def output_format(self):
        return getattr(self, '_output_format', hug.defaults.output_format)

    @output_format.setter
    def output_format(self, formatter):
        self._output_format = formatter

    @property
    def not_found(self):
        """Returns the active not found handler"""
        handler = getattr(self, '_not_found', self.base_404)
        handler.interface = True
        return handler

    def input_format(self, content_type):
        """Returns the set input_format handler for the given content_type"""
        return getattr(self, '_input_format', {}).get(content_type, hug.defaults.input_format.get(content_type, None))

    def set_input_format(self, content_type, handler):
        """Sets an input format handler for this Hug API, given the specified content_type"""
        if getattr(self, '_input_format', None) is None:
            self._input_format = {}
        self._input_format[content_type] = handler

    @property
    def middleware(self):
        return getattr(self, '_middleware', None)

    def add_middleware(self, middleware):
        """Adds a middleware object used to process all incoming requests against the API"""
        if self.middleware is None:
            self._middleware = []
        self.middleware.append(middleware)

    def add_sink(self, sink, url):
        self.sinks[url] = sink

    def exception_handlers(self, version=None):
        if not hasattr(self, '_exception_handlers'):
            return None

        return self._exception_handlers.get(version, self._exception_handlers.get(None, None))

    def add_exception_handler(self, exception_type, error_handler, versions=(None, )):
        """Adds a error handler to the hug api"""
        versions = (versions, ) if not isinstance(versions, (tuple, list)) else versions
        if not hasattr(self, '_exception_handlers'):
            self._exception_handlers = {}

        for version in versions:
            self._exception_handlers.setdefault(version, OrderedDict())[exception_type] = error_handler

    def extend(self, http_api, route=""):
        """Adds handlers from a different Hug API to this one - to create a single API"""
        self.versions.update(http_api.versions)

        for item_route, handler in http_api.routes.items():
            self.routes[route + item_route] = handler

        for (url, sink) in http_api.sinks.items():
            self.add_sink(sink, url)

        for middleware in (http_api.middleware or ()):
            self.add_middleware(middleware)

        for startup_handler in (http_api.startup_handlers or ()):
            self.add_startup_handler(startup_handler)\

        for version, handler in getattr(http_api, '_exception_handlers', {}).items():
            for exception_type, exception_handler in handler.items():
                self.add_exception_handler(exception_type, exception_handler, version)

        for input_format, input_format_handler in getattr(http_api, '_input_format', {}).items():
            if not input_format in getattr(self, '_input_format', {}):
                self.set_input_format(input_format, input_format_handler)

    @property
    def not_found_handlers(self):
        return getattr(self, '_not_found_handlers', {})

    def set_not_found_handler(self, handler, version=None):
        """Sets the not_found handler for the specified version of the api"""
        if not self.not_found_handlers:
            self._not_found_handlers = {}

        self.not_found_handlers[version] = handler

    def documentation(self, base_url=None, api_version=None):
        """Generates and returns documentation for this API endpoint"""
        documentation = OrderedDict()
        base_url = self.base_url if base_url is None else base_url
        overview = self.api.module.__doc__
        if overview:
            documentation['overview'] = overview

        version_dict = OrderedDict()
        versions = self.versions
        versions_list = list(versions)
        versions_list.remove(None)
        if api_version is None and len(versions_list) > 0:
            api_version = max(versions_list)
            documentation['version'] = api_version
        elif api_version is not None:
            documentation['version'] = api_version
        if versions_list:
            documentation['versions'] = versions_list
        for url, methods in self.routes.items():
            for method, method_versions in methods.items():
                for version, handler in method_versions.items():
                    if version is None:
                        applies_to = versions
                    else:
                        applies_to = (version, )
                    for version in applies_to:
                        if api_version and version != api_version:
                            continue
                        doc = version_dict.setdefault(url, OrderedDict())
                        doc[method] = handler.documentation(doc.get(method, None), version=version,
                                                            base_url=base_url, url=url)

        documentation['handlers'] = version_dict
        return documentation

    def serve(self, port=8000, no_documentation=False):
        """Runs the basic hug development server against this API"""
        if no_documentation:
            api = self.server(None)
        else:
            api = self.server()

        print(INTRO)
        httpd = make_server('', port, api)
        print("Serving on port {0}...".format(port))
        httpd.serve_forever()

    @staticmethod
    def base_404(request, response, *kargs, **kwargs):
        """Defines the base 404 handler"""
        response.status = falcon.HTTP_NOT_FOUND

    def determine_version(self, request, api_version=None):
        """Determines the appropriate version given the set api_version, the request header, and URL query params"""
        if api_version is False:
            api_version = None
            for version in self.versions:
                if version and "v{0}".format(version) in request.path:
                    api_version = version
                    break

        request_version = set()
        if api_version is not None:
            request_version.add(api_version)

        version_header = request.get_header("X-API-VERSION")
        if version_header:
            request_version.add(version_header)

        version_param = request.get_param('api_version')
        if version_param is not None:
            request_version.add(version_param)

        if len(request_version) > 1:
            raise ValueError('You are requesting conflicting versions')

        return next(iter(request_version or (None, )))

    def documentation_404(self, base_url=None):
        """Returns a smart 404 page that contains documentation for the written API"""
        base_url = self.base_url if base_url is None else base_url

        def handle_404(request, response, *kargs, **kwargs):
            url_prefix = self.base_url
            if not url_prefix:
                url_prefix = request.url[:-1]
                if request.path and request.path != "/":
                    url_prefix = request.url.split(request.path)[0]

            to_return = OrderedDict()
            to_return['404'] = ("The API call you tried to make was not defined. "
                                "Here's a definition of the API to help you get going :)")
            to_return['documentation'] = self.documentation(url_prefix, self.determine_version(request, False))
            response.data = json.dumps(to_return, indent=4, separators=(',', ': ')).encode('utf8')
            response.status = falcon.HTTP_NOT_FOUND
            response.content_type = 'application/json'
        return handle_404

    def version_router(self, request, response, api_version=None, versions={}, not_found=None, **kwargs):
        """Intelligently routes a request to the correct handler based on the version being requested"""
        request_version = self.determine_version(request, api_version)
        if request_version:
            request_version = int(request_version)
        versions.get(request_version, versions.get(None, not_found))(request, response, api_version=api_version,
                                                                     **kwargs)

    def server(self, default_not_found=True, base_url=None):
        """Returns a WSGI compatible API server for the given Hug API module"""
        falcon_api = falcon.API(middleware=self.middleware)
        default_not_found = self.documentation_404() if default_not_found is True else None
        base_url = self.base_url if base_url is None else base_url

        not_found_handler = default_not_found
        for startup_handler in self.startup_handlers:
            startup_handler(self)
        if self.not_found_handlers:
            if len(self.not_found_handlers) == 1 and None in self.not_found_handlers:
                not_found_handler = self.not_found_handlers[None]
            else:
                not_found_handler = partial(self.version_router, api_version=False,
                                            versions=self.not_found_handlers, not_found=default_not_found)

        if not_found_handler:
            falcon_api.add_sink(not_found_handler)
            self._not_found = not_found_handler

        for url, extra_sink in self.sinks.items():
            falcon_api.add_sink(extra_sink, base_url + url)

        for url, methods in self.routes.items():
            router = {}
            for method, versions in methods.items():
                method_function = "on_{0}".format(method.lower())
                if len(versions) == 1 and None in versions.keys():
                    router[method_function] = versions[None]
                else:
                    router[method_function] = partial(self.version_router, versions=versions,
                                                      not_found=not_found_handler)

            router = namedtuple('Router', router.keys())(**router)
            falcon_api.add_route(base_url + url, router)
            if self.versions and self.versions != (None, ):
                falcon_api.add_route(base_url + '/v{api_version}' + url, router)

        def error_serializer(_, error):
            return (self.output_format.content_type,
                    self.output_format({"errors": {error.title: error.description}}))

        falcon_api.set_error_serializer(error_serializer)
        return falcon_api

    @property
    def startup_handlers(self):
        return getattr(self, '_startup_handlers', ())

    def add_startup_handler(self, handler):
        """Adds a startup handler to the hug api"""
        if not self.startup_handlers:
            self._startup_handlers = []

        self.startup_handlers.append(handler)


class CLIInterfaceAPI(InterfaceAPI):
    """Defines the CLI interface specific API"""
    __slots__ = ('commands', )

    def __init__(self, api, version=''):
        super().__init__(api)
        self.commands = {}

    def __call__(self):
        """Routes to the correct command line tool"""
        if not len(sys.argv) > 1 or not sys.argv[1] in self.commands:
            print(str(self))
            return sys.exit(1)

        command = sys.argv.pop(1)
        self.commands.get(command)()

    def __str__(self):
        return "{0}\n\nAvailable Commands:{1}\n".format(self.api.module.__doc__ or self.api.module.__name__,
                                                        "\n\n\t- " + "\n- ".join(self.commands.keys()))


class ModuleSingleton(type):
    """Defines the module level __hug__ singleton"""

    def __call__(cls, module, *args, **kwargs):
        if isinstance(module, API):
            return module

        if type(module) == str:
            module = sys.modules[module]

        if not '__hug__' in module.__dict__:
            def api_auto_instantiate(*kargs, **kwargs):
                if not hasattr(module, '__hug_serving__'):
                    module.__hug_wsgi__ = module.__hug__.http.server()
                    module.__hug_serving__ = True
                return module.__hug_wsgi__(*kargs, **kwargs)

            module.__hug__ = super().__call__(module, *args, **kwargs)
            module.__hug_wsgi__ = api_auto_instantiate
        return module.__hug__


class API(object, metaclass=ModuleSingleton):
    """Stores the information necessary to expose API calls within this module externally"""
    __slots__ = ('module', '_directives', '_http', '_cli')

    def __init__(self, module):
        self.module = module

    def directives(self):
        """Returns all directives applicable to this Hug API"""
        directive_sources = chain(hug.defaults.directives.items(), getattr(self, '_directives', {}).items())
        return {'hug_' + directive_name: directive for directive_name, directive in directive_sources}

    def directive(self, name, default=None):
        """Returns the loaded directive with the specified name, or default if passed name is not present"""
        return getattr(self, '_directives', {}).get(name,  hug.defaults.directives.get(name, default))

    def add_directive(self, directive):
        self._directives = getattr(self, '_directives', {})
        self._directives[directive.__name__] = directive

    @property
    def http(self):
        if not hasattr(self, '_http'):
            self._http = HTTPInterfaceAPI(self)
        return self._http

    @property
    def cli(self):
        if not hasattr(self, '_cli'):
            self._cli = CLIInterfaceAPI(self)
        return self._cli


    def extend(self, api, route=""):
        """Adds handlers from a different Hug API to this one - to create a single API"""
        api = API(api)

        if hasattr(api, '_http'):
            self.http.extend(api.http, route)

        for directive in getattr(api, '_directives', {}).values():
            self.add_directive(directive)


def from_object(obj):
    """Returns a Hug API instance from a given object (function, class, instance)"""
    return API(obj.__module__)
