"""hug/interface.py

Defines the various interface hug provides to expose routes to functions

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

import argparse
import asyncio
import os
import sys
from collections import OrderedDict
from functools import lru_cache, partial, wraps

import falcon
from falcon import HTTP_BAD_REQUEST

import hug._empty as empty
import hug.api
import hug.output_format
import hug.types as types
from hug import introspect
from hug.exceptions import InvalidTypeData
from hug.format import parse_content_type
from hug.types import (
    MarshmallowInputSchema,
    MarshmallowReturnSchema,
    Multiple,
    OneOf,
    SmartBoolean,
    Text,
    text,
)


def asyncio_call(function, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return function(*args, **kwargs)

    function = asyncio.ensure_future(function(*args, **kwargs), loop=loop)
    loop.run_until_complete(function)
    return function.result()


class Interfaces(object):
    """Defines the per-function singleton applied to hugged functions defining common data needed by all interfaces"""

    def __init__(self, function, args=None):
        self.api = hug.api.from_object(function)
        self.spec = getattr(function, "original", function)
        self.arguments = introspect.arguments(function)
        self.name = introspect.name(function)
        self._function = function

        self.is_coroutine = introspect.is_coroutine(self.spec)
        if self.is_coroutine:
            self.spec = getattr(self.spec, "__wrapped__", self.spec)

        self.takes_args = introspect.takes_args(self.spec)
        self.takes_kwargs = introspect.takes_kwargs(self.spec)

        self.parameters = list(introspect.arguments(self.spec, self.takes_kwargs + self.takes_args))
        if self.takes_kwargs:
            self.kwarg = self.parameters.pop(-1)
        if self.takes_args:
            self.arg = self.parameters.pop(-1)
        self.parameters = tuple(self.parameters)
        self.defaults = dict(zip(reversed(self.parameters), reversed(self.spec.__defaults__ or ())))
        self.required = self.parameters[: -(len(self.spec.__defaults__ or ())) or None]
        self.is_method = introspect.is_method(self.spec) or introspect.is_method(function)
        if self.is_method:
            self.required = self.required[1:]
            self.parameters = self.parameters[1:]

        self.all_parameters = set(self.parameters)
        if self.spec is not function:
            self.all_parameters.update(self.arguments)

        if args is not None:
            transformers = args
        else:
            transformers = self.spec.__annotations__

        self.transform = transformers.get("return", None)
        self.directives = {}
        self.input_transformations = {}
        for name, transformer in transformers.items():
            if isinstance(transformer, str):
                continue
            elif hasattr(transformer, "directive"):
                self.directives[name] = transformer
                continue

            if hasattr(transformer, "from_string"):
                transformer = transformer.from_string
            elif hasattr(transformer, "load"):
                transformer = MarshmallowInputSchema(transformer)
            elif hasattr(transformer, "deserialize"):
                transformer = transformer.deserialize

            self.input_transformations[name] = transformer

    def __call__(__hug_internal_self, *args, **kwargs):  # noqa: N805
        """"Calls the wrapped function, uses __hug_internal_self incase self is passed in as a kwarg from the wrapper"""
        if not __hug_internal_self.is_coroutine:
            return __hug_internal_self._function(*args, **kwargs)

        return asyncio_call(__hug_internal_self._function, *args, **kwargs)


