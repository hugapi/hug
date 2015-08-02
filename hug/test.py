from falcon.testing import StartResponseMock, create_environ
from falcon import HTTP_METHODS
from urllib.parse import urlencode
import json
from hug.run import server
from functools import partial


def call(method, api_module, url, body='', headers=None, **params):
    api = server(api_module)
    response = StartResponseMock()
    result = api(create_environ(path=url, method=method, headers=headers, query_string=urlencode(params)), response)
    return json.loads(result[0].decode('utf8'))


for method in HTTP_METHODS:
    globals()[method.lower()] = partial(call, method)
