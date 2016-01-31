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
import mimetypes
import re
from collections import OrderedDict, namedtuple
from functools import wraps

import falcon
from falcon import HTTP_BAD_REQUEST, HTTP_METHODS

import hug.api
import hug.defaults
import hug.output_format
from hug.exceptions import InvalidTypeData

AUTO_INCLUDE = {'request', 'response'}
RE_CHARSET = re.compile("charset=(?P<charset>[^;]+)")


class Router(object):
    '''The base chainable router object'''
    __slots__ = ('route', )

    def __init__(self, transform=None, output=None):
        self.route = {'transform': transform, 'output': output}

    def output(self, formatter, **overrides):
        '''Sets the output formatter that should be used to render this route'''
        return self.where(output=formatter, **overrides)

    def transform(self, function, **overrides):
        '''Sets the function that should be used to transform the returned Python structure into something
           serializable by specified output format
        '''
        return self.where(transform=function, **overrides)

    def where(self, **overrides):
        '''Creates a new route, based on the current route, with the specified overrided values'''
        route_data = self.route.copy()
        route_data.update(overrides)
        return self.__class__(**route_data)


class CLIRouter(Router):
    '''The CLIRouter provides a chainable router that can be used to route a CLI command to a Python function'''

    def __init__(self, name=None, version=None, doc=None, transform=None, output=None):
        super().__init__(transform=transform, output=output)
        self.route['name'] = name
        self.route['version'] = version
        self.route['doc'] = doc

    def name(self, name, **overrides):
        '''Sets the name for the CLI interface'''
        return self.where(name=name, **overrides)

    def version(self, version, **overrides):
        '''Sets the version for the CLI interface'''
        return self.where(version=version, **overrides)

    def doc(self, documentation, **overrides):
        '''Sets the documentation for the CLI interface'''
        return self.where(doc=documentation, **overrides)

    def __call__(self, api_function):
        '''Enables exposing a Hug compatible function as a Command Line Interface'''
        api = hug.api.from_object(api_function)

        takes_kargs = bool(api_function.__code__.co_flags & 0x04)
        if takes_kargs:
            accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount + 1]
            karg_method = accepted_parameters[-1]
            nargs_set = True
        else:
            karg_method = None
            accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount]
            nargs_set = False

        defaults = {}
        for index, default in enumerate(reversed(api_function.__defaults__ or ())):
            defaults[accepted_parameters[-(index + 1)]] = default

        required = accepted_parameters[:-(len(api_function.__defaults__ or ())) or None]


        directives = api.directives()
        use_directives = set(accepted_parameters).intersection(directives.keys())
        output_transform = self.route['transform'] or api_function.__annotations__.get('return', None)

        is_method = False
        if 'method' in api_function.__class__.__name__:
            is_method = True
            required = required[1:]
            accepted_parameters = accepted_parameters[1:]

        used_options = {'h', 'help'}
        parser = argparse.ArgumentParser(description=self.route['doc'] or api_function.__doc__)
        if self.route['version']:
            parser.add_argument('-v', '--version', action='version',
                                version="{0} {1}".format(self.route['name'] or api_function.__name__,
                                                         self.route['version']))
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

        if is_method:
            callable_method.__dict__['cli'] = cli_interface
        else:
            callable_method.cli = cli_interface
        cli_interface.output = self.route['output']
        cli_interface.karg_method = karg_method
        return callable_method