class Interface(object):
    """Defines the basic hug interface object, which is responsible for wrapping a user defined function and providing
       all the info requested in the function as well as the route

       A Interface object should be created for every kind of protocal hug supports
    """

    __slots__ = (
        "interface",
        "_api",
        "defaults",
        "parameters",
        "required",
        "_outputs",
        "on_invalid",
        "requires",
        "validate_function",
        "transform",
        "examples",
        "output_doc",
        "wrapped",
        "directives",
        "all_parameters",
        "raise_on_invalid",
        "invalid_outputs",
        "map_params",
        "input_transformations",
    )

    def __init__(self, route, function):
        if route.get("api", None):
            self._api = route["api"]
        if "examples" in route:
            self.examples = route["examples"]
        function_args = route.get("args")
        if not hasattr(function, "interface"):
            function.__dict__["interface"] = Interfaces(function, function_args)

        self.interface = function.interface
        self.requires = route.get("requires", ())
        if "validate" in route:
            self.validate_function = route["validate"]
        if "output_invalid" in route:
            self.invalid_outputs = route["output_invalid"]

        if not "parameters" in route:
            self.defaults = self.interface.defaults
            self.parameters = self.interface.parameters
            self.all_parameters = self.interface.all_parameters
            self.required = self.interface.required
        else:
            self.defaults = route.get("defaults", {})
            self.parameters = tuple(route["parameters"])
            self.all_parameters = set(route["parameters"])
            self.required = tuple(
                [parameter for parameter in self.parameters if parameter not in self.defaults]
            )

        if "map_params" in route:
            self.map_params = route["map_params"]
            for interface_name, internal_name in self.map_params.items():
                if internal_name in self.defaults:
                    self.defaults[interface_name] = self.defaults.pop(internal_name)
                if internal_name in self.parameters:
                    self.parameters = [
                        interface_name if param == internal_name else param
                        for param in self.parameters
                    ]
                if internal_name in self.all_parameters:
                    self.all_parameters.remove(internal_name)
                    self.all_parameters.add(interface_name)
                if internal_name in self.required:
                    self.required = tuple(
                        [
                            interface_name if param == internal_name else param
                            for param in self.required
                        ]
                    )

            reverse_mapping = {
                internal: interface for interface, internal in self.map_params.items()
            }
            self.input_transformations = {
                reverse_mapping.get(name, name): transform
                for name, transform in self.interface.input_transformations.items()
            }
        else:
            self.map_params = {}
            self.input_transformations = self.interface.input_transformations

        if "output" in route:
            self.outputs = route["output"]

        self.transform = route.get("transform", None)
        if self.transform is None and not isinstance(self.interface.transform, (str, type(None))):
            self.transform = self.interface.transform

        if hasattr(self.transform, "dump"):
            self.transform = MarshmallowReturnSchema(self.transform)
            self.output_doc = self.transform.__doc__
        elif self.transform or self.interface.transform:
            output_doc = self.transform or self.interface.transform
            self.output_doc = output_doc if type(output_doc) is str else output_doc.__doc__

        self.raise_on_invalid = route.get("raise_on_invalid", False)
        if "on_invalid" in route:
            self.on_invalid = route["on_invalid"]
        elif self.transform:
            self.on_invalid = self.transform

        defined_directives = self.api.directives()
        used_directives = set(self.parameters).intersection(defined_directives)
        self.directives = {
            directive_name: defined_directives[directive_name] for directive_name in used_directives
        }
        self.directives.update(self.interface.directives)

    @property
    def api(self):
        return getattr(self, "_api", self.interface.api)

    @property
    def outputs(self):
        return getattr(self, "_outputs", None)

    @outputs.setter
    def outputs(self, outputs):
        self._outputs = outputs  # pragma: no cover - generally re-implemented by sub classes

    def validate(self, input_parameters, context):
        """Runs all set type transformers / validators against the provided input parameters and returns any errors"""
        errors = {}

        for key, type_handler in self.input_transformations.items():
            if self.raise_on_invalid:
                if key in input_parameters:
                    input_parameters[key] = self.initialize_handler(
                        type_handler, input_parameters[key], context=context
                    )
            else:
                try:
                    if key in input_parameters:
                        input_parameters[key] = self.initialize_handler(
                            type_handler, input_parameters[key], context=context
                        )
                except InvalidTypeData as error:
                    errors[key] = error.reasons or str(error)
                except Exception as error:
                    if hasattr(error, "args") and error.args:
                        errors[key] = error.args[0]
                    else:
                        errors[key] = str(error)
        for require in self.required:
            if not require in input_parameters:
                errors[require] = "Required parameter '{}' not supplied".format(require)
        if not errors and getattr(self, "validate_function", False):
            errors = self.validate_function(input_parameters)
        return errors

    def check_requirements(self, request=None, response=None, context=None):
        """Checks to see if all requirements set pass

           if all requirements pass nothing will be returned
           otherwise, the error reported will be returned
        """
        for requirement in self.requires:
            conclusion = requirement(
                response=response, request=request, context=context, module=self.api.module
            )
            if conclusion and conclusion is not True:
                return conclusion

    def documentation(self, add_to=None):
        """Produces general documentation for the interface"""
        doc = OrderedDict if add_to is None else add_to

        usage = self.interface.spec.__doc__
        if usage:
            doc["usage"] = usage
        if getattr(self, "requires", None):
            doc["requires"] = [
                getattr(requirement, "__doc__", requirement.__name__)
                for requirement in self.requires
            ]
        doc["outputs"] = OrderedDict()
        doc["outputs"]["format"] = self.outputs.__doc__
        doc["outputs"]["content_type"] = self.outputs.content_type
        parameters = [
            param
            for param in self.parameters
            if not param in ("request", "response", "self")
            and not param in ("api_version", "body")
            and not param.startswith("hug_")
            and not hasattr(param, "directive")
        ]
        if parameters:
            inputs = doc.setdefault("inputs", OrderedDict())
            types = self.interface.spec.__annotations__
            for argument in parameters:
                kind = types.get(self._remap_entry(argument), text)
                if getattr(kind, "directive", None) is True:
                    continue

                input_definition = inputs.setdefault(argument, OrderedDict())
                input_definition["type"] = kind if isinstance(kind, str) else kind.__doc__
                default = self.defaults.get(argument, None)
                if default is not None:
                    input_definition["default"] = default

        return doc

    def _rewrite_params(self, params):
        for interface_name, internal_name in self.map_params.items():
            if interface_name in params:
                params[internal_name] = params.pop(interface_name)

    def _remap_entry(self, interface_name):
        return self.map_params.get(interface_name, interface_name)

    @staticmethod
    def cleanup_parameters(parameters, exception=None):
        for _parameter, directive in parameters.items():
            if hasattr(directive, "cleanup"):
                directive.cleanup(exception=exception)

    @staticmethod
    def initialize_handler(handler, value, context):
        try:  # It's easier to ask for forgiveness than for permission
            return handler(value, context=context)
        except TypeError:
            return handler(value)


