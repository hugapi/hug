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
import os
import re
import hug.api
from functools import wraps
import falcon
from falcon import HTTP_BAD_REQUEST
from hug import introspect
from hug.exceptions import InvalidTypeData
from hug import _empty as empty

AUTO_INCLUDE = {'request', 'response'}
RE_CHARSET = re.compile("charset=(?P<charset>[^;]+)")

class Interface(object):
    __slots__ = ('api', 'spec', 'function', 'takes_kargs', 'takes_kwargs', 'defaults', 'parameters', 'required',
                 'outputs', 'params_for_outputs', 'invalid_outputs', 'params_for_invalid_outputs', 'directives',
                 'params_for_transform', 'on_invalid', 'params_for_on_invalid', 'parse_body', 'requires',
                 'set_status', 'validate_function', 'response_headers', 'raise_on_invalid', 'catch_exceptions',
                 'transform', 'input_transformations', 'examples', 'output_doc', 'wrapped')

    def __init__(self, route, function, catch_exceptions=True):
        self.api = route.get('api', hug.api.from_object(function))
        self.spec =  getattr(function, 'original', function)
        self.function = function
        self.catch_exceptions = catch_exceptions

        self.takes_kargs = introspect.takes_kargs(self.spec)
        self.takes_kwargs = introspect.takes_kwargs(self.spec)

        if not 'parameters' in route:
            self.parameters = introspect.arguments(self.spec)
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

        self.outputs = route.get('output', self.api.output_format)
        self.params_for_outputs = introspect.takes_arguments(self.outputs, *AUTO_INCLUDE)
        if 'output_invalid' in route:
            self.invalid_outputs = route['output_invalid']
            self.params_for_invalid_outputs = introspect.takes_arguments(self.invalid_outputs, *AUTO_INCLUDE)

        self.transform = route.get('transform', None)
        if self.transform is None and not isinstance(self.spec.__annotations__.get('return', None), (str, type(None))):
            self.transform = self.spec.__annotations__['return']

        if hasattr(self.transform, 'dump'):
            self.transform = self.transform.dump
            self.output_doc = self.transform.__doc__
        elif self.transform or 'return' in self.spec.__annotations__:
            self.output_doc = self.transform or self.spec.__annotations__['return']

        self.params_for_transform = introspect.takes_arguments(self.transform, *AUTO_INCLUDE)

        if 'on_invalid' in route:
            self.on_invalid = route['on_invalid']
            self.params_for_on_invalid = introspect.takes_arguments(self.on_invalid, *AUTO_INCLUDE)
        elif self.transform:
            self.on_invalid = self.transform
            self.params_for_on_invalid = self.params_for_transform

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

        self.parse_body = 'parse_body' in route
        self.requires = route.get('requires', ())
        self.set_status = route.get('status', False)
        self.validate_function = route.get('validate', False)
        self.response_headers = tuple(route.get('response_headers', {}).items())
        self.raise_on_invalid = route.get('raise_on_invalid', False)

        if route['versions']:
            self.api.versions.update(route['versions'])

        self.wrapped = self.function
        if self.directives and not getattr(function, 'without_directives', None):
            @wraps(function)
            def callable_method(*args, **kwargs):
                for parameter, directive in self.directives.items():
                    if parameter in kwargs:
                        continue
                    arguments = (self.defaults[parameter], ) if parameter in self.defaults else ()
                    kwargs[parameter] = directive(*arguments, module=self.api.module,
                                        api_version=max(route['versions'], key=lambda version: version or -1)
                                        if route['versions'] else None)
                return function(*args, **kwargs)
            self.wrapped = callable_method
            self.wrapped.without_directives = self.function

        self.wrapped.__dict__['interface'] = self

    def gather_parameters(self, request, response, api_version=None, **input_parameters):
        input_parameters.update(request.params)
        if self.parse_body and request.content_length is not None:
            body = request.stream
            content_type = request.content_type
            encoding = None
            if content_type and ";" in content_type:
                content_type, rest = content_type.split(";", 1)
                charset = RE_CHARSET.search(rest).groupdict()
                encoding = charset.get('charset', encoding).strip()

            body_formatting_handler = body and self.api.input_format(content_type)
            if body_formatting_handler:
                if encoding is not None:
                    body = body_formatting_handler(body, encoding)
                else:
                    body = body_formatting_handler(body)
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

    def validate(self, input_parameters):
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
        if not errors and self.validate_function:
            errors = self.validate_function(input_parameters)
        return errors

    def transform_data(self, data, request=None, response=None):
        if self.transform and not (isinstance(self.transform, type) and isinstance(data, self.transform)):
            if self.params_for_transform:
                extra_kwargs = {}
                if 'response' in self.params_for_transform:
                    extra_kwargs['response'] = response
                if 'request' in self.params_for_transform:
                    extra_kwargs['request'] = request
                return self.transform(data, **extra_kwargs)
            else:
                return self.transform(data)
        return data

    def __call__(self, request, response, api_version=None, **kwargs):
        api_version = int(api_version) if api_version is not None else api_version
        if not self.catch_exceptions:
            exception_types = ()
        else:
            exception_types = self.api.exception_handlers(api_version)
            exception_types = tuple(exception_types.keys()) if exception_types else ()
        try:
            for header_name, header_value in self.response_headers:
                response.set_header(header_name, header_value)

            if self.set_status:
                response.status = self.set_status

            if self.params_for_outputs:
                params_for_outputs = {}
                if 'response' in self.params_for_outputs:
                    params_for_outputs['response'] = response
                if 'request' in self.params_for_outputs:
                    params_for_outputs['request'] = request
            else:
                params_for_outputs = empty.dict

            if callable(self.outputs.content_type):
                response.content_type = self.outputs.content_type(request=request, response=response)
            else:
                response.content_type = self.outputs.content_type
            for requirement in self.requires:
                conclusion = requirement(response=response, request=request, module=self.api.module,
                                         api_version=api_version)
                if conclusion is not True:
                    if conclusion:
                        response.data = self.outputs(conclusion, **params_for_outputs)
                    return

            input_parameters = self.gather_parameters(request, response, api_version, **kwargs)

            errors = self.validate(input_parameters)
            if errors:
                data = {'errors': errors}
                if getattr(self, 'on_invalid', False):
                    if self.params_for_on_invalid:
                        extra_kwargs = {}
                        if 'response' in self.params_for_on_invalid:
                            extra_kwargs['response'] = response
                        if 'request' in self.params_for_on_invalid:
                            extra_kwargs['request'] = request
                        data = self.on_invalid(data, **extra_kwargs)
                    else:
                        data = self.on_invalid(data)

                response.status = HTTP_BAD_REQUEST
                if getattr(self, 'invalid_outputs', False):
                    if callable(self.invalid_outputs.content_type):
                        response.content_type = self.invalid_outputs.content_type(request=request,
                                                                                        response=response)
                    else:
                        response.content_type = self.invalid_outputs.content_type
                    if self.params_for_invalid_outputs:
                        function_invalid_output_kwargs = {}
                        if 'response' in self.params_for_invalid_outputs:
                            function_invalid_output_kwargs['response'] = response
                        if 'request' in self.params_for_invalid_outputs:
                            function_invalid_output_kwargs['request'] = request
                    else:
                        function_invalid_output_kwargs = empty.dict

                    response.data = self.invalid_outputs(data, **function_invalid_output_kwargs)
                else:
                    response.data = self.outputs(data, **params_for_outputs)
                return

            if not self.takes_kwargs:
                input_parameters = {key: value for key, value in input_parameters.items() if
                                    key in self.parameters}

            data = self.function(**input_parameters)
            if hasattr(data, 'interface'):
                if data.interface is True:
                    data(request, response, api_version=None, **kwargs)
                else:
                    data.interface(request, response, api_version=None, **kwargs)
                return

            data = self.transform_data(data, request, response)

            data = self.outputs(data, **params_for_outputs)
            if hasattr(data, 'read'):
                size = None
                if hasattr(data, 'name') and os.path.isfile(data.name):
                    size = os.path.getsize(data.name)
                if request.range and size:
                    start, end = request.range
                    if end < 0:
                        end = size + end
                    end = min(end, size)
                    length = end - start + 1
                    data.seek(start)
                    response.data = data.read(length)
                    response.status = falcon.HTTP_206
                    response.content_range = (start, end, size)
                    data.close()
                else:
                    response.stream = data
                    if size:
                        response.stream_len = size
            else:
                response.data = data
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