class HTTPRouter(Router):
    '''The HTTPRouter provides the base concept of a router from an HTTPRequest to a Python function'''

    def __init__(self, output=None, versions=None, parse_body=False, transform=None, requires=(), parameters=None,
                 defaults={}, status=None, on_invalid=None):
        super().__init__(output=output, transform=transform)
        self.route['versions'] = (versions, ) if isinstance(versions, (int, float, None.__class__)) else versions
        self.route['parse_body'] = parse_body
        self.route['requires'] = (requires, ) if not isinstance(requires, (tuple, list)) else requires
        self.route['parameters'] = parameters
        self.route['defaults'] = defaults
        self.route['status'] = status
        self.route['on_invalid'] = on_invalid

    def versions(self, supported, **overrides):
        '''Sets the versions that this route should be compatiable with'''
        return self.where(versions=supported, **overrides)

    def parse_body(self, automatic=True, **overrides):
        '''Tells hug to automatically parse the input body if it matches a registered input format'''
        return self.where(parse_body=automatic, **overrides)

    def requires(self, requirements, **overrides):
        '''Adds additional requirements to the specified route'''
        return self.where(requires=tuple(self.route.get('requires', ())) + tuple(requirements), **overrides)

    def set_status(self, status, **overrides):
        '''Sets the status that will be returned by default'''
        return self.where(status=status, **overrides)

    def parameters(self, parameters, **overrides):
        '''Sets the custom parameters that will be used instead of those found introspecting the decorated function'''
        return self.where(parameters=parameters, **overrides)

    def defaults(self, defaults, **overrides):
        '''Sets the custom defaults that will be used for custom parameters'''
        return self.where(defaults=defaults, **overrides)

    def on_invalid(self, function, **overrides):
        '''Sets a function to use to transform data on validation errors
            Defaults to the transform function if one is set
            To ensure no special handling occurs for invalid data set to `False`
        '''
        return self.where(on_invalid=function, **overrides)

    def _marshmallow_schema(self, marshmallow):
        '''Dynamically generates a hug style type handler from a Marshmallow style schema'''
        def marshmallow_type(input_data):
            result, errors = marshmallow.loads(input_data) if isinstance(input_data, str) else marshmallow.load(input_data)
            if errors:
                raise InvalidTypeData('Invalid {0} passed in'.format(marshmallow.__class__.__name__), errors)
            return result

        marshmallow_type.__doc__ = marshmallow.__doc__
        marshmallow_type.__name__ = marshmallow.__class__.__name__
        return marshmallow_type

    def _create_interface(self, api, api_function, catch_exceptions=True):
        module = api.module
        defaults = self.route['defaults']
        if not self.route['parameters']:
            accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount]
            defaults = {}
            for index, default in enumerate(reversed(api_function.__defaults__ or ())):
                defaults[accepted_parameters[-(index + 1)]] = default

            required = accepted_parameters[:-(len(api_function.__defaults__ or ())) or None]
        else:
            accepted_parameters = tuple(self.route['parameters'])
            required = tuple([parameter for parameter in accepted_parameters if parameter not in
                              self.route['defaults']])


        takes_kwargs = bool(api_function.__code__.co_flags & 0x08)
        function_output = self.route['output'] or api.output_format
        function_output_args = (AUTO_INCLUDE.intersection(function_output.__code__.co_varnames) if
                                hasattr(function_output, '__code__') else ())
        default_kwargs = {}
        directives = api.directives()
        use_directives = set(accepted_parameters).intersection(directives.keys())
        transform = self.route['transform']
        if transform is None and not isinstance(api_function.__annotations__.get('return', None),
                                                     (str, type(None))):
            transform = api_function.__annotations__['return']

        if hasattr(transform, 'dump'):
            transform = transform.dump
            output_type = transform
        else:
            output_type = transform or api_function.__annotations__.get('return', None)

        transform_args = ()
        if transform and hasattr(transform, '__code__'):
            transform_args = AUTO_INCLUDE.intersection(transform.__code__.co_varnames)

        on_invalid = self.route['on_invalid']
        if on_invalid is None and transform:
            on_invalid = transform
            on_invalid_args = transform_args
        else:
            on_invalid_args = ()
            if on_invalid and hasattr(on_invalid, '__code__'):
                on_invalid_args = AUTO_INCLUDE.intersection(on_invalid.__code__.co_varnames)

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
                transformer = self._marshmallow_schema(transformer)
            elif hasattr(transformer, 'deserialize'):
                transformer = transformer.deserialize

            input_transformations[name] = transformer

        parse_body = self.route['parse_body']
        requires = self.route['requires']
        set_status = self.route['status']
        response_headers = tuple(self.route.get('response_headers', {}).items())
        def interface(request, response, api_version=None, **kwargs):
            if not catch_exceptions:
                exception_types = ()
            else:
                exception_types = api.exception_handlers(api_version)
                exception_types = tuple(exception_types.keys()) if exception_types else ()
            try:
                for header_name, header_value in response_headers:
                    response.set_header(header_name, header_value)

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
                if parse_body and request.content_length is not None:
                    body = request.stream
                    content_type = request.content_type
                    encoding = None
                    if content_type and ";" in content_type:
                        content_type, rest = content_type.split(";", 1)
                        charset = RE_CHARSET.search(rest).groupdict()
                        encoding = charset.get('charset', encoding).strip()

                    body_formatting_handler = body and api.input_format(content_type)
                    if body_formatting_handler:
                        if encoding is not None:
                            body = body_formatting_handler(body, encoding)
                        else:
                            body = body_formatting_handler(body)
                    if 'body' in accepted_parameters:
                        input_parameters['body'] = body
                    if isinstance(body, dict):
                        input_parameters.update(body)
                elif 'body' in accepted_parameters:
                    input_parameters['body'] = None

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
                    input_parameters[parameter] = directive(*arguments, response=response, request=request,
                                                            module=module, api_version=api_version)
                for require in required:
                    if not require in input_parameters:
                        errors[require] = "Required parameter not supplied"
                if errors:
                    data = {'errors': errors}
                    if on_invalid:
                        if on_invalid_args:
                            extra_kwargs = {}
                            if 'response' in on_invalid_args:
                                extra_kwargs['response'] = response
                            if 'request' in on_invalid_args:
                                extra_kwargs['request'] = request
                            data = on_invalid(data, **extra_kwargs)
                        else:
                            data = on_invalid(data)

                    response.status = HTTP_BAD_REQUEST
                    response.data = function_output(data, **function_output_kwargs)
                    return

                if not takes_kwargs:
                    input_parameters = {key: value for key, value in input_parameters.items() if
                                        key in accepted_parameters}

                to_return = api_function(**input_parameters)
                if hasattr(to_return, 'interface'):
                    to_return.interface(request, response, api_version=None, **kwargs)
                    return

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
                    size = None
                    if hasattr(to_return, 'name') and os.path.isfile(to_return.name):
                        size = os.path.getsize(to_return.name)
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
            except exception_types as exception:
                handler = None
                if type(exception) in exception_types:
                    handler = api.exception_handlers(api_version)[type(exception)]
                else:
                    for exception_type, exception_handler in tuple(api.exception_handlers(api_version).items())[::-1]:
                        if isinstance(exception, exception_type):
                            handler = exception_handler
                handler(request=request, response=response, exception=exception, **kwargs)

        if self.route['versions']:
            api.versions.update(self.route['versions'])

        callable_method = api_function
        if named_directives and not getattr(api_function, 'without_directives', None):
            @wraps(api_function)
            def callable_method(*args, **kwargs):
                for parameter, directive in named_directives.items():
                    if parameter in kwargs:
                        continue
                    arguments = (defaults[parameter], ) if parameter in defaults else ()
                    kwargs[parameter] = directive(*arguments, module=module,
                                        api_version=max(self.route['versions'], key=lambda version: version or -1)
                                        if self.route['versions'] else None)
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


