from functools import wraps
from collections import OrderedDict
import sys

from falcon import HTTP_METHODS


def call(url, methods=HTTP_METHODS):
    def decorator(api_function):
        module = sys.modules[api_function.__name__]
        api_definition = sys.modules['hug.hug'].__dict__.setdefault('HUG_API_CALLS', OrderedDict())
        for method in methods:
            api_definition.setdefault(url, {})["on_{0}".format(method.lower())] = api_function

        def interface(request, reponse):
            return api_function(**request.attributes)

        api_function.interface = interface

        return api_function


def get(url):
    return call(url=url, accept=('GET', ))


def post(url):
    return call(url=url, accept=('POST', ))


def put(url):
    return call(url=url, acccept('PUT', ))


def delete(url):
    return call(url=url, accept=('DELETE', ))