class Local(Interface):
    """Defines the Interface responsible for exposing functions locally"""

    __slots__ = ("skip_directives", "skip_validation", "version")

    def __init__(self, route, function):
        super().__init__(route, function)
        self.version = route.get("version", None)
        if "skip_directives" in route:
            self.skip_directives = True
        if "skip_validation" in route:
            self.skip_validation = True

        self.interface.local = self

    def __get__(self, instance, kind):
        """Support instance methods"""
        return partial(self.__call__, instance) if instance else self.__call__

    @property
    def __name__(self):
        return self.interface.spec.__name__

    @property
    def __module__(self):
        return self.interface.spec.__module__

    def __call__(self, *args, **kwargs):
        context = self.api.context_factory(api=self.api, api_version=self.version, interface=self)
        """Defines how calling the function locally should be handled"""

        for _requirement in self.requires:
            lacks_requirement = self.check_requirements(context=context)
            if lacks_requirement:
                self.api.delete_context(context, lacks_requirement=lacks_requirement)
                return self.outputs(lacks_requirement) if self.outputs else lacks_requirement

        for index, argument in enumerate(args):
            kwargs[self.parameters[index]] = argument

        if not getattr(self, "skip_directives", False):
            for parameter, directive in self.directives.items():
                if parameter in kwargs:
                    continue
                arguments = (self.defaults[parameter],) if parameter in self.defaults else ()
                kwargs[parameter] = directive(
                    *arguments,
                    api=self.api,
                    api_version=self.version,
                    interface=self,
                    context=context
                )

        if not getattr(self, "skip_validation", False):
            errors = self.validate(kwargs, context)
            if errors:
                errors = {"errors": errors}
                if getattr(self, "on_invalid", False):
                    errors = self.on_invalid(errors)
                outputs = getattr(self, "invalid_outputs", self.outputs)
                self.api.delete_context(context, errors=errors)
                return outputs(errors) if outputs else errors

        self._rewrite_params(kwargs)
        try:
            result = self.interface(**kwargs)
            if self.transform:
                if hasattr(self.transform, "context"):
                    self.transform.context = context
                result = self.transform(result)
        except Exception as exception:
            self.cleanup_parameters(kwargs, exception=exception)
            self.api.delete_context(context, exception=exception)
            raise exception
        self.cleanup_parameters(kwargs)
        self.api.delete_context(context)
        return self.outputs(result) if self.outputs else result


