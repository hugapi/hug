"""hug/run.py

Contains logic to enable execution of hug APIS from the command line
"""
import importlib
import json
import sys
from collections import OrderedDict, namedtuple
from wsgiref.simple_server import make_server

import falcon

from hug import documentation


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


def server(module, sink=documentation_404):
    api = falcon.API()
    for url, method_handlers in module.HUG_API_CALLS.items():
        api.add_route(url, namedtuple('Router', method_handlers.keys())(**method_handlers))
    if sink:
        api.add_sink(sink(module))
    return api


def terminal():
    if len(sys.argv) < 2:
        print("Please specify a hug API file to start the server with")
        sys.exit(1)

    api = server(importlib.machinery.SourceFileLoader(sys.argv[1].split(".")[0], sys.argv[1]).load_module())
    httpd = make_server('', 8000, api)
    print("Serving on port 8000...")
    httpd.serve_forever()


if __name__ == '__main__':
    terminal()
