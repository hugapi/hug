"""hug/interface.py

Defines the various interfaces hug provides to expose routes to functions

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
from functools import wraps

import falcon
from falcon import HTTP_BAD_REQUEST

import hug.api
import hug.output_format
from hug import _empty as empty
from hug import introspect
from hug.exceptions import InvalidTypeData
from hug.input_format import separate_encoding


class Interface(object):
    """Defines the basic hug interface object, which is responsible for wrapping a user defined function and providing
       all the info requested in the function as well as the route

       A Interface object should be created for every kind of protocal hug supports
    """
    __slots__ = ('api', 'spec', 'function', 'takes_kargs', 'takes_kwargs', 'defaults', 'parameters', 'required',
                 'outputs', 'directives', 'on_invalid', 'requires', 'validate_function',
                 'transform', 'input_transformations', 'examples', 'output_doc', 'wrapped')

    def __init__(self, route, function):
        self.api = route.get('api', hug.api.from_object(function))
        self.spec =  getattr(function, 'original', function)
        self.function = function
        self.requires = route.get('requires', ())
        if 'validate' in route:
            self.validate_function = route['validate']

        self.takes_kargs = introspect.takes_kargs(self.spec)
        self.takes_kwargs = introspect.takes_kwargs(self.spec)

        if not 'parameters' in route:
            self.parameters = introspect.arguments(self.spec, 1 if self.takes_kargs else 0)
            self.defaults = {}
            for index, default in enumerate(reversed(self.spec.__defaults__ or ())):
                self.defaults[self.parameters[-(index + 1)]] = default
            self.required = self.parameters[:-(len(self.spec.__defaults__ or ())) or None]
        else:
            self.defaults = route.get('defaults', {})
            self.parameters = tuple(route['parameters'])
            self.required = tuple([parameter for parameter in self.parameters if parameter not in self.defaults])
        if 'method' in self.spec.__class__.__name__:
            self.required = self.required[1:]
            self.parameters = self.parameters[1:]

        self.outputs = route.get('output', self.api.output_format)
        self.transform = route.get('transform', None)
        if self.transform is None and not isinstance(self.spec.__annotations__.get('return', None), (str, type(None))):
            self.transform = self.spec.__annotations__['return']

        if hasattr(self.transform, 'dump'):
            self.transform = self.transform.dump
            self.output_doc = self.transform.__doc__
        elif self.transform or 'return' in self.spec.__annotations__:
            self.output_doc = self.transform or self.spec.__annotations__['return']

        if 'on_invalid' in route:
            self.on_invalid = route['on_invalid']
        elif self.transform:
            self.on_invalid = self.transform

        defined_directives = self.api.directives()
        used_directives = set(self.parameters).intersection(defined_directives)
        self.directives = {directive_name: defined_directives[directive_name] for directive_name in used_directives}

        self.input_transformations = {}
        for name, transformer in self.spec.__annotations__.items():
            if isinstance(transformer, str):
                continue
            elif hasattr(transformer, 'directive'):
                self.directives[name] = transformer
                continue

            if hasattr(transformer, 'load'):
                transformer = self._marshmallow_schema(transformer)
            elif hasattr(transformer, 'deserialize'):
                transformer = transformer.deserialize

            self.input_transformations[name] = transformer

        self.wrapped = self.function
        if self.directives and not getattr(function, 'without_directives', None):
            @wraps(function)
            def callable_method(*args, **kwargs):
                for parameter, directive in self.directives.items():
                    if parameter in kwargs:
                        continue
                    arguments = (self.defaults[parameter], ) if parameter in self.defaults else ()
                    kwargs[parameter] = directive(*arguments, module=self.api.module,
                                        api_version=max(route.get('versions', ()), key=lambda version: version or -1)
                                        if route.get('versions', None) else None)
                return function(*args, **kwargs)
            self.wrapped = callable_method
            self.wrapped.without_directives = self.function

    def validate(self, input_parameters):
        """Runs all set type transformers / validators against the provided input parameters and returns any errors"""
        errors = {}
        for key, type_handler in self.input_transformations.items():
            if self.raise_on_invalid:
                if key in input_parameters:
                    input_parameters[key] = type_handler(input_parameters[key])
            else:
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

        for require in self.required:
            if not require in input_parameters:
                errors[require] = "Required parameter not supplied"
        if not errors and getattr(self, 'validate_function', False):
            errors = self.validate_function(input_parameters)
        return errors

    def check_requirements(self, request=None, response=None):
        """Checks to see if all requirements set pass

           if all requirements pass nothing will be returned
           otherwise, the error reported will be returned
        """
        for requirement in self.requires:
            conclusion = requirement(response=response, request=request, module=self.api.module)
            if conclusion and conclusion is not True:
                return conclusion


class CLI(Interface):
    """Defines the Interface responsible for exposing functions to the CLI"""

    def __init__(self, route, function):
        super().__init__(route, function)
        self.outputs = route.get('output', hug.output_format.text)
        self.wrapped.__dict__['cli'] = self
        nargs_set = self.takes_kargs
        if nargs_set:
            self.karg = self.parameters[-1]

        used_options = {'h', 'help'}
        self.parser = argparse.ArgumentParser(description=route.get('doc', self.spec.__doc__))
        if 'version' in route:
            self.parser.add_argument('-v', '--version', action='version',
                                version="{0} {1}".format(route.get('name', self.spec.__name__),
                                                         route['version']))
            used_options.update(('v', 'version'))

        for option in self.parameters:
            if option in self.directives:
                continue

            if option in self.required:
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
            if option in self.defaults:
                kwargs['default'] = self.defaults[option]
            if option in self.input_transformations:
                transform = self.input_transformations[option]
                kwargs['type'] = transform
                kwargs['help'] = transform.__doc__
                kwargs.update(getattr(transform, 'cli_behaviour', {}))
            elif option in self.spec.__annotations__ and type(self.spec.__annotations__[option]) == str:
                kwargs['help'] = option
            if ((kwargs.get('type', None) == bool or kwargs.get('action', None) == 'store_true') and
                 kwargs['default'] == False):
                kwargs['action'] = 'store_true'
                kwargs.pop('type', None)
            elif kwargs.get('action', None) == 'store_true':
                kwargs.pop('action', None) == 'store_true'

            if option == getattr(self, 'karg', ()):
                kwargs['nargs'] = '*'
            elif not nargs_set and kwargs.get('action', None) == 'append' and not option in self.defaults:
                kwargs['nargs'] = '*'
                kwargs.pop('action', '')
                nargs_set = True

            self.parser.add_argument(*args, **kwargs)

    def output(self, data):
        """Outputs the provided data using the transformations and output format specified for this CLI endpoint"""
        if self.transform:
            data = self.transform(data)
        if hasattr(data, 'read'):
            data = data.read().decode('utf8')
        if data is not None:
            data = self.outputs(data)
            if data:
                sys.stdout.buffer.write(data)
        return data

    def __call__(self):
        """Calls the wrapped function through the lens of a CLI ran command"""
        for requirement in self.requires:
            conclusion = requirement(request=sys.argv, module=self.api.module)
            if conclusion and conclusion is not True:
                self.output(conclusion)

        pass_to_function = vars(self.parser.parse_args())
        for option, directive in self.directives.items():
            arguments = (self.defaults[option], ) if option in self.defaults else ()
            pass_to_function[option] = directive(*arguments, module=self.api.module)

        if getattr(self, 'validate_function', False):
            errors = self.validate_function(pass_to_function)
            if errors:
                return self.output(errors)

        if hasattr(self, 'karg'):
            karg_values = pass_to_function.pop(self.karg, ())
            result = self.function(*karg_values, **pass_to_function)
        else:
            result = self.function(**pass_to_function)

        return self.output(result)


class HTTP(Interface):
    """Defines the interface responsible for wrapping functions and exposing them via HTTP based on the route"""
    __slots__ = ('_params_for_outputs', '_params_for_invalid_outputs', '_params_for_transform', 'on_invalid',
                 '_params_for_on_invalid',  'set_status','response_headers', 'transform', 'input_transformations',
                 'examples', 'output_doc', 'wrapped', 'catch_exceptions', 'parse_body', 'invalid_outputs',
                 'raise_on_invalid')
    AUTO_INCLUDE = {'request', 'response'}

    def __init__(self, route, function, catch_exceptions=True):
        super().__init__(route, function)
        self.catch_exceptions = catch_exceptions
        self.parse_body = 'parse_body' in route
        self.set_status = route.get('status', False)
        self.response_headers = tuple(route.get('response_headers', {}).items())
        self.raise_on_invalid = route.get('raise_on_invalid', False)

        self._params_for_outputs = introspect.takes_arguments(self.outputs, *self.AUTO_INCLUDE)
        self._params_for_transform = introspect.takes_arguments(self.transform, *self.AUTO_INCLUDE)

        if 'output_invalid' in route:
            self.invalid_outputs = route['output_invalid']
            self._params_for_invalid_outputs = introspect.takes_arguments(self.invalid_outputs, *self.AUTO_INCLUDE)

        if 'on_invalid' in route:
            self._params_for_on_invalid = introspect.takes_arguments(self.on_invalid, *self.AUTO_INCLUDE)
        elif self.transform:
            self._params_for_on_invalid = self._params_for_transform

        if route['versions']:
            self.api.versions.update(route['versions'])

        self.wrapped.__dict__['interface'] = self

    def gather_parameters(self, request, response, api_version=None, **input_parameters):
        """Gathers and returns all parameters that will be used for this endpoint"""
        input_parameters.update(request.params)
        if self.parse_body and request.content_length is not None:
            body = request.stream
            content_type, encoding = separate_encoding(request.content_type)
            body_formatter = body and self.api.input_format(content_type)
            if body_formatter:
                body = body_formatter(body, encoding) if encoding is not None else body_formatter(body)
            if 'body' in self.parameters:
                input_parameters['body'] = body
            if isinstance(body, dict):
                input_parameters.update(body)
        elif 'body' in self.parameters:
            input_parameters['body'] = None

        if 'request' in self.parameters:
            input_parameters['request'] = request
        if 'response' in self.parameters:
            input_parameters['response'] = response
        if 'api_version' in self.parameters:
            input_parameters['api_version'] = api_version
        for parameter, directive in self.directives.items():
            arguments = (self.defaults[parameter], ) if parameter in self.defaults else ()
            input_parameters[parameter] = directive(*arguments, response=response, request=request,
                                                    module=self.api.module, api_version=api_version)

        return input_parameters

    def transform_data(self, data, request=None, response=None):
        """Runs the transforms specified on this endpoint with the provided data, returning the data modified"""
        if self.transform and not (isinstance(self.transform, type) and isinstance(data, self.transform)):
            if self._params_for_transform:
                return self.transform(data, **self._arguments(self._params_for_transform, request, response))
            else:
                return self.transform(data)
        return data

    def content_type(self, request=None, response=None):
        """Returns the content type that should be used by default for this endpoint"""
        if callable(self.outputs.content_type):
            return self.outputs.content_type(request=request, response=response)
        else:
            return self.outputs.content_type

    def invalid_content_type(self, request=None, response=None):
        """Returns the content type that should be used by default on validation errors"""
        if callable(self.invalid_outputs.content_type):
            return self.invalid_outputs.content_type(request=request, response=response)
        else:
            return self.invalid_outputs.content_type

    def _arguments(self, requested_params, request=None, response=None):
        if requested_params:
            arguments = {}
            if 'response' in requested_params:
                arguments['response'] = response
            if 'request' in requested_params:
                arguments['request'] = request
            return arguments

        return empty.dict

    def _marshmallow_schema(self, marshmallow):
        """Dynamically generates a hug style type handler from a Marshmallow style schema"""
        def marshmallow_type(input_data):
            result, errors = marshmallow.loads(input_data) if isinstance(input_data, str) else marshmallow.load(input_data)
            if errors:
                raise InvalidTypeData('Invalid {0} passed in'.format(marshmallow.__class__.__name__), errors)
            return result

        marshmallow_type.__doc__ = marshmallow.__doc__
        marshmallow_type.__name__ = marshmallow.__class__.__name__
        return marshmallow_type

    def set_response_defaults(self, response, request=None):
        """Sets up the response defaults that are defined in the URL route"""
        for header_name, header_value in self.response_headers:
            response.set_header(header_name, header_value)
        if self.set_status:
            response.status = self.set_status
        response.content_type = self.content_type(request, response)

    def render_errors(self, errors, request, response):
        data = {'errors': errors}
        if getattr(self, 'on_invalid', False):
            data = self.on_invalid(data, **self._arguments(self._params_for_on_invalid, request, response))

        response.status = HTTP_BAD_REQUEST
        if getattr(self, 'invalid_outputs', False):
            response.content_type = self.invalid_content_type(request, response)
            response.data = self.invalid_outputs(data, **self._arguments(self._params_for_invalid_outputs,
                                                                            request, response))
        else:
            response.data = self.outputs(data, **self._arguments(self._params_for_outputs, request, response))

    def call_function(self, **parameters):
        if not self.takes_kwargs:
            parameters = {key: value for key, value in parameters.items() if key in self.parameters}

        return self.function(**parameters)

    def render_content(self, content, request, response, **kwargs):
        if hasattr(content, 'interface'):
            if content.interface is True:
                content(request, response, api_version=None, **kwargs)
            else:
                content.interface(request, response, api_version=None, **kwargs)
            return

        content = self.transform_data(content, request, response)
        content = self.outputs(content, **self._arguments(self._params_for_outputs, request, response))
        if hasattr(content, 'read'):
            size = None
            if hasattr(content, 'name') and os.path.isfile(content.name):
                size = os.path.getsize(content.name)
            if request.range and size:
                start, end = request.range
                if end < 0:
                    end = size + end
                end = min(end, size)
                length = end - start + 1
                content.seek(start)
                response.content = content.read(length)
                response.status = falcon.HTTP_206
                response.content_range = (start, end, size)
                content.close()
            else:
                response.stream = content
                if size:
                    response.stream_len = size
        else:
            response.data = content

    def __call__(self, request, response, api_version=None, **kwargs):
        """Call the wrapped function over HTTP pulling information as needed"""
        api_version = int(api_version) if api_version is not None else api_version
        if not self.catch_exceptions:
            exception_types = ()
        else:
            exception_types = self.api.exception_handlers(api_version)
            exception_types = tuple(exception_types.keys()) if exception_types else ()
        try:
            self.set_response_defaults(response, request)

            lacks_requirement = self.check_requirements(request, response)
            if lacks_requirement:
                response.data = self.outputs(lacks_requirement,
                                             **self._arguments(self._params_for_outputs, request, response))
                return

            input_parameters = self.gather_parameters(request, response, api_version, **kwargs)
            errors = self.validate(input_parameters)
            if errors:
                return self.render_errors(errors, request, response)

            self.render_content(self.call_function(**input_parameters), request, response, **kwargs)
        except falcon.HTTPNotFound:
            return self.api.not_found(request, response, **kwargs)
        except exception_types as exception:
            handler = None
            if type(exception) in exception_types:
                handler = self.api.exception_handlers(api_version)[type(exception)]
            else:
                for exception_type, exception_handler in tuple(self.api.exception_handlers(api_version).items())[::-1]:
                    if isinstance(exception, exception_type):
                        handler = exception_handler
            handler(request=request, response=response, exception=exception, **kwargs)
