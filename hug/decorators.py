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
import argparse
import os
import sys
from collections import OrderedDict, namedtuple
from functools import partial, wraps
from itertools import chain
from wsgiref.simple_server import make_server

import falcon
from falcon import HTTP_BAD_REQUEST, HTTP_METHODS

import hug.defaults
import hug.output_format
from hug.exceptions import InvalidTypeData
from hug.format import underscore
from hug.run import INTRO, server

AUTO_INCLUDE = {'request', 'response'}


class HugAPI(object):
    '''Stores the information necessary to expose API calls within this module externally'''
    __slots__ = ('module', 'versions', 'routes', '_output_format', '_input_format', '_directives', 'versioned',
                 '_middleware', '_not_found_handlers')

    def __init__(self, module):
        self.module = module
        self.versions = set()
        self.routes = OrderedDict()
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

    def extend(self, module, route=""):
        '''Adds handlers from a different Hug API module to this one - to create a single API'''
        for item_route, handler in module.__hug__.routes.items():
            self.routes[route + item_route] = handler

        for directive in getattr(module.__hug__, '_directives', {}).values():
            self.add_directive(directive)

        for middleware in (module.__hug__.middleware or ()):
            self.add_middleware(middleware)

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


def default_output_format(content_type='application/json', apply_globally=False):
    '''A decorator that allows you to override the default output format for an API'''
    def decorator(formatter):
        module = _api_module(formatter.__module__)
        formatter = hug.output_format.content_type(content_type)(formatter)
        if apply_globally:
            hug.defaults.output_format = formatter
        else:
            module.__hug__.output_format = formatter
        return formatter
    return decorator


def default_input_format(content_type='application/json', apply_globally=False):
    '''A decorator that allows you to override the default output format for an API'''
    def decorator(formatter):
        module = _api_module(formatter.__module__)
        formatter = hug.output_format.content_type(content_type)(formatter)
        if apply_globally:
            hug.defaults.input_format[content_type] = formatter
        else:
            module.__hug__.set_input_format(content_type, formatter)
        return formatter
    return decorator


def directive(apply_globally=True):
    '''A decorator that registers a single hug directive'''
    def decorator(directive_method):
        if apply_globally:
            hug.defaults.directives[underscore(directive_method.__name__)] = directive_method
        else:
            module = _api_module(directive_method.__module__)
            module.__hug__.add_directive(directive_method)
        directive_method.directive = True
        return directive_method
    return decorator


def request_middleware():
    '''Registers a middleware function that will be called on every request'''
    def decorator(middleware_method):
        module = _api_module(middleware_method.__module__)
        middleware_method.__self__ = middleware_method
        module.__hug__.add_middleware(namedtuple('MiddlewareRouter', ('process_request', ))(middleware_method))
        return middleware_method
    return decorator


def response_middleware():
    '''Registers a middleware function that will be called on every response'''
    def decorator(middleware_method):
        module = _api_module(middleware_method.__module__)
        middleware_method.__self__ = middleware_method
        module.__hug__.add_middleware(namedtuple('MiddlewareRouter', ('process_response', ))(middleware_method))
        return middleware_method
    return decorator


def extend_api(route=""):
    '''Extends the current api, with handlers from an imported api. Optionally provide a route that prefixes access'''
    def decorator(extend_with):
        module = _api_module(extend_with.__module__)
        for api in extend_with():
            module.__hug__.extend(api, route)
        return extend_with
    return decorator


def _api_module(module_name):
    module = sys.modules[module_name]
    if not '__hug__' in module.__dict__:
        def api_auto_instantiate(*kargs, **kwargs):
            if not hasattr(module, '__hug_serving__'):
                module.__hug_wsgi__ = server(module)
                module.__hug_serving__ = True
            return module.__hug_wsgi__(*kargs, **kwargs)
        module.__hug__ = HugAPI(module)
        module.__hug_wsgi__ = api_auto_instantiate
    return module