class CLI(Interface):
    """Defines the Interface responsible for exposing functions to the CLI"""

    def __init__(self, route, function):
        super().__init__(route, function)
        if not self.outputs:
            self.outputs = self.api.cli.output_format

        self.interface.cli = self
        self.reaffirm_types = {}
        use_parameters = list(self.interface.parameters)
        self.additional_options = getattr(
            self.interface, "arg", getattr(self.interface, "kwarg", False)
        )
        if self.additional_options:
            use_parameters.append(self.additional_options)

        used_options = {"h", "help"}
        nargs_set = self.interface.takes_args or self.interface.takes_kwargs

        class CustomArgumentParser(argparse.ArgumentParser):
            exit_callback = None

            def exit(self, status=0, message=None):
                if self.exit_callback:
                    self.exit_callback(message)
                super().exit(status, message)

        self.parser = CustomArgumentParser(
            description=route.get("doc", self.interface.spec.__doc__)
        )
        if "version" in route:
            self.parser.add_argument(
                "-v",
                "--version",
                action="version",
                version="{0} {1}".format(
                    route.get("name", self.interface.spec.__name__), route["version"]
                ),
            )
            used_options.update(("v", "version"))

        self.context_tranforms = []
        for option in use_parameters:

            if option in self.directives:
                continue

            if option in self.interface.required or option == self.additional_options:
                args = (option,)
            else:
                short_option = option[0]
                while short_option in used_options and len(short_option) < len(option):
                    short_option = option[: len(short_option) + 1]

                used_options.add(short_option)
                used_options.add(option)
                if short_option != option:
                    args = ("-{0}".format(short_option), "--{0}".format(option))
                else:
                    args = ("--{0}".format(option),)

            kwargs = {}
            if option in self.defaults:
                kwargs["default"] = self.defaults[option]
            if option in self.interface.input_transformations:
                transform = self.interface.input_transformations[option]
                kwargs["type"] = transform
                kwargs["help"] = transform.__doc__
                if transform in (list, tuple) or isinstance(transform, types.Multiple):
                    kwargs["action"] = "append"
                    kwargs["type"] = Text()
                    self.reaffirm_types[option] = transform
                elif transform == bool or isinstance(transform, type(types.boolean)):
                    kwargs["action"] = "store_true"
                    self.reaffirm_types[option] = transform
                elif isinstance(transform, types.OneOf):
                    kwargs["choices"] = transform.values
            elif (
                option in self.interface.spec.__annotations__
                and type(self.interface.spec.__annotations__[option]) == str
            ):
                kwargs["help"] = option
            if (
                kwargs.get("type", None) == bool or kwargs.get("action", None) == "store_true"
            ) and not kwargs["default"]:
                kwargs["action"] = "store_true"
                kwargs.pop("type", None)
            elif kwargs.get("action", None) == "store_true":
                kwargs.pop("action", None) == "store_true"

            if option == self.additional_options:
                kwargs["nargs"] = "*"
            elif (
                not nargs_set
                and kwargs.get("action", None) == "append"
                and not option in self.interface.defaults
            ):
                kwargs["nargs"] = "*"
                kwargs.pop("action", "")
                nargs_set = True

            self.parser.add_argument(*args, **kwargs)

        self.api.cli.commands[route.get("name", self.interface.spec.__name__)] = self

    def output(self, data, context):
        """Outputs the provided data using the transformations and output format specified for this CLI endpoint"""
        if self.transform:
            if hasattr(self.transform, "context"):
                self.transform.context = context
            data = self.transform(data)
        if hasattr(data, "read"):
            data = data.read().decode("utf8")
        if data is not None:
            data = self.outputs(data)
            if data:
                sys.stdout.buffer.write(data)
                if not data.endswith(b"\n"):
                    sys.stdout.buffer.write(b"\n")
        return data

    def __call__(self):
        """Calls the wrapped function through the lens of a CLI ran command"""
        context = self.api.context_factory(api=self.api, argparse=self.parser, interface=self)

        def exit_callback(message):
            self.api.delete_context(context, errors=message)

        self.parser.exit_callback = exit_callback

        self.api._ensure_started()
        for requirement in self.requires:
            conclusion = requirement(request=sys.argv, module=self.api.module, context=context)
            if conclusion and conclusion is not True:
                self.api.delete_context(context, lacks_requirement=conclusion)
                return self.output(conclusion, context)

        if self.interface.is_method:
            self.parser.prog = "%s %s" % (self.api.module.__name__, self.interface.name)

        known, unknown = self.parser.parse_known_args()
        pass_to_function = vars(known)
        for option, directive in self.directives.items():
            arguments = (self.defaults[option],) if option in self.defaults else ()
            pass_to_function[option] = directive(
                *arguments, api=self.api, argparse=self.parser, context=context, interface=self
            )

        for field, type_handler in self.reaffirm_types.items():
            if field in pass_to_function:
                pass_to_function[field] = self.initialize_handler(
                    type_handler, pass_to_function[field], context=context
                )

        if getattr(self, "validate_function", False):
            errors = self.validate_function(pass_to_function)
            if errors:
                self.api.delete_context(context, errors=errors)
                return self.output(errors, context)

        args = None
        if self.additional_options:
            args = []
            for parameter in self.interface.parameters:
                if parameter in pass_to_function:
                    args.append(pass_to_function.pop(parameter))
            args.extend(pass_to_function.pop(self.additional_options, ()))
            if self.interface.takes_kwargs:
                add_options_to = None
                for option in unknown:
                    if option.startswith("--"):
                        if add_options_to:
                            value = pass_to_function[add_options_to]
                            if len(value) == 1:
                                pass_to_function[add_options_to] = value[0]
                            elif value == []:
                                pass_to_function[add_options_to] = True
                        add_options_to = option[2:]
                        pass_to_function.setdefault(add_options_to, [])
                    elif add_options_to:
                        pass_to_function[add_options_to].append(option)

        self._rewrite_params(pass_to_function)

        try:
            if args:
                result = self.output(self.interface(*args, **pass_to_function), context)
            else:
                result = self.output(self.interface(**pass_to_function), context)
        except Exception as exception:
            self.cleanup_parameters(pass_to_function, exception=exception)
            self.api.delete_context(context, exception=exception)
            raise exception
        self.cleanup_parameters(pass_to_function)
        self.api.delete_context(context)
        return result


