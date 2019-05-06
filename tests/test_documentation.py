"""tests/test_documentation.py.

Tests the documentation generation capabilities integrated into Hug

Copyright (C) 2016 Timothy Edmund Crosley

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
import json
from unittest import mock

import hug
import marshmallow
from falcon import Request
from falcon.testing import StartResponseMock, create_environ

api = hug.API(__name__)


def test_basic_documentation():
    """Ensure creating and then documenting APIs with Hug works as intuitively as expected"""
    @hug.get()
    def hello_world():
        """Returns hello world"""
        return "Hello World!"

    @hug.post()
    def echo(text):
        """Returns back whatever data it is given in the text parameter"""
        return text

    @hug.post('/happy_birthday', examples="name=HUG&age=1")
    def birthday(name, age: hug.types.number=1):
        """Says happy birthday to a user"""
        return "Happy {age} Birthday {name}!".format(**locals())

    @hug.post()
    def noop(request, response):
        """Performs no action"""
        pass

    @hug.get()
    def string_docs(data: 'Takes data', ignore_directive: hug.directives.Timer) -> 'Returns data':
        """Annotations defined with strings should be documentation only"""
        pass

    @hug.get(private=True)
    def private():
        """Hidden from documentation"""
        pass

    documentation = api.http.documentation()
    assert 'test_documentation' in documentation['overview']

    assert '/hello_world' in documentation['handlers']
    assert '/echo' in documentation['handlers']
    assert '/happy_birthday' in documentation['handlers']
    assert '/birthday' not in documentation['handlers']
    assert '/noop' in documentation['handlers']
    assert '/string_docs' in documentation['handlers']
    assert '/private' not in documentation['handlers']

    assert documentation['handlers']['/hello_world']['GET']['usage'] == "Returns hello world"
    assert documentation['handlers']['/hello_world']['GET']['examples'] == ["/hello_world"]
    assert documentation['handlers']['/hello_world']['GET']['outputs']['content_type'] in [
        "application/json",
        "application/json; charset=utf-8"
    ]
    assert 'inputs' not in documentation['handlers']['/hello_world']['GET']

    assert 'text' in documentation['handlers']['/echo']['POST']['inputs']['text']['type']
    assert 'default' not in documentation['handlers']['/echo']['POST']['inputs']['text']

    assert 'number' in documentation['handlers']['/happy_birthday']['POST']['inputs']['age']['type']
    assert documentation['handlers']['/happy_birthday']['POST']['inputs']['age']['default'] == 1

    assert 'inputs' not in documentation['handlers']['/noop']['POST']

    assert documentation['handlers']['/string_docs']['GET']['inputs']['data']['type'] == 'Takes data'
    assert documentation['handlers']['/string_docs']['GET']['outputs']['type'] == 'Returns data'
    assert 'ignore_directive' not in documentation['handlers']['/string_docs']['GET']['inputs']

    @hug.post(versions=1)  # noqa
    def echo(text):
        """V1 Docs"""
        return 'V1'

    @hug.post(versions=2)  # noqa
    def echo(text):
        """V1 Docs"""
        return 'V2'

    @hug.post(versions=2)
    def test(text):
        """V1 Docs"""
        return True

    @hug.get(requires=test)
    def unversioned():
        return 'Hello'

    @hug.get(versions=False)
    def noversions():
        pass

    @hug.extend_api('/fake', base_url='/api')
    def extend_with():
        import tests.module_fake_simple
        return (tests.module_fake_simple, )

    versioned_doc = api.http.documentation()
    assert 'versions' in versioned_doc
    assert 1 in versioned_doc['versions']
    assert 2 in versioned_doc['versions']
    assert False not in versioned_doc['versions']
    assert '/unversioned' in versioned_doc['handlers']
    assert '/echo' in versioned_doc['handlers']
    assert '/test' in versioned_doc['handlers']

    specific_version_doc = api.http.documentation(api_version=1)
    assert 'versions' in specific_version_doc
    assert '/echo' in specific_version_doc['handlers']
    assert '/unversioned' in specific_version_doc['handlers']
    assert specific_version_doc['handlers']['/unversioned']['GET']['requires'] == ['V1 Docs']
    assert '/test' not in specific_version_doc['handlers']

    specific_base_doc = api.http.documentation(base_url='/api')
    assert '/echo' not in specific_base_doc['handlers']
    assert '/fake/made_up_hello' in specific_base_doc['handlers']

    handler = api.http.documentation_404()
    response = StartResponseMock()
    handler(Request(create_environ(path='v1/doc')), response)
    documentation = json.loads(response.data.decode('utf8'))['documentation']
    assert 'versions' in documentation
    assert '/echo' in documentation['handlers']
    assert '/test' not in documentation['handlers']


def test_basic_documentation_output_type_accept():
    """Ensure API documentation works with selectable output types"""
    accept_output = hug.output_format.accept(
        {'application/json': hug.output_format.json,
         'application/pretty-json': hug.output_format.pretty_json},
        default=hug.output_format.json)
    with mock.patch.object(api.http, '_output_format', accept_output, create=True):
        handler = api.http.documentation_404()
        response = StartResponseMock()

        handler(Request(create_environ(path='v1/doc')), response)

    documentation = json.loads(response.data.decode('utf8'))['documentation']
    assert 'handlers' in documentation and 'overview' in documentation

    
def test_marshmallow_return_type_documentation():

    class Returns(marshmallow.Schema):
        "Return docs"

    @hug.post()
    def marshtest() -> Returns():
        pass

    doc = api.http.documentation()

    assert doc['handlers']['/marshtest']['POST']['outputs']['type'] == "Return docs"
