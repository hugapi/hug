from functools import wraps
from collections import OrderedDict
import sys
from hug.run import server

from falcon import HTTP_METHODS


def call(url, accept=HTTP_METHODS):
    def decorator(api_function):
        module = sys.modules[api_function.__name__]

        def interface(request, response):
            response.data = api_function(**request.params).encode('utf8')

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
