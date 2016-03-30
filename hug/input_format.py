"""hug/input_formats.py

Defines the built-in Hug input_formatting handlers

Copyright (C) 2016  Timothy Edmund Crosley

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
from __future__ import absolute_import

import json as json_converter
import re

from hug.format import content_type, underscore

RE_CHARSET = re.compile("charset=(?P<charset>[^;]+)")


def separate_encoding(content_type, default=None):
    """Separates out the encoding from the content_type and returns both in a tuple (content_type, encoding)"""
    encoding = default
    if content_type and ";" in content_type:
        content_type, rest = content_type.split(";", 1)
        charset = RE_CHARSET.search(rest)
        if charset:
            encoding = charset.groupdict().get('charset', encoding).strip()

    return (content_type, encoding)


@content_type('text/plain')
def text(body, encoding='utf-8'):
    """Takes plain text data"""
    return body.read().decode(encoding)


@content_type('application/json')
def json(body, encoding='utf-8'):
    """Takes JSON formatted data, converting it into native Python objects"""
    return json_converter.loads(text(body, encoding=encoding))


def _underscore_dict(dictionary):
    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = _underscore_dict(value)
        if isinstance(key, str):
            key = underscore(key)
        new_dictionary[key] = value
    return new_dictionary


def json_underscore(body):
    """Converts JSON formatted date to native Python objects.

    The keys in any JSON dict are transformed from camelcase to underscore separated words.
    """
    return _underscore_dict(json(body))
