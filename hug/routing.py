"""hug/routing.py

Defines the chainable classes responsible for defining the routing of Python functions for use with Falcon
and CLIs

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
import argparse

import os
import re
from functools import wraps

import falcon
from falcon import HTTP_METHODS

import hug.api
import hug.output_format
from hug import introspect
from hug.exceptions import InvalidTypeData

from hug.interface import HTTP


class Router(object):
    """The base chainable router object"""
    __slots__ = ('route', )

    def __init__(self, transform=None, output=None, api=None):
        self.route = {}
        if transform is not None:
            self.route['transform'] = transform
        if output:
            self.route['output'] = output
        if api:
            self.route['api'] = api

    def output(self, formatter, **overrides):
        """Sets the output formatter that should be used to render this route"""
        return self.where(output=formatter, **overrides)

    def transform(self, function, **overrides):
        """Sets the function that should be used to transform the returned Python structure into something
           serializable by specified output format
        """
        return self.where(transform=function, **overrides)

    def api(self, api, **overrides):
        """Sets the API that should contain this route"""
        return self.where(api=api, **overrides)

    def where(self, **overrides):
        """Creates a new route, based on the current route, with the specified overrided values"""
        route_data = self.route.copy()
        route_data.update(overrides)
        return self.__class__(**route_data)


class CLIRouter(Router):
    """The CLIRouter provides a chainable router that can be used to route a CLI command to a Python function"""
    __slots__ = ()

    def __init__(self, name=None, version=None, doc=None, **kwargs):
        super().__init__(**kwargs)
        if name is not None:
            self.route['name'] = name
        if version:
            self.route['version'] = version
        if doc:
            self.route['doc'] = doc

    def name(self, name, **overrides):
        """Sets the name for the CLI interface"""
        return self.where(name=name, **overrides)

    def version(self, version, **overrides):
        """Sets the version for the CLI interface"""
        return self.where(version=version, **overrides)

    def doc(self, documentation, **overrides):
        """Sets the documentation for the CLI interface"""
        return self.where(doc=documentation, **overrides)

    def __call__(self, api_function):
        """Enables exposing a Hug compatible function as a Command Line Interface"""
        api = self.route.get('api', hug.api.from_object(api_function))
        function_spec = getattr(api_function, 'original', api_function)

        if introspect.takes_kargs(function_spec):
            accepted_parameters = introspect.arguments(function_spec, 1)
            karg_method = accepted_parameters[-1]
            nargs_set = True
        else:
            karg_method = None
            accepted_parameters = introspect.arguments(function_spec)
            nargs_set = False

        defaults = {}
        for index, default in enumerate(reversed(function_spec.__defaults__ or ())):
            defaults[accepted_parameters[-(index + 1)]] = default

        required = accepted_parameters[:-(len(function_spec.__defaults__ or ())) or None]


        directives = api.directives()
        use_directives = set(accepted_parameters).intersection(directives.keys())
        output_transform = self.route.get('transform', function_spec.__annotations__.get('return', None))

        is_method = False
        if 'method' in function_spec.__class__.__name__:
            is_method = True
            required = required[1:]
            accepted_parameters = accepted_parameters[1:]

        used_options = {'h', 'help'}
        parser = argparse.ArgumentParser(description=self.route.get('doc', function_spec.__doc__))
        if 'version' in self.route:
            parser.add_argument('-v', '--version', action='version',
                                version="{0} {1}".format(self.route['name'] or function_spec.__name__,
                                                         self.route['version']))
            used_options.update(('v', 'version'))

        annotations = function_spec.__annotations__
        named_directives = {directive_name: directives[directive_name] for directive_name in use_directives}
        for option in accepted_parameters:
            if option in use_directives:
                continue
            elif hasattr(annotations.get(option, None), 'directive'):
                named_directives[option] = annotations[option]
                continue

            if option in required:
                args = (option, )
            else:
                short_option = option[0]
                while short_option in used_options and len(short_option) < len(option):
                    short_option = option[:len(short_option) + 1]

                used_options.add(short_option)
                used_options.add(option)
                if short_option != option:
                    args = ('-{0}'.format(short_option), '--{0}'.format(option))
                else:
                    args = ('--{0}'.format(option), )

            kwargs = {}
            if option in defaults:
                kwargs['default'] = defaults[option]
            if option in annotations:
                annotation = annotations[option]
                if isinstance(annotation, str):
                    kwargs['help'] = annotation
                else:
                    kwargs['type'] = annotation
                    kwargs['help'] = annotation.__doc__
                    kwargs.update(getattr(annotation, 'cli_behaviour', {}))
            if ((kwargs.get('type', None) == bool or kwargs.get('action', None) == 'store_true') and
                    kwargs['default'] == False):
                kwargs['action'] = 'store_true'
                kwargs.pop('type', None)
            elif kwargs.get('action', None) == 'store_true':
                kwargs.pop('action', None) == 'store_true'

            if option == karg_method or ():
                kwargs['nargs'] = '*'
            elif not nargs_set and kwargs.get('action', None) == 'append' and not option in defaults:
                kwargs['nargs'] = '*'
                kwargs.pop('action', '')
                nargs_set = True

            parser.add_argument(*args, **kwargs)

        def cli_interface():
            pass_to_function = vars(parser.parse_args())
            for option, directive in named_directives.items():
                arguments = (defaults[option], ) if option in defaults else ()
                pass_to_function[option] = directive(*arguments, module=api.module)

            if karg_method:
                karg_values = pass_to_function.pop(karg_method, ())
                result = api_function(*karg_values, **pass_to_function)
            else:
                result = api_function(**pass_to_function)
            if output_transform:
                result = output_transform(result)
            if hasattr(result, 'read'):
                result = result.read().decode('utf8')
            if result is not None:
                if cli_interface.output is not None:
                    cli_interface.output(result)
                else:
                    print(result)

        callable_method = api_function
        if named_directives and not getattr(api_function, 'without_directives', None):
            @wraps(api_function)
            def callable_method(*args, **kwargs):
                for parameter, directive in named_directives.items():
                    if parameter in kwargs:
                        continue
                    arguments = (defaults[parameter], ) if parameter in defaults else ()
                    kwargs[parameter] = directive(*arguments, module=api.module)
                return api_function(*args, **kwargs)
            callable_method.without_directives = api_function

        callable_method.__dict__['cli'] = cli_interface
        cli_interface.output = self.route.get('output', None)
        cli_interface.karg_method = karg_method
        return callable_method


class HTTPRouter(Router):
    """The HTTPRouter provides the base concept of a router from an HTTPRequest to a Python function"""
    __slots__ = ()

    def __init__(self, versions=None, parse_body=False, requires=(), parameters=None, defaults={}, status=None,
                 on_invalid=None, output_invalid=None, validate=None, raise_on_invalid=False, **kwargs):
        super().__init__(**kwargs)
        self.route['versions'] = (versions, ) if isinstance(versions, (int, float, None.__class__)) else versions
        if parse_body:
            self.route['parse_body'] = parse_body
        if requires:
            self.route['requires'] = (requires, ) if not isinstance(requires, (tuple, list)) else requires
        if parameters:
            self.route['parameters'] = parameters
        if defaults:
            self.route['defaults'] = defaults
        if status:
            self.route['status'] = status
        if on_invalid:
            self.route['on_invalid'] = on_invalid
        if output_invalid:
            self.route['output_invalid'] = output_invalid
        if validate:
            self.route['validate'] = validate
        if raise_on_invalid:
            self.route['raise_on_invalid'] = raise_on_invalid


    def versions(self, supported, **overrides):
        """Sets the versions that this route should be compatiable with"""
        return self.where(versions=supported, **overrides)

    def parse_body(self, automatic=True, **overrides):
        """Tells hug to automatically parse the input body if it matches a registered input format"""
        return self.where(parse_body=automatic, **overrides)

    def requires(self, requirements, **overrides):
        """Adds additional requirements to the specified route"""
        return self.where(requires=tuple(self.route.get('requires', ())) + tuple(requirements), **overrides)

    def set_status(self, status, **overrides):
        """Sets the status that will be returned by default"""
        return self.where(status=status, **overrides)

    def parameters(self, parameters, **overrides):
        """Sets the custom parameters that will be used instead of those found introspecting the decorated function"""
        return self.where(parameters=parameters, **overrides)

    def defaults(self, defaults, **overrides):
        """Sets the custom defaults that will be used for custom parameters"""
        return self.where(defaults=defaults, **overrides)

    def on_invalid(self, function, **overrides):
        """Sets a function to use to transform data on validation errors.

        Defaults to the transform function if one is set to ensure no special
        handling occurs for invalid data set to `False`.
        """
        return self.where(on_invalid=function, **overrides)

    def output_invalid(self, output_handler, **overrides):
        """Sets an output handler to be used when handler validation fails.

        Defaults to the output formatter set globally for the route.
        """
        return self.where(output_invalid=output_handler, **overrides)

    def validate(self, validation_function, **overrides):
        """Sets the secondary validation fucntion to use for this handler"""
        return self.where(validate=validation_function, **overrides)

    def raise_on_invalid(self, setting=True, **overrides):
        """Sets the route to raise validation errors instead of catching them"""
        return self.where(raise_on_invalid=setting, **overrides)

    def _create_interface(self, api, api_function, catch_exceptions=True):
        interface = HTTP(self.route, api_function, catch_exceptions)
        return (interface, interface.wrapped)


class NotFoundRouter(HTTPRouter):
    """Provides a chainable router that can be used to route 404'd request to a Python function"""
    __slots__ = ()

    def __init__(self, output=None, versions=None, status=falcon.HTTP_NOT_FOUND, **kwargs):
        super().__init__(output=output, versions=versions, status=status, **kwargs)

    def __call__(self, api_function):
        api = self.route.get('api', hug.api.from_object(api_function))
        (interface, callable_method) = self._create_interface(api, api_function)
        for version in self.route['versions']:
            api.set_not_found_handler(interface, version)

        return callable_method


