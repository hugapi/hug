from functools import wraps
from collections import OrderedDict
import sys
from hug.run import server
import hug.output_format

from falcon import HTTP_METHODS, HTTP_BAD_REQUEST


def call(url, accept=HTTP_METHODS, output=hug.output_format.json):
    def decorator(api_function):
        module = sys.modules[api_function.__module__]

        def interface(request, response):
            input_parameters = request.params
            errors = {}
            for key, type_handler in api_function.__annotations__.items():
                try:
                    input_parameters[key] = type_handler(input_parameters[key])
                except Exception as error:
                    errors[key] = str(error)
            if errors:
                response.data = output({"errors": errors})
                response.status = HTTP_BAD_REQUEST
                return

            input_parameters['request'], input_parameters['response'] = (request, response)
            response.data = output(api_function(**input_parameters))

        if not 'HUG' in module.__dict__:
            def api_auto_instantiate(*kargs, **kwargs):
                module.HUG = server(module)
                return module.HUG(*kargs, **kwargs)
            module.HUG = api_auto_instantiate
            module.HUG_API_CALLS = OrderedDict()

        for method in accept:
            module.HUG_API_CALLS.setdefault(url, {})["on_{0}".format(method.lower())] = interface

        api_function.interface = interface
        interface.api_function = api_function

        return api_function
    return decorator


def get(url):
    return call(url=url, accept=('GET', ))


def post(url):
    return call(url=url, accept=('POST', ))


def put(url):
    return call(url=url, acccept=('PUT', ))


def delete(url):
    return call(url=url, accept=('DELETE', ))