def _marshmallow_schema(marshmallow):
    '''Dynamically generates a hug style type handler from a Marshmallow style schema'''
    def marshmallow_type(input_data):
        result, errors = marshmallow.loads(input_data) if isinstance(input_data, str) else marshmallow.load(input_data)
        if errors:
            raise InvalidTypeData('Invalid {0} passed in'.format(marshmallow.__class__.__name__), errors)
        return result

    marshmallow_type.__doc__ = marshmallow.__doc__
    marshmallow_type.__name__ = marshmallow.__class__.__name__
    return marshmallow_type


def _create_interface(module, api_function, parameters=None, defaults={}, output=None, versions=None,
                      parse_body=True, set_status=False, transform=None, requires=()):
    '''Creates the request handling interface method for the given API function'''
    if not parameters:
        accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount]
        defaults = {}
        for index, default in enumerate(reversed(api_function.__defaults__ or ())):
            defaults[accepted_parameters[-(index + 1)]] = default

        required = accepted_parameters[:-(len(api_function.__defaults__ or ())) or None]
    else:
        accepted_parameters = tuple(parameters)
        required = tuple([p for p in accepted_parameters if p not in defaults])

    takes_kwargs = bool(api_function.__code__.co_flags & 0x08)
    function_output = output or module.__hug__.output_format
    function_output_args = (AUTO_INCLUDE.intersection(function_output.__code__.co_varnames) if
                            hasattr(function_output, '__code__') else ())
    default_kwargs = {}
    directives = module.__hug__.directives()
    use_directives = set(accepted_parameters).intersection(directives.keys())
    if transform is None and not isinstance(api_function.__annotations__.get('return', None), (str, type(None))):
        transform = api_function.__annotations__['return']

    if hasattr(transform, 'dump'):
        transform = transform.dump
        output_type = transform
    else:
        output_type = transform or api_function.__annotations__.get('return', None)

    if transform and hasattr(transform, '__code__'):
        transform_args = AUTO_INCLUDE.intersection(transform.__code__.co_varnames)

    is_method = False
    if 'method' in api_function.__class__.__name__:
        is_method = True
        required = required[1:]

    input_transformations = {}
    named_directives = {directive_name: directives[directive_name] for directive_name in use_directives}
    for name, transformer in api_function.__annotations__.items():
        if isinstance(transformer, str):
            continue
        elif hasattr(transformer, 'directive'):
            named_directives[name] = transformer
            continue

        if hasattr(transformer, 'load'):
            transformer = _marshmallow_schema(transformer)
        elif hasattr(transformer, 'deserialize'):
            transformer = transformer.deserialize

        input_transformations[name] = transformer

    def interface(request, response, api_version=None, **kwargs):
        if set_status:
            response.status = set_status

        if function_output_args:
            function_output_kwargs = {}
            if 'response' in function_output_args:
                function_output_kwargs['response'] = response
            if 'request' in function_output_args:
                function_output_kwargs['request'] = request
        else:
            function_output_kwargs = default_kwargs

        api_version = int(api_version) if api_version is not None else api_version
        if callable(function_output.content_type):
            response.content_type = function_output.content_type(request=request, response=response)
        else:
            response.content_type = function_output.content_type
        for requirement in requires:
            conclusion = requirement(response=response, request=request, module=module, api_version=api_version)
            if conclusion is not True:
                if conclusion:
                    response.data = function_output(conclusion, **function_output_kwargs)
                return

        input_parameters = kwargs
        input_parameters.update(request.params)
        body_formatting_handler = parse_body and module.__hug__.input_format(request.content_type)
        if body_formatting_handler:
            body = body_formatting_handler(request.stream.read().decode('utf8'))
            if 'body' in accepted_parameters:
                input_parameters['body'] = body
            if isinstance(body, dict):
                input_parameters.update(body)

        errors = {}
        for key, type_handler in input_transformations.items():
            try:
                if key in input_parameters:
                    input_parameters[key] = type_handler(input_parameters[key])
            except InvalidTypeData as error:
                errors[key] = error.reasons or str(error.message)
            except Exception as error:
                if hasattr(error, 'args') and error.args:
                    errors[key] = error.args[0]
                else:
                    errors[key] = str(error)

        if 'request' in accepted_parameters:
            input_parameters['request'] = request
        if 'response' in accepted_parameters:
            input_parameters['response'] = response
        if 'api_version' in accepted_parameters:
            input_parameters['api_version'] = api_version
        for parameter, directive in named_directives.items():
            arguments = (defaults[parameter], ) if parameter in defaults else ()
            input_parameters[parameter] = directive(*arguments, response=response, request=request,  module=module,
                                                    api_version=api_version)
        for require in required:
            if not require in input_parameters:
                errors[require] = "Required parameter not supplied"
        if errors:
            response.data = function_output({"errors": errors}, **function_output_kwargs)
            response.status = HTTP_BAD_REQUEST
            return

        if not takes_kwargs:
            input_parameters = {key: value for key, value in input_parameters.items() if key in accepted_parameters}

        to_return = api_function(**input_parameters)
        if transform and not (isinstance(transform, type) and isinstance(to_return, transform)):
            if transform_args:
                extra_kwargs = {}
                if 'response' in transform_args:
                    extra_kwargs['response'] = response
                if 'request' in transform_args:
                    extra_kwargs['request'] = request
                to_return = transform(to_return, **extra_kwargs)
            else:
                to_return = transform(to_return)

        to_return = function_output(to_return, **function_output_kwargs)
        if hasattr(to_return, 'read'):
            size = os.path.isfile(to_return.name) if hasattr(to_return, 'name') else None
            if request.range and size:
                start, end = request.range
                if end < 0:
                    end = size + end
                end = min(end, size)
                length = end - start + 1
                to_return.seek(start)
                response.data = to_return.read(length)
                response.status = falcon.HTTP_206
                response.content_range = (start, end, size)
                to_return.close()
            else:
                response.stream = to_return
                if size:
                    response.stream_len = size
        else:
            response.data = to_return

    if versions:
        module.__hug__.versions.update(versions)

    callable_method = api_function
    if named_directives and not getattr(api_function, 'without_directives', None):
        @wraps(api_function)
        def callable_method(*args, **kwargs):
            for parameter, directive in named_directives.items():
                if parameter in kwargs:
                    continue
                arguments = (defaults[parameter], ) if parameter in defaults else ()
                kwargs[parameter] = directive(*arguments, module=module,
                                    api_version=max(versions, key=lambda version: version or -1) if versions else None)
            return api_function(*args, **kwargs)
        callable_method.interface = interface
        callable_method.without_directives = api_function

    if is_method:
        api_function.__dict__['interface'] = interface
    else:
        api_function.interface = interface
    interface.api_function = api_function
    interface.output_format = function_output
    interface.defaults = defaults
    interface.accepted_parameters = accepted_parameters
    interface.content_type = function_output.content_type
    interface.required = required
    interface.output_type = output_type if isinstance(output_type, (str, type(None))) else output_type.__doc__
    return (interface, callable_method)