class SinkRouter(HTTPRouter):
    """Provides a chainable router that can be used to route all routes pass a certain base URL (essentially route/*)"""
    __slots__ = ()

    def __init__(self, urls=None, output=None, **kwargs):
        super().__init__(output=output, **kwargs)
        if urls:
            self.route['urls'] = (urls, ) if isinstance(urls, str) else urls

    def __call__(self, api_function):
        api = hug.api.from_object(api_function)
        (interface, callable_method) = self._create_interface(api, api_function)
        for base_url in self.route.get('urls', ("/{0}".format(api_function.__name__), )):
            api.add_sink(interface, base_url)
        return callable_method


class StaticRouter(SinkRouter):
    """Provides a chainable router that can be used to return static files automtically from a set of directories"""
    __slots__ = ('route', )

    def __init__(self, urls=None, output=hug.output_format.file, **kwargs):
        super().__init__(urls=urls, output=output, **kwargs)

    def __call__(self, api_function):
        directories = []
        for directory in api_function():
            path = os.path.abspath(
                directory
            )
            directories.append(path)

        api = self.route.get('api', hug.api.from_object(api_function))
        for base_url in self.route.get('urls', ("/{0}".format(api_function.__name__), )):
            def read_file(request):
                filename = request.relative_uri[len(base_url) + 1:]
                for directory in directories:
                    path = os.path.join(directory, filename)
                    if os.path.isdir(path):
                        new_path = os.path.join(path, "index.html")
                        if os.path.exists(new_path) and os.path.isfile(new_path):
                            path = new_path
                    if os.path.exists(path) and os.path.isfile(path):
                        return path

                hug.redirect.not_found()
            api.add_sink(self._create_interface(api, read_file)[0], base_url)
        return api_function


