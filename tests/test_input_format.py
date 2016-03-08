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
from io import BytesIO

import hug


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
