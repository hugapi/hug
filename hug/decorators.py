from functools import wraps, partial
from collections import OrderedDict
import sys
from hug.run import server
import hug.output_format

from falcon import HTTP_METHODS, HTTP_BAD_REQUEST


def call(urls, accept=HTTP_METHODS, output=hug.output_format.json, example=None):
    if isinstance(urls, str):
        urls = (urls, )

    def decorator(api_function):
        module = sys.modules[api_function.__module__]
        accepted_parameters = api_function.__code__.co_varnames
        takes_kwargs = len(accepted_parameters) > api_function.__code__.co_argcount
        if takes_kwargs:
            accepted_parameters = accepted_parameters[:api_function.__code__.co_argcount]

        defaults = {}
        for index, default in enumerate(reversed(api_function.__defaults__ or ())):
            defaults[accepted_parameters[-(index + 1)]] = default
        required = accepted_parameters[:-(len(api_function.__defaults__))]

        def interface(request, response):
            input_parameters = request.params
            errors = {}
            for key, type_handler in api_function.__annotations__.items():
                try:
                    if key in input_parameters:
                        input_parameters[key] = type_handler(input_parameters[key])
                except Exception as error:
                    errors[key] = str(error)

            input_parameters['request'], input_parameters['response'] = (request, response)
            for require in required:
                if not require in input_parameters:
                    errors[require] = "Required parameter not supplied"
            if errors:
                response.data = output({"errors": errors})
                response.status = HTTP_BAD_REQUEST
                return

            if not takes_kwargs:
                input_parameters = {key: value for key, value in input_parameters.items() if key in accepted_parameters}

            response.data = output(api_function(**input_parameters))

        if not 'HUG' in module.__dict__:
            def api_auto_instantiate(*kargs, **kwargs):
                module.HUG = server(module)
                return module.HUG(*kargs, **kwargs)
            module.HUG = api_auto_instantiate
            module.HUG_API_CALLS = OrderedDict()

        for url in urls:
            handlers = module.HUG_API_CALLS.setdefault(url, {})
            for method in accept:
                handlers["on_{0}".format(method.lower())] = interface

        api_function.interface = interface
        interface.api_function = api_function
        interface.output_format = output
        interface.example = example
        interface.defaults = defaults
        interface.accepted_parameters = accepted_parameters

        return api_function
    return decorator


for method in HTTP_METHODS:
    globals()[method.lower()] = partial(call, accept=(method, ))