class NotFoundRouter(HTTPRouter):
    '''Provides a chainable router that can be used to route 404'd request to a Python function'''

    def __init__(self, output=None, versions=None, parse_body=False, transform=None, requires=(), parameters=None,
                 defaults={}, status=falcon.HTTP_NOT_FOUND, on_invalid=None):
        super().__init__(output=output, versions=versions, parse_body=parse_body, transform=transform,
                         requires=requires, parameters=parameters, defaults=defaults, status=status,
                         on_invalid=on_invalid)

    def __call__(self, api_function):
        api = hug.api.from_object(api_function)
        (interface, callable_method) = self._create_interface(api, api_function)
        for version in self.route['versions']:
            api.set_not_found_handler(interface, version)

        return callable_method

class SinkRouter(HTTPRouter):
    def __init__(self, urls=None, output=None, versions=None, parse_body=False, transform=None, requires=(), parameters=None,
                 defaults={}, status=None, on_invalid=None):
        super().__init__(output=output, versions=versions, parse_body=parse_body, transform=transform,
                         requires=requires, parameters=parameters, defaults=defaults, status=status,
                         on_invalid=on_invalid)
        self.route['urls'] = (urls, ) if isinstance(urls, str) else urls

    def __call__(self, api_function):
        api = hug.api.from_object(api_function)
        (interface, callable_method) = self._create_interface(api, api_function)
        for base_url in self.route['urls'] or ("/{0}".format(api_function.__name__), ):
            api.add_sink(interface, base_url)
        return callable_method

