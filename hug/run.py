"""hug/run.py

Contains logic to enable execution of hug APIS from the command line
"""
import argparse
import importlib
import json
import sys
from collections import OrderedDict, namedtuple
from wsgiref.simple_server import make_server

import falcon

from hug import documentation
from hug._version import current


def documentation_404(module):
    def handle_404(request, response, *kargs, **kwargs):
        base_url = request.url[:-1]
        if request.path and request.path != "/":
            base_url = request.url.split(request.path)[0]
        to_return = OrderedDict()
        to_return['404'] = ("The API call you tried to make was not defined. "
                            "Here's a definition of the API to help you get going :)")
        to_return['documentation'] = documentation.generate(module, base_url)
        response.data = json.dumps(to_return, indent=4, separators=(',', ': ')).encode('utf8')
        response.status = falcon.HTTP_NOT_FOUND
    return handle_404


def _router(dictionary):
    return namedtuple('Router', dictionary.keys())(**dictionary)

def server(module, sink=documentation_404):
    api = falcon.API()
    sink = sink(module)
    api.add_sink(sink)
    for url, methods in module.HUG_API_CALLS.items():
        router = {}
        for method, versions in methods.items():
            if len(versions) == 1 and None in versions.keys():
                router[method] = versions[None]
            else:
                def version_router(request, response, api_version=None, **kwargs):
                    request_version = set()
                    if api_version is not None:
                        request_version.add(api_version)

                    version_header = request.get_header("X-API-VERSION")
                    if version_header:
                        request_version.add(version_header)

                    version_param = request.get_param('api_version')
                    if version_param is not None:
                        requested_version.add(version_param)

                    if len(request_version) > 1:
                        raise ValueError('You are requesting conflicting versions')

                    request_version = (request_version or (None, ))[0]
                    if request_version:
                        request_version = int(request_version)
                    versions.get(request_version, handlers.get(None, api.add_sink()))(request, reponse,
                                                                                      api_version=api_version, **kwargs)
                router[method] = version_router

        api.add_route(url, namedtuple('Router', router.keys())(**router))
    return api


def terminal():
    parser = argparse.ArgumentParser(description='Hug API Development Server')
    parser.add_argument('-f', '--file', dest='file_name', help="A Python file that contains a Hug API")
    parser.add_argument('-m', '--module', dest='module', help="A Python module that contains a Hug API")
    parser.add_argument('-p', '--port', dest='port', help="Port on which to run the Hug server", default=8000, type=int)
    parser.add_argument('-v', '--version', action='version', version='hug {0}'.format(current))

    parsed = parser.parse_args()
    file_name, module = parsed.file_name, parsed.module
    api = None
    if file_name and module:
        print("Error: can not define both a file and module source for Hug API.")
    if file_name:
        api = server(importlib.machinery.SourceFileLoader(file_name.split(".")[0], file_name).load_module())
    elif module:
        api = server(importlib.import_module(module))
    else:
        print("Error: must define a file name or module that contains a Hug API.")
    if not api:
        sys.exit(1)

    httpd = make_server('', parsed.port, api)
    print("Serving on port {0}...".format(parsed.port))
    httpd.serve_forever()
