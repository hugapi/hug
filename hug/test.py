from falcon.testing import StartResponseMock, create_environ
from falcon import HTTP_METHODS
from urllib.parse import urlencode
import json
from hug.run import server
from hug import output_format
from functools import partial


def call(method, api_module, url, body='', headers=None, **params):
    api = server(api_module)
    response = StartResponseMock()
    body = output_format.json(body) if not isinstance(body, str) else body

    result = api(create_environ(path=url, method=method, headers=headers, query_string=urlencode(params), body=body),
                 response)
    if result:
        response.data = result[0].decode('utf8')
        response.content_type = response.headers_dict['content-type']
        if response.content_type == 'application/json':
            response.data = json.loads(response.data)

    return response


for method in HTTP_METHODS:
    globals()[method.lower()] = partial(call, method)
