"""tests/test_input_format.py.

Tests the input format handlers included with Hug

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
import os
from cgi import parse_header
from io import BytesIO

import hug
import requests

from .constants import BASE_DIRECTORY


def test_text():
    """Ensure that plain text input format works as intended"""
    test_data = BytesIO(b'{"a": "b"}')
    assert hug.input_format.text(test_data) == '{"a": "b"}'


def test_json():
    """Ensure that the json input format works as intended"""
    test_data = BytesIO(b'{"a": "b"}')
    assert hug.input_format.json(test_data) == {'a': 'b'}


def test_json_underscore():
    """Ensure that camelCase keys can be converted into under_score for easier use within Python"""
    test_data = BytesIO(b'{"CamelCase": {"becauseWeCan": "ValueExempt"}}')
    assert hug.input_format.json_underscore(test_data) == {'camel_case': {'because_we_can': 'ValueExempt'}}


def test_urlencoded():
    """Ensure that urlencoded input format works as intended"""
    test_data = BytesIO(b'foo=baz&foo=bar&name=John+Doe')
    assert hug.input_format.urlencoded(test_data) == {'name': 'John Doe', 'foo': ['baz', 'bar']}


def test_multipart():
    """Ensure multipart form data works as intended"""
    with open(os.path.join(BASE_DIRECTORY, 'artwork', 'koala.png'),'rb') as koala:
        prepared_request = requests.Request('POST', 'http://localhost/', files={'koala': koala}).prepare()
        koala.seek(0)
        file_content = hug.input_format.multipart(BytesIO(prepared_request.body),
                                                  **parse_header(prepared_request.headers['Content-Type'])[1])['koala']
        assert file_content == koala.read()