class HTTP(Interface):
    """Defines the interface responsible for wrapping functions and exposing them via HTTP based on the route"""

    __slots__ = (
        "_params_for_outputs_state",
        "_params_for_invalid_outputs_state",
        "_params_for_transform_state",
        "_params_for_on_invalid",
        "set_status",
        "response_headers",
        "transform",
        "input_transformations",
        "examples",
        "wrapped",
        "catch_exceptions",
        "parse_body",
        "private",
        "on_invalid",
        "inputs",
    )
    AUTO_INCLUDE = {"request", "response"}

    def __init__(self, route, function, catch_exceptions=True):
        super().__init__(route, function)
        self.catch_exceptions = catch_exceptions
        self.parse_body = "parse_body" in route
        self.set_status = route.get("status", False)
        self.response_headers = tuple(route.get("response_headers", {}).items())
        self.private = "private" in route
        self.inputs = route.get("inputs", {})

        if "on_invalid" in route:
            self._params_for_on_invalid = introspect.takes_arguments(
                self.on_invalid, *self.AUTO_INCLUDE
            )
        elif self.transform:
            self._params_for_on_invalid = self._params_for_transform

        self.api.http.versions.update(route.get("versions", (None,)))

        self.interface.http = self

    @property
    def _params_for_outputs(self):
        if not hasattr(self, "_params_for_outputs_state"):
            self._params_for_outputs_state = introspect.takes_arguments(
                self.outputs, *self.AUTO_INCLUDE
            )
        return self._params_for_outputs_state

    @property
    def _params_for_invalid_outputs(self):
        if not hasattr(self, "_params_for_invalid_outputs_state"):
            self._params_for_invalid_outputs_state = introspect.takes_arguments(
                self.invalid_outputs, *self.AUTO_INCLUDE
            )
        return self._params_for_invalid_outputs_state

    @property
    def _params_for_transform(self):
        if not hasattr(self, "_params_for_transform_state"):
            self._params_for_transform_state = introspect.takes_arguments(
                self.transform, *self.AUTO_INCLUDE
            )
        return self._params_for_transform_state

    def gather_parameters(self, request, response, context, api_version=None, **input_parameters):
        """Gathers and returns all parameters that will be used for this endpoint"""
        input_parameters.update(request.params)

        if self.parse_body and request.content_length:
            body = request.bounded_stream
            content_type, content_params = parse_content_type(request.content_type)
            body_formatter = body and self.inputs.get(
                content_type, self.api.http.input_format(content_type)
            )
            if body_formatter:
                body = body_formatter(body, content_length=request.content_length, **content_params)
            if "body" in self.all_parameters:
                input_parameters["body"] = body
            if isinstance(body, dict):
                input_parameters.update(body)
        elif "body" in self.all_parameters:
            input_parameters["body"] = None

        if "request" in self.all_parameters:
            input_parameters["request"] = request
        if "response" in self.all_parameters:
            input_parameters["response"] = response
        if "api_version" in self.all_parameters:
            input_parameters["api_version"] = api_version
        for parameter, directive in self.directives.items():
            arguments = (self.defaults[parameter],) if parameter in self.defaults else ()
            input_parameters[parameter] = directive(
                *arguments,
                response=response,
                request=request,
                api=self.api,
                api_version=api_version,
                context=context,
                interface=self
            )
        return input_parameters

    @property
    def outputs(self):
        return getattr(self, "_outputs", self.api.http.output_format)

    @outputs.setter
    def outputs(self, outputs):
        self._outputs = outputs

    def transform_data(self, data, request=None, response=None, context=None):
        transform = self.transform
        if hasattr(transform, "context"):
            self.transform.context = context
        """Runs the transforms specified on this endpoint with the provided data, returning the data modified"""
        if transform and not (isinstance(transform, type) and isinstance(data, transform)):
            if self._params_for_transform:
                return transform(
                    data, **self._arguments(self._params_for_transform, request, response)
                )
            else:
                return transform(data)
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
            if "response" in requested_params:
                arguments["response"] = response
            if "request" in requested_params:
                arguments["request"] = request
            return arguments

        return empty.dict

    def set_response_defaults(self, response, request=None):
        """Sets up the response defaults that are defined in the URL route"""
        for header_name, header_value in self.response_headers:
            response.set_header(header_name, header_value)
        if self.set_status:
            response.status = self.set_status
        response.content_type = self.content_type(request, response)

    def render_errors(self, errors, request, response):
        data = {"errors": errors}
        if getattr(self, "on_invalid", False):
            data = self.on_invalid(
                data, **self._arguments(self._params_for_on_invalid, request, response)
            )

        response.status = HTTP_BAD_REQUEST
        if getattr(self, "invalid_outputs", False):
            response.content_type = self.invalid_content_type(request, response)
            response.data = self.invalid_outputs(
                data, **self._arguments(self._params_for_invalid_outputs, request, response)
            )
        else:
            response.data = self.outputs(
                data, **self._arguments(self._params_for_outputs, request, response)
            )

    def call_function(self, parameters):
        if not self.interface.takes_kwargs:
            parameters = {
                key: value for key, value in parameters.items() if key in self.all_parameters
            }
        self._rewrite_params(parameters)

        return self.interface(**parameters)

    def render_content(self, content, context, request, response, **kwargs):
        if hasattr(content, "interface") and (
            content.interface is True or hasattr(content.interface, "http")
        ):
            if content.interface is True:
                content(request, response, api_version=None, **kwargs)
            else:
                content.interface.http(request, response, api_version=None, **kwargs)
            return

        content = self.transform_data(content, request, response, context)
        content = self.outputs(
            content, **self._arguments(self._params_for_outputs, request, response)
        )
        if hasattr(content, "read"):
            size = None
            if hasattr(content, "name") and os.path.isfile(content.name):
                size = os.path.getsize(content.name)
            if request.range and size:
                start, end = request.range
                if end < 0:
                    end = size + end
                end = min(end, size)
                length = end - start + 1
                content.seek(start)
                response.data = content.read(length)
                response.status = falcon.HTTP_206
                response.content_range = (start, end, size)
                content.close()
            else:
                if size:
                    response.set_stream(content, size)
                else:
                    response.stream = content  # pragma: no cover
        else:
            response.data = content

    def __call__(self, request, response, api_version=None, **kwargs):
        context = self.api.context_factory(
            response=response,
            request=request,
            api=self.api,
            api_version=api_version,
            interface=self,
        )
        """Call the wrapped function over HTTP pulling information as needed"""
        if isinstance(api_version, str) and api_version.isdigit():
            api_version = int(api_version)
        else:
            api_version = None
        if not self.catch_exceptions:
            exception_types = ()
        else:
            exception_types = self.api.http.exception_handlers(api_version)
            exception_types = tuple(exception_types.keys()) if exception_types else ()
        input_parameters = {}
        try:
            self.set_response_defaults(response, request)
            lacks_requirement = self.check_requirements(request, response, context)
            if lacks_requirement:
                response.data = self.outputs(
                    lacks_requirement,
                    **self._arguments(self._params_for_outputs, request, response)
                )
                self.api.delete_context(context, lacks_requirement=lacks_requirement)
                return

            input_parameters = self.gather_parameters(
                request, response, context, api_version, **kwargs
            )
            errors = self.validate(input_parameters, context)
            if errors:
                self.api.delete_context(context, errors=errors)
                return self.render_errors(errors, request, response)

            self.render_content(
                self.call_function(input_parameters), context, request, response, **kwargs
            )
        except falcon.HTTPNotFound as exception:
            self.cleanup_parameters(input_parameters, exception=exception)
            self.api.delete_context(context, exception=exception)
            return self.api.http.not_found(request, response, **kwargs)
        except exception_types as exception:
            self.cleanup_parameters(input_parameters, exception=exception)
            self.api.delete_context(context, exception=exception)
            handler = None
            exception_type = type(exception)
            if exception_type in exception_types:
                handler = self.api.http.exception_handlers(api_version)[exception_type][0]
            else:
                for match_exception_type, exception_handlers in tuple(
                    self.api.http.exception_handlers(api_version).items()
                )[::-1]:
                    if isinstance(exception, match_exception_type):
                        for potential_handler in exception_handlers:
                            if not isinstance(exception, potential_handler.exclude):
                                handler = potential_handler

            if not handler:
                raise exception

            handler(request=request, response=response, exception=exception, **kwargs)
        except Exception as exception:
            self.cleanup_parameters(input_parameters, exception=exception)
            self.api.delete_context(context, exception=exception)
            raise exception
        self.cleanup_parameters(input_parameters)
        self.api.delete_context(context)

    def documentation(self, add_to=None, version=None, prefix="", base_url="", url=""):
        """Returns the documentation specific to an HTTP interface"""
        doc = OrderedDict() if add_to is None else add_to

        usage = self.interface.spec.__doc__
        if usage:
            doc["usage"] = usage

        for example in self.examples:
            example_text = "{0}{1}{2}{3}".format(
                prefix, base_url, "/v{0}".format(version) if version else "", url
            )
            if isinstance(example, str):
                example_text += "?{0}".format(example)
            doc_examples = doc.setdefault("examples", [])
            if not example_text in doc_examples:
                doc_examples.append(example_text)

        doc = super().documentation(doc)

        if getattr(self, "output_doc", ""):
            doc["outputs"]["type"] = self.output_doc

        return doc

    @lru_cache()
    def urls(self, version=None):
        """Returns all URLS that are mapped to this interface"""
        urls = []
        for _base_url, routes in self.api.http.routes.items():
            for url, methods in routes.items():
                for _method, versions in methods.items():
                    for interface_version, interface in versions.items():
                        if interface_version == version and interface == self:
                            if not url in urls:
                                urls.append(("/v{0}".format(version) if version else "") + url)
        return urls

    def url(self, version=None, **kwargs):
        """Returns the first matching URL found for the specified arguments"""
        for url in self.urls(version):
            if [key for key in kwargs.keys() if not "{" + key + "}" in url]:
                continue

            return url.format(**kwargs)

        raise KeyError("URL that takes all provided parameters not found")


class ExceptionRaised(HTTP):
    """Defines the interface responsible for taking and transforming exceptions that occur during processing"""

    __slots__ = ("handle", "exclude")

    def __init__(self, route, *args, **kwargs):
        self.handle = route["exceptions"]
        self.exclude = route["exclude"]
        super().__init__(route, *args, **kwargs)