class StaticRouter(object):
    def __init__(self, urls=None):
        self.route = {
            'urls': (urls, ) if isinstance(urls, str) else urls
        }

    def _create_handler(self, base_url, directories):
        def static_handler(request, response):
            filename = request.relative_uri[len(base_url) + 1:]
            for directory in directories:
                path = os.path.join(directory, filename)
                
                if os.path.isdir(path):
                    new_path = os.path.join(path, "index.html")
                    if os.path.exists(new_path) and os.path.isfile(new_path):
                        path = new_path
                if os.path.exists(path) and os.path.isfile(path):
                    filetype = mimetypes.guess_type(path, strict=True)[0]
                    if not filetype:
                        filetype = 'text/plain'
                    response.content_type = filetype
                    response.data = open(path, 'rb').read()
                    return
                
                response.status = falcon.HTTP_NOT_FOUND
                response.data = b"File does not exist"
        return static_handler

    def __call__(self, api_function):
        directories = []
        for directory in api_function():
            path = os.path.abspath(
                directory
            )
            directories.append(path)

        api = hug.api.from_object(api_function)
        for base_url in self.route['urls'] or ("/{0}".format(api_function.__name__), ):
            api.add_sink(self._create_handler(base_url, directories), base_url)
        return api_function


class ExceptionRouter(HTTPRouter):
    '''Provides a chainable router that can be used to route exceptions thrown during request handling'''

    def __init__(self, exceptions=(Exception, ), output=None, versions=None, parse_body=False, transform=None,
                 requires=(), parameters=None, defaults={}, status=falcon.HTTP_NOT_FOUND, on_invalid=None):
        super().__init__(output=output, versions=versions, parse_body=parse_body, transform=transform,
                         requires=requires, parameters=parameters, defaults=defaults, status=status,
                         on_invalid=on_invalid)
        self.route['exceptions'] = (exceptions, ) if not isinstance(exceptions, (list, tuple)) else exceptions

    def __call__(self, api_function):
        api = hug.api.from_object(api_function)
        (interface, callable_method) = self._create_interface(api, api_function, catch_exceptions=False)
        for version in self.route['versions']:
            for exception in self.route['exceptions']:
                api.add_exception_handler(exception, interface, version)

        return callable_method


