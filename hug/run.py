"""hug/run.py

Contains logic to enable execution of hug APIS from the command line or to expose a wsgi API from within Python

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
import importlib
import json
import os
import sys
from collections import OrderedDict, namedtuple
from functools import partial
from wsgiref.simple_server import make_server

import falcon

from hug import documentation
from hug._version import current


INTRO = """
/#######################################################################\\
          `.----``..-------..``.----.
         :/:::::--:---------:--::::://.
        .+::::----##/-/oo+:-##----:::://
        `//::-------/oosoo-------::://.       ##    ##  ##    ##    #####
          .-:------./++o/o-.------::-`   ```  ##    ##  ##    ##  ##
             `----.-./+o+:..----.     `.:///. ########  ##    ## ##
   ```        `----.-::::::------  `.-:::://. ##    ##  ##    ## ##   ####
  ://::--.``` -:``...-----...` `:--::::::-.`  ##    ##  ##   ##   ##    ##
  :/:::::::::-:-     `````      .:::::-.`     ##    ##    ####     ######
   ``.--:::::::.                .:::.`
         ``..::.                .::         EMBRACE THE APIs OF THE FUTURE
             ::-                .:-
             -::`               ::-                   VERSION {0}
             `::-              -::`
              -::-`           -::-
\########################################################################/

 Copyright (C) 2015 Timothy Edmund Crosley
 Under the MIT License

""".format(current)


def determine_version(request, api_version=None, api=None):
    '''Determines the appropriate version given the set api_version, the request header, and URL query params'''
    if api_version is False and api:
        api_version = None
        for version in api.versions:
            if version and "v{0}".format(version) in request.path:
                api_version = version
                break

    request_version = set()
    if api_version is not None:
        request_version.add(api_version)

    version_header = request.get_header("X-API-VERSION")
    if version_header:
        request_version.add(version_header)

    version_param = request.get_param('api_version')
    if version_param is not None:
        request_version.add(version_param)

    if len(request_version) > 1:
        raise ValueError('You are requesting conflicting versions')

    return next(iter(request_version or (None, )))





def documentation_404(api):
    '''Returns a smart 404 page that contains documentation for the written API'''
    def handle_404(request, response, *kargs, **kwargs):
        base_url = request.url[:-1]
        if request.path and request.path != "/":
            base_url = request.url.split(request.path)[0]

        to_return = OrderedDict()
        to_return['404'] = ("The API call you tried to make was not defined. "
                            "Here's a definition of the API to help you get going :)")
        to_return['documentation'] = api.documentation(base_url, determine_version(request, False, api))
        response.data = json.dumps(to_return, indent=4, separators=(',', ': ')).encode('utf8')
        response.status = falcon.HTTP_NOT_FOUND
        response.content_type = 'application/json'
    return handle_404


def version_router(request, response, api_version=None, versions={}, not_found=None, api=None, **kwargs):
    '''Intelligently routes a request to the correct handler based on the version being requested'''
    request_version = determine_version(request, api_version, api)
    if request_version:
        request_version = int(request_version)
    versions.get(request_version, versions.get(None, not_found))(request, response, api_version=api_version, **kwargs)


def server(hug_api, default_not_found=documentation_404):
    '''Returns a WSGI compatible API server for the given Hug API module'''
    api = falcon.API(middleware=hug_api.middleware)

    not_found_handler = None
    for startup_handler in hug_api.startup_handlers:
        startup_handler(hug_api)
    if hug_api.not_found_handlers:
        if len(hug_api.not_found_handlers) == 1 and None in hug_api.not_found_handlers:
            not_found_handler = hug_api.not_found_handlers[None]
        else:
            not_found_handler = partial(version_router, api=hug_api, api_version=False,
                                        versions=hug_api.not_found_handlers, not_found=default_not_found)
    elif default_not_found:
        not_found_handler = default_not_found(hug_api)

    if not_found_handler:
        api.add_sink(not_found_handler)
        hug_api._not_found = not_found_handler

    for url, extra_sink in hug_api.sinks.items():
        api.add_sink(extra_sink, url)

    for url, methods in hug_api.routes.items():
        router = {}
        for method, versions in methods.items():
            method_function = "on_{0}".format(method.lower())
            if len(versions) == 1 and None in versions.keys():
                router[method_function] = versions[None]
            else:
                router[method_function] = partial(version_router, versions=versions, not_found=not_found_handler,
                                                  api=hug_api)

        router = namedtuple('Router', router.keys())(**router)
        api.add_route(url, router)
        if hug_api.versions and hug_api.versions != (None, ):
            api.add_route('/v{api_version}' + url, router)

    def error_serializer(_, error):
        return (hug_api.output_format.content_type,
                hug_api.output_format({"errors": {error.title: error.description}}))

    api.set_error_serializer(error_serializer)
    return api


def terminal():
    '''Starts the terminal application'''
    parser = argparse.ArgumentParser(description='Hug API Development Server')
    parser.add_argument('-f', '--file', dest='file_name', help="A Python file that contains a Hug API")
    parser.add_argument('-m', '--module', dest='module', help="A Python module that contains a Hug API")
    parser.add_argument('-p', '--port', dest='port', help="Port on which to run the Hug server", default=8000, type=int)
    parser.add_argument('-nd', '--no-404-documentation', dest='no_documentation', action='store_true')
    parser.add_argument('-v', '--version', action='version', version='hug {0}'.format(current))

    parsed = parser.parse_args()
    file_name, module = parsed.file_name, parsed.module
    api = None
    server_arguments = {}
    if parsed.no_documentation:
        server_arguments['default_not_found'] = None
    if file_name and module:
        print("Error: can not define both a file and module source for Hug API.")
    if file_name:
        sys.path.append(os.path.dirname(os.path.abspath(file_name)))
        api = server(importlib.machinery.SourceFileLoader(file_name.split(".")[0], file_name).load_module(),
                     **server_arguments)
    elif module:
        api = server(importlib.import_module(module), **server_arguments)
    else:
        print("Error: must define a file name or module that contains a Hug API.")
    if not api:
        sys.exit(1)

    print(INTRO)
    httpd = make_server('', parsed.port, api)
    print("Serving on port {0}...".format(parsed.port))
    httpd.serve_forever()