def not_found(output=None, versions=None, parse_body=False, transform=None, requires=()):
    '''A decorator to register a 404 handler'''
    versions = (versions, ) if isinstance(versions, (int, float, None.__class__)) else versions
    requires = (requires, ) if not isinstance(requires, (tuple, list)) else requires

    def decorator(api_function):
        module = _api_module(api_function.__module__)
        (interface, callable_method) = _create_interface(module, api_function, output=output,
                                                         versions=versions, parse_body=parse_body,
                                                         set_status=falcon.HTTP_NOT_FOUND, transform=transform,
                                                         requires=requires)

        for version in versions:
            module.__hug__.set_not_found_handler(interface, version)

        return callable_method
    return decorator


def call(urls=None, accept=HTTP_METHODS, parameters=None, defaults={}, output=None, examples=(), versions=None,
         parse_body=True, transform=None, requires=()):
    '''Defines the base Hug API creating decorator, which exposes normal python methods as HTTP APIs'''
    urls = (urls, ) if isinstance(urls, str) else urls
    examples = (examples, ) if isinstance(examples, str) else examples
    versions = (versions, ) if isinstance(versions, (int, float, None.__class__)) else versions
    requires = (requires, ) if not isinstance(requires, (tuple, list)) else requires

    def decorator(api_function):
        module = _api_module(api_function.__module__)
        (interface, callable_method) = _create_interface(module, api_function, output=output,
                                                         parameters=parameters, defaults=defaults,
                                                         versions=versions, parse_body=parse_body, transform=transform,
                                                         requires=requires)

        use_examples = examples
        if not interface.required and not use_examples:
            use_examples = (True, )
        for url in urls or ("/{0}".format(api_function.__name__), ):
            handlers = module.__hug__.routes.setdefault(url, {})
            for method in accept:
                version_mapping = handlers.setdefault(method.upper(), {})
                for version in versions:
                    version_mapping[version] = interface
                    module.__hug__.versioned.setdefault(version, {})[callable_method.__name__] = callable_method

        interface.examples = use_examples
        return callable_method
    return decorator