class URLRouter(HTTPRouter):
    '''Provides a chainable router that can be used to route a URL to a Python function'''

    def __init__(self, urls=None, accept=HTTP_METHODS, parameters=None, defaults={}, output=None, examples=(),
                 versions=None, parse_body=True, transform=None, requires=(), status=None, on_invalid=None,
                 suffixes=(), prefixes=(), response_headers=None):
        super().__init__(output=output, versions=versions, parse_body=parse_body, transform=transform,
                         requires=requires, parameters=parameters, defaults=defaults, status=status,
                         on_invalid=on_invalid)
        self.route['urls'] = (urls, ) if isinstance(urls, str) else urls
        self.route['accept'] = (accept, ) if isinstance(accept, str) else accept
        self.route['examples'] = (examples, ) if isinstance(examples, str) else examples
        self.route['suffixes'] = (suffixes, ) if isinstance(suffixes, str) else suffixes
        self.route['prefixes'] = (prefixes, ) if isinstance(prefixes, str) else prefixes
        if response_headers:
            self.route['response_headers'] = response_headers

    def __call__(self, api_function):
        api = hug.api.from_object(api_function)
        (interface, callable_method) = self._create_interface(api, api_function)

        use_examples = self.route['examples']
        if not interface.required and not use_examples:
            use_examples = (True, )

        for base_url in self.route['urls'] or ("/{0}".format(api_function.__name__), ):
            expose = [base_url, ]
            for suffix in self.route['suffixes']:
                if suffix.startswith('/'):
                    expose.append(os.path.join(base_url, suffix.lstrip('/')))
                else:
                    expose.append(base_url + suffix)
            for prefix in self.route['prefixes']:
                expose.append(prefix + base_url)
            for url in expose:
                handlers = api.routes.setdefault(url, {})
                for method in self.route['accept']:
                    version_mapping = handlers.setdefault(method.upper(), {})
                    for version in self.route['versions']:
                        version_mapping[version] = interface
                        api.versioned.setdefault(version, {})[callable_method.__name__] = callable_method

        interface.examples = use_examples
        return callable_method

    def urls(self, *urls, **overrides):
        '''Sets the URLs that will map to this API call'''
        return self.where(urls=urls, **overrides)

    def accept(self, *accept, **overrides):
        '''Sets a list of HTTP methods this router should accept'''
        return self.where(accept=accept, **overrides)

    def get(self, **overrides):
        '''Sets the acceptable HTTP method to a GET'''
        return self.where(accept='GET', **overrides)

    def delete(self, **overrides):
        '''Sets the acceptable HTTP method to DELETE'''
        return self.where(accept='DELETE', **overrides)

    def post(self, **overrides):
        '''Sets the acceptable HTTP method to POST'''
        return self.where(accept='POST', **overrides)

    def put(self, **overrides):
        '''Sets the acceptable HTTP method to PUT'''
        return self.where(accept='PUT', **overrides)

    def trace(self, **overrides):
        '''Sets the acceptable HTTP method to TRACE'''
        return self.where(accept='TRACE', **overrides)

    def patch(self, **overrides):
        '''Sets the acceptable HTTP method to PATCH'''
        return self.where(accept='PATCH', **overrides)

    def options(self, **overrides):
        '''Sets the acceptable HTTP method to OPTIONS'''
        return self.where(accept='OPTIONS', **overrides)

    def head(self, **overrides):
        '''Sets the acceptable HTTP method to HEAD'''
        return self.where(accept='HEAD', **overrides)

    def connect(self, **overrides):
        '''Sets the acceptable HTTP method to CONNECT'''
        return self.where(accept='CONNECT', **overrides)

    def call(self, **overrides):
        '''Sets the acceptable HTTP method to all known'''
        return self.where(accept=HTTP_METHODS, **overrides)

    def examples(self, *examples, **overrides):
        '''Sets the examples that the route should use'''
        return self.where(examples=examples, **overrides)

    def suffixes(self, *suffixes, **overrides):
        '''Sets the suffixes supported by the route'''
        return self.where(suffixes=suffixes, **overrides)

    def prefixes(self, *prefixes, **overrides):
        '''Sets the prefixes supported by the route'''
        return self.where(prefixes=prefixes, **overrides)

    def response_headers(self, headers, **overrides):
        '''Sets the response headers automatically injected by the router'''
        return self.where(response_headers=headers, **overrides)

    def add_response_headers(self, headers, **overrides):
        '''Adds the specified response headers while keeping existing ones in-tact'''
        response_headers = self.route.get('response_headers', {}).copy()
        response_headers.update(headers)
        return self.where(response_headers=response_headers, **overrides)

    def cache(self, private=False, max_age=31536000, s_maxage=None, no_cache=False, no_store=False,
              must_revalidate=False, **overrides):
        '''Convience method for quickly adding cache header to route'''
        parts = ('private' if private else 'public', 'max-age={0}'.format(max_age),
                 's-maxage={0}'.format(s_maxage) if s_maxage is not None else None, no_cache and 'no-cache',
                 no_store and 'no-store', must_revalidate and 'must-revalidate')
        return self.add_response_headers({'cache-control': ', '.join(filter(bool, parts))}, **overrides)

    def allow_origins(self, *origins, methods=None, **overrides):
        '''Convience method for quickly allowing other resources to access this one'''
        headers = {'Access-Control-Allow-Origin': ', '.join(origins) if origins else '*'}
        if methods:
            headers['Access-Control-Allow-Methods'] = ', '.join(methods)
        return self.add_response_headers(headers, **overrides)
