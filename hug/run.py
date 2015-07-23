"""hug/run.py

Contains logic to enable execution of hug APIS from the command line
"""
from wsgiref.simple_server import make_server

import falcon
import sys
import importlib
from collections import namedtuple


def server(module):
    api = falcon.API()
    for url, method_handlers in module.HUG_API_CALLS.items():
        api.add_route(url, namedtuple('Router', method_handlers.keys())(**method_handlers))
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