def cli(name=None, version=None, doc=None, transform=None, output=None):
    '''Enables exposing a Hug compatible function as a Command Line Interface'''
    def decorator(api_function):
        module = module = _api_module(api_function.__module__)
        takes_kargs = bool(api_function.__code__.co_flags & 0x04)
        accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount + (1 if takes_kargs else 0)]
        directives = module.__hug__.directives()
        use_directives = set(accepted_parameters).intersection(directives.keys())
        output_transform = transform or api_function.__annotations__.get('return', None)

        defaults = {}
        for index, default in enumerate(reversed(api_function.__defaults__ or ())):
            accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount + 1]
            defaults[accepted_parameters[-(index + 1)]] = default
        required = accepted_parameters[:-(len(api_function.__defaults__ or ())) or None]
        is_method = False
        if 'method' in api_function.__class__.__name__:
            is_method = True
            required = required[1:]
        karg_method = accepted_parameters[-1] if takes_kargs else None

        used_options = set()
        parser = argparse.ArgumentParser(description=doc or api_function.__doc__)
        if version:
            parser.add_argument('-v', '--version', action='version',
                                version="{0} {1}".format(name or api_function.__name__, version))
            used_options.update(('v', 'version'))

        annotations = api_function.__annotations__
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
            if kwargs.get('type', None) == bool and kwargs['default'] == False:
                kwargs['action'] = 'store_true'
                kwargs.pop('type', None)
            if option == karg_method:
                kwargs['nargs'] = '*'

            parser.add_argument(*args, **kwargs)

        def cli_interface():
            pass_to_function = vars(parser.parse_args())
            for option, directive in named_directives.items():
                arguments = (defaults[option], ) if option in defaults else ()
                pass_to_function[option] = directive(*arguments, module=module)

            if karg_method:
                karg_values = pass_to_function.pop(karg_method, ())
                result = api_function(*karg_values, **pass_to_function)
            else:
                result = api_function(**pass_to_function)
            if output_transform:
                result = output_transform(result)
            if hasattr(result, 'read'):
                result = result.read().decode('utf8')
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
                    kwargs[parameter] = directive(*arguments, module=module)
                return api_function(*args, **kwargs)
            callable_method.without_directives = api_function

        if is_method:
            callable_method.__dict__['cli'] = cli_interface
        else:
            callable_method.cli = cli_interface
        cli_interface.output = output
        cli_interface.karg_method = karg_method
        return callable_method
    return decorator


for method in HTTP_METHODS:
    method_handler = partial(call, accept=(method, ))
    method_handler.__doc__ = "Exposes a Python method externally as an HTTP {0} method".format(method.upper())
    globals()[method.lower()] = method_handler