class ExceptionRouter(HTTPRouter):
    """Provides a chainable router that can be used to route exceptions thrown during request handling"""
    __slots__ = ()

    def __init__(self, exceptions=(Exception, ), output=None, **kwargs):
        super().__init__(output=output, **kwargs)
        self.route['exceptions'] = (exceptions, ) if not isinstance(exceptions, (list, tuple)) else exceptions

    def __call__(self, api_function):
        api = hug.api.from_object(api_function)
        (interface, callable_method) = self._create_interface(api, api_function, catch_exceptions=False)
        for version in self.route['versions']:
            for exception in self.route['exceptions']:
                api.add_exception_handler(exception, interface, version)

        return callable_method


class URLRouter(HTTPRouter):
    """Provides a chainable router that can be used to route a URL to a Python function"""
    __slots__ = ()

    def __init__(self, urls=None, accept=HTTP_METHODS, output=None, examples=(), versions=None,
                 suffixes=(), prefixes=(), response_headers=None, parse_body=True, **kwargs):
        super().__init__(output=output, versions=versions, parse_body=parse_body, **kwargs)
        if urls is not None:
            self.route['urls'] = (urls, ) if isinstance(urls, str) else urls
        if accept:
            self.route['accept'] = (accept, ) if isinstance(accept, str) else accept
        if examples:
            self.route['examples'] = (examples, ) if isinstance(examples, str) else examples
        if suffixes:
            self.route['suffixes'] = (suffixes, ) if isinstance(suffixes, str) else suffixes
        if prefixes:
            self.route['prefixes'] = (prefixes, ) if isinstance(prefixes, str) else prefixes
        if response_headers:
            self.route['response_headers'] = response_headers

    def __call__(self, api_function):
        api = hug.api.from_object(api_function)
        (interface, callable_method) = self._create_interface(api, api_function)

        use_examples = self.route.get('examples', ())
        if not interface.required and not use_examples:
            use_examples = (True, )

        for base_url in self.route.get('urls', ("/{0}".format(api_function.__name__), )):
            expose = [base_url, ]
            for suffix in self.route.get('suffixes', ()):
                if suffix.startswith('/'):
                    expose.append(os.path.join(base_url, suffix.lstrip('/')))
                else:
                    expose.append(base_url + suffix)
            for prefix in self.route.get('prefixes', ()):
                expose.append(prefix + base_url)
            for url in expose:
                handlers = api.routes.setdefault(url, {})
                for method in self.route.get('accept', ()):
                    version_mapping = handlers.setdefault(method.upper(), {})
                    for version in self.route['versions']:
                        version_mapping[version] = interface
                        api.versioned.setdefault(version, {})[callable_method.__name__] = callable_method

        interface.examples = use_examples
        return callable_method

    def urls(self, *urls, **overrides):
        """Sets the URLs that will map to this API call"""
        return self.where(urls=urls, **overrides)

    def accept(self, *accept, **overrides):
        """Sets a list of HTTP methods this router should accept"""
        return self.where(accept=accept, **overrides)

    def get(self, **overrides):
        """Sets the acceptable HTTP method to a GET"""
        return self.where(accept='GET', **overrides)

    def delete(self, **overrides):
        """Sets the acceptable HTTP method to DELETE"""
        return self.where(accept='DELETE', **overrides)

    def post(self, **overrides):
        """Sets the acceptable HTTP method to POST"""
        return self.where(accept='POST', **overrides)

    def put(self, **overrides):
        """Sets the acceptable HTTP method to PUT"""
        return self.where(accept='PUT', **overrides)

    def trace(self, **overrides):
        """Sets the acceptable HTTP method to TRACE"""
        return self.where(accept='TRACE', **overrides)

    def patch(self, **overrides):
        """Sets the acceptable HTTP method to PATCH"""
        return self.where(accept='PATCH', **overrides)

    def options(self, **overrides):
        """Sets the acceptable HTTP method to OPTIONS"""
        return self.where(accept='OPTIONS', **overrides)

    def head(self, **overrides):
        """Sets the acceptable HTTP method to HEAD"""
        return self.where(accept='HEAD', **overrides)

    def connect(self, **overrides):
        """Sets the acceptable HTTP method to CONNECT"""
        return self.where(accept='CONNECT', **overrides)

    def call(self, **overrides):
        """Sets the acceptable HTTP method to all known"""
        return self.where(accept=HTTP_METHODS, **overrides)

    def examples(self, *examples, **overrides):
        """Sets the examples that the route should use"""
        return self.where(examples=examples, **overrides)

    def suffixes(self, *suffixes, **overrides):
        """Sets the suffixes supported by the route"""
        return self.where(suffixes=suffixes, **overrides)

    def prefixes(self, *prefixes, **overrides):
        """Sets the prefixes supported by the route"""
        return self.where(prefixes=prefixes, **overrides)

    def response_headers(self, headers, **overrides):
        """Sets the response headers automatically injected by the router"""
        return self.where(response_headers=headers, **overrides)

    def add_response_headers(self, headers, **overrides):
        """Adds the specified response headers while keeping existing ones in-tact"""
        response_headers = self.route.get('response_headers', {}).copy()
        response_headers.update(headers)
        return self.where(response_headers=response_headers, **overrides)

    def cache(self, private=False, max_age=31536000, s_maxage=None, no_cache=False, no_store=False,
              must_revalidate=False, **overrides):
        """Convience method for quickly adding cache header to route"""
        parts = ('private' if private else 'public', 'max-age={0}'.format(max_age),
                 's-maxage={0}'.format(s_maxage) if s_maxage is not None else None, no_cache and 'no-cache',
                 no_store and 'no-store', must_revalidate and 'must-revalidate')
        return self.add_response_headers({'cache-control': ', '.join(filter(bool, parts))}, **overrides)

    def allow_origins(self, *origins, methods=None, **overrides):
        """Convience method for quickly allowing other resources to access this one"""
        headers = {'Access-Control-Allow-Origin': ', '.join(origins) if origins else '*'}
        if methods:
            headers['Access-Control-Allow-Methods'] = ', '.join(methods)
        return self.add_response_headers(headers, **overrides)
