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

import asyncio
import sys
from collections import OrderedDict, namedtuple
from distutils.util import strtobool
from functools import partial
from itertools import chain
from types import ModuleType
from wsgiref.simple_server import make_server

import falcon
from falcon import HTTP_METHODS

import hug.defaults
import hug.output_format
from hug import introspect
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

""".format(
    current
)


class InterfaceAPI(object):
    """Defines the per-interface API which defines all shared information for a specific interface, and how it should
        be exposed
    """

    __slots__ = ("api",)

    def __init__(self, api):
        self.api = api


class HTTPInterfaceAPI(InterfaceAPI):
    """Defines the HTTP interface specific API"""
    __slots__ = (
        "routes",
        "versions",
        "base_url",
        "falcon",
        "_output_format",
        "_input_format",
        "versioned",
        "_middleware",
        "_not_found_handlers",
        "sinks",
        "_not_found",
        "_exception_handlers",
    )

    def __init__(self, api, base_url=""):
        super().__init__(api)
        self.versions = set()
        self.routes = OrderedDict()
        self.sinks = OrderedDict()
        self.versioned = OrderedDict()
        self.base_url = base_url

    @property
    def output_format(self):
        return getattr(self, "_output_format", hug.defaults.output_format)

    @output_format.setter
    def output_format(self, formatter):
        self._output_format = formatter

    @property
    def not_found(self):
        """Returns the active not found handler"""
        return getattr(self, "_not_found", self.base_404)

    def urls(self):
        """Returns a generator of all URLs attached to this API"""
        for base_url, mapping in self.routes.items():
            for url, _ in mapping.items():
                yield base_url + url

    def handlers(self):
        """Returns all registered handlers attached to this API"""
        used = []
        for base_url, mapping in self.routes.items():
            for url, methods in mapping.items():
                for method, versions in methods.items():
                    for version, handler in versions.items():
                        if not handler in used:
                            used.append(handler)
                            yield handler

    def input_format(self, content_type):
        """Returns the set input_format handler for the given content_type"""
        return getattr(self, "_input_format", {}).get(
            content_type, hug.defaults.input_format.get(content_type, None)
        )

    def set_input_format(self, content_type, handler):
        """Sets an input format handler for this Hug API, given the specified content_type"""
        if getattr(self, "_input_format", None) is None:
            self._input_format = {}
        self._input_format[content_type] = handler

    @property
    def middleware(self):
        return getattr(self, "_middleware", None)

    def add_middleware(self, middleware):
        """Adds a middleware object used to process all incoming requests against the API"""
        if self.middleware is None:
            self._middleware = []
        self.middleware.append(middleware)

    def add_sink(self, sink, url, base_url=""):
        base_url = base_url or self.base_url
        self.sinks.setdefault(base_url, OrderedDict())
        self.sinks[base_url][url] = sink

    def exception_handlers(self, version=None):
        if not hasattr(self, "_exception_handlers"):
            return None

        return self._exception_handlers.get(version, self._exception_handlers.get(None, None))

    def add_exception_handler(self, exception_type, error_handler, versions=(None,)):
        """Adds a error handler to the hug api"""
        versions = (versions,) if not isinstance(versions, (tuple, list)) else versions
        if not hasattr(self, "_exception_handlers"):
            self._exception_handlers = {}

        for version in versions:
            placement = self._exception_handlers.setdefault(version, OrderedDict())
            placement[exception_type] = (error_handler,) + placement.get(exception_type, tuple())

    def extend(self, http_api, route="", base_url="", **kwargs):
        """Adds handlers from a different Hug API to this one - to create a single API"""
        self.versions.update(http_api.versions)
        base_url = base_url or self.base_url

        for router_base_url, routes in http_api.routes.items():
            self.routes.setdefault(base_url, OrderedDict())
            for item_route, handler in routes.items():
                for method, versions in handler.items():
                    for version, function in versions.items():
                        function.interface.api = self.api
                self.routes[base_url].setdefault(route + item_route, {}).update(handler)

        for sink_base_url, sinks in http_api.sinks.items():
            for url, sink in sinks.items():
                self.add_sink(sink, route + url, base_url=base_url)

        for middleware in http_api.middleware or ():
            self.add_middleware(middleware)

        for version, handler in getattr(http_api, "_exception_handlers", {}).items():
            for exception_type, exception_handlers in handler.items():
                target_exception_handlers = self.exception_handlers(version) or {}
                for exception_handler in exception_handlers:
                    if exception_type not in target_exception_handlers:
                        self.add_exception_handler(exception_type, exception_handler, version)

        for input_format, input_format_handler in getattr(http_api, "_input_format", {}).items():
            if not input_format in getattr(self, "_input_format", {}):
                self.set_input_format(input_format, input_format_handler)

        for version, handler in http_api.not_found_handlers.items():
            if version not in self.not_found_handlers:
                self.set_not_found_handler(handler, version)

    @property
    def not_found_handlers(self):
        return getattr(self, "_not_found_handlers", {})

    def set_not_found_handler(self, handler, version=None):
        """Sets the not_found handler for the specified version of the api"""
        if not self.not_found_handlers:
            self._not_found_handlers = {}

        self.not_found_handlers[version] = handler

    def documentation(self, base_url=None, api_version=None, prefix=""):
        """Generates and returns documentation for this API endpoint"""
        documentation = OrderedDict()
        base_url = self.base_url if base_url is None else base_url
        overview = self.api.doc
        if overview:
            documentation["overview"] = overview

        version_dict = OrderedDict()
        versions = self.versions
        versions_list = list(versions)
        if None in versions_list:
            versions_list.remove(None)
        if False in versions_list:
            versions_list.remove(False)
        if api_version is None and len(versions_list) > 0:
            api_version = max(versions_list)
            documentation["version"] = api_version
        elif api_version is not None:
            documentation["version"] = api_version
        if versions_list:
            documentation["versions"] = versions_list
        for router_base_url, routes in self.routes.items():
            for url, methods in routes.items():
                for method, method_versions in methods.items():
                    for version, handler in method_versions.items():
                        if getattr(handler, "private", False):
                            continue
                        if version is None:
                            applies_to = versions
                        else:
                            applies_to = (version,)
                        for version in applies_to:
                            if api_version and version != api_version:
                                continue
                            if base_url and router_base_url != base_url:
                                continue
                            doc = version_dict.setdefault(url, OrderedDict())
                            doc[method] = handler.documentation(
                                doc.get(method, None),
                                version=version,
                                prefix=prefix,
                                base_url=router_base_url,
                                url=url,
                            )
        documentation["handlers"] = version_dict
        return documentation

    def serve(self, host="", port=8000, no_documentation=False, display_intro=True):
        """Runs the basic hug development server against this API"""
        if no_documentation:
            api = self.server(None)
        else:
            api = self.server()

        if display_intro:
            print(INTRO)

        httpd = make_server(host, port, api)
        print("Serving on {0}:{1}...".format(host, port))
        httpd.serve_forever()

    @staticmethod
    def base_404(request, response, *args, **kwargs):
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

        version_param = request.get_param("api_version")
        if version_param is not None:
            request_version.add(version_param)

        if len(request_version) > 1:
            raise ValueError("You are requesting conflicting versions")

        return next(iter(request_version or (None,)))

    def documentation_404(self, base_url=None):
        """Returns a smart 404 page that contains documentation for the written API"""
        base_url = self.base_url if base_url is None else base_url

        def handle_404(request, response, *args, **kwargs):
            url_prefix = request.forwarded_uri[:-1]
            if request.path and request.path != "/":
                url_prefix = request.forwarded_uri.split(request.path)[0]

            to_return = OrderedDict()
            to_return["404"] = (
                "The API call you tried to make was not defined. "
                "Here's a definition of the API to help you get going :)"
            )
            to_return["documentation"] = self.documentation(
                base_url, self.determine_version(request, False), prefix=url_prefix
            )

            if self.output_format == hug.output_format.json:
                response.data = hug.output_format.json(to_return, indent=4, separators=(",", ": "))
                response.content_type = "application/json; charset=utf-8"
            else:
                response.data = self.output_format(to_return, request=request, response=response)
                response.content_type = self.output_format.content_type

            response.status = falcon.HTTP_NOT_FOUND

        handle_404.interface = True
        return handle_404

    def version_router(
        self, request, response, api_version=None, versions={}, not_found=None, **kwargs
    ):
        """Intelligently routes a request to the correct handler based on the version being requested"""
        request_version = self.determine_version(request, api_version)
        if request_version:
            request_version = int(request_version)
        versions.get(request_version or False, versions.get(None, not_found))(
            request, response, api_version=api_version, **kwargs
        )

    def server(self, default_not_found=True, base_url=None):
        """Returns a WSGI compatible API server for the given Hug API module"""
        falcon_api = self.falcon = falcon.API(middleware=self.middleware)
        falcon_api.req_options.keep_blank_qs_values = False
        default_not_found = self.documentation_404() if default_not_found is True else None
        base_url = self.base_url if base_url is None else base_url

        not_found_handler = default_not_found
        self.api._ensure_started()
        if self.not_found_handlers:
            if len(self.not_found_handlers) == 1 and None in self.not_found_handlers:
                not_found_handler = self.not_found_handlers[None]
            else:
                not_found_handler = partial(
                    self.version_router,
                    api_version=False,
                    versions=self.not_found_handlers,
                    not_found=default_not_found,
                )
                not_found_handler.interface = True

        if not_found_handler:
            falcon_api.add_sink(not_found_handler)
            self._not_found = not_found_handler

        for sink_base_url, sinks in self.sinks.items():
            for url, extra_sink in sinks.items():
                falcon_api.add_sink(extra_sink, sink_base_url + url + "(?P<path>.*)")

        for router_base_url, routes in self.routes.items():
            for url, methods in routes.items():
                router = {}
                for method, versions in methods.items():
                    method_function = "on_{0}".format(method.lower())
                    if len(versions) == 1 and None in versions.keys():
                        router[method_function] = versions[None]
                    else:
                        router[method_function] = partial(
                            self.version_router, versions=versions, not_found=not_found_handler
                        )

                router = namedtuple("Router", router.keys())(**router)
                falcon_api.add_route(router_base_url + url, router)
                if self.versions and self.versions != (None,):
                    falcon_api.add_route(router_base_url + "/v{api_version}" + url, router)

        def error_serializer(request, response, error):
            response.content_type = self.output_format.content_type
            response.body = self.output_format(
                {"errors": {error.title: error.description}}, request, response
            )

        falcon_api.set_error_serializer(error_serializer)
        return falcon_api


HTTPInterfaceAPI.base_404.interface = True


class CLIInterfaceAPI(InterfaceAPI):
    """Defines the CLI interface specific API"""

    __slots__ = ("commands", "error_exit_codes", "_output_format")

    def __init__(self, api, version="", error_exit_codes=False):
        super().__init__(api)
        self.commands = {}
        self.error_exit_codes = error_exit_codes

    def __call__(self, args=None):
        """Routes to the correct command line tool"""
        self.api._ensure_started()
        args = sys.argv if args is None else args
        if not len(args) > 1 or not args[1] in self.commands:
            print(str(self))
            return sys.exit(1)

        command = args.pop(1)
        result = self.commands.get(command)()

        if self.error_exit_codes and bool(strtobool(result.decode("utf-8"))) is False:
            sys.exit(1)

    def handlers(self):
        """Returns all registered handlers attached to this API"""
        return self.commands.values()

    def extend(self, cli_api, command_prefix="", sub_command="", **kwargs):
        """Extends this CLI api with the commands present in the provided cli_api object"""
        if sub_command and command_prefix:
            raise ValueError(
                "It is not currently supported to provide both a command_prefix and sub_command"
            )

        if sub_command:
            self.commands[sub_command] = cli_api
        else:
            for name, command in cli_api.commands.items():
                self.commands["{}{}".format(command_prefix, name)] = command

    @property
    def output_format(self):
        return getattr(self, "_output_format", hug.defaults.cli_output_format)

    @output_format.setter
    def output_format(self, formatter):
        self._output_format = formatter

    def __str__(self):
        return "{0}\n\nAvailable Commands:{1}\n".format(
            self.api.doc or self.api.name, "\n\n\t- " + "\n\t- ".join(self.commands.keys())
        )


class ModuleSingleton(type):
    """Defines the module level __hug__ singleton"""

    def __call__(cls, module=None, *args, **kwargs):
        if isinstance(module, API):
            return module

        if type(module) == str:
            if module not in sys.modules:
                sys.modules[module] = ModuleType(module)
            module = sys.modules[module]
        elif module is None:
            return super().__call__(*args, **kwargs)

        if not "__hug__" in module.__dict__:

            def api_auto_instantiate(*args, **kwargs):
                if not hasattr(module, "__hug_serving__"):
                    module.__hug_wsgi__ = module.__hug__.http.server()
                    module.__hug_serving__ = True
                return module.__hug_wsgi__(*args, **kwargs)

            module.__hug__ = super().__call__(module, *args, **kwargs)
            module.__hug_wsgi__ = api_auto_instantiate
        return module.__hug__


class API(object, metaclass=ModuleSingleton):
    """Stores the information necessary to expose API calls within this module externally"""

    __slots__ = (
        "module",
        "_directives",
        "_http",
        "_cli",
        "_context",
        "_context_factory",
        "_delete_context",
        "_startup_handlers",
        "started",
        "name",
        "doc",
        "cli_error_exit_codes",
    )

    def __init__(self, module=None, name="", doc="", cli_error_exit_codes=False):
        self.module = module
        if module:
            self.name = name or module.__name__ or ""
            self.doc = doc or module.__doc__ or ""
        else:
            self.name = name
            self.doc = doc
        self.started = False
        self.cli_error_exit_codes = cli_error_exit_codes

    def directives(self):
        """Returns all directives applicable to this Hug API"""
        directive_sources = chain(
            hug.defaults.directives.items(), getattr(self, "_directives", {}).items()
        )
        return {
            "hug_" + directive_name: directive for directive_name, directive in directive_sources
        }

    def directive(self, name, default=None):
        """Returns the loaded directive with the specified name, or default if passed name is not present"""
        return getattr(self, "_directives", {}).get(
            name, hug.defaults.directives.get(name, default)
        )

    def add_directive(self, directive):
        self._directives = getattr(self, "_directives", {})
        self._directives[directive.__name__] = directive

    def handlers(self):
        """Returns all registered handlers attached to this API"""
        if getattr(self, "_http"):
            yield from self.http.handlers()
        if getattr(self, "_cli"):
            yield from self.cli.handlers()

    @property
    def http(self):
        if not hasattr(self, "_http"):
            self._http = HTTPInterfaceAPI(self)
        return self._http

    @property
    def cli(self):
        if not hasattr(self, "_cli"):
            self._cli = CLIInterfaceAPI(self, error_exit_codes=self.cli_error_exit_codes)
        return self._cli

    @property
    def context_factory(self):
        return getattr(self, "_context_factory", hug.defaults.context_factory)

    @context_factory.setter
    def context_factory(self, context_factory_):
        self._context_factory = context_factory_

    @property
    def delete_context(self):
        return getattr(self, "_delete_context", hug.defaults.delete_context)

    @delete_context.setter
    def delete_context(self, delete_context_):
        self._delete_context = delete_context_

    @property
    def context(self):
        if not hasattr(self, "_context"):
            self._context = {}
        return self._context

    def extend(self, api, route="", base_url="", http=True, cli=True, **kwargs):
        """Adds handlers from a different Hug API to this one - to create a single API"""
        api = API(api)

        if http and hasattr(api, "_http"):
            self.http.extend(api.http, route, base_url, **kwargs)

        if cli and hasattr(api, "_cli"):
            self.cli.extend(api.cli, **kwargs)

        for directive in getattr(api, "_directives", {}).values():
            self.add_directive(directive)

        for startup_handler in api.startup_handlers or ():
            self.add_startup_handler(startup_handler)

    def add_startup_handler(self, handler):
        """Adds a startup handler to the hug api"""
        if not self.startup_handlers:
            self._startup_handlers = []

        self.startup_handlers.append(handler)

    def _ensure_started(self):
        """Marks the API as started and runs all startup handlers"""
        if not self.started:
            async_handlers = [
                startup_handler
                for startup_handler in self.startup_handlers
                if introspect.is_coroutine(startup_handler)
            ]
            if async_handlers:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(
                    asyncio.gather(*[handler(self) for handler in async_handlers], loop=loop)
                )
            for startup_handler in self.startup_handlers:
                if not startup_handler in async_handlers:
                    startup_handler(self)

    @property
    def startup_handlers(self):
        return getattr(self, "_startup_handlers", ())


def from_object(obj):
    """Returns a Hug API instance from a given object (function, class, instance)"""
    return API(obj.__module__)
