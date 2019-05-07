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

import re
from cgi import parse_multipart
from urllib.parse import parse_qs as urlencoded_converter

from falcon.util.uri import parse_query_string

from hug.format import content_type, underscore
from hug.json_module import json as json_converter


@content_type("text/plain")
def text(body, charset="utf-8", **kwargs):
    """Takes plain text data"""
    return body.read().decode(charset)


@content_type("application/json")
def json(body, charset="utf-8", **kwargs):
    """Takes JSON formatted data, converting it into native Python objects"""
    return json_converter.loads(text(body, charset=charset))


def _underscore_dict(dictionary):
    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = _underscore_dict(value)
        if isinstance(key, str):
            key = underscore(key)
        new_dictionary[key] = value
    return new_dictionary


def json_underscore(body, charset="utf-8", **kwargs):
    """Converts JSON formatted date to native Python objects.

    The keys in any JSON dict are transformed from camelcase to underscore separated words.
    """
    return _underscore_dict(json(body, charset=charset))


@content_type("application/x-www-form-urlencoded")
def urlencoded(body, charset="ascii", **kwargs):
    """Converts query strings into native Python objects"""
    return parse_query_string(text(body, charset=charset), False)


@content_type("multipart/form-data")
def multipart(body, content_length=0, **header_params):
    """Converts multipart form data into native Python objects"""
    header_params.setdefault("CONTENT-LENGTH", content_length)
    if header_params and "boundary" in header_params:
        if type(header_params["boundary"]) is str:
            header_params["boundary"] = header_params["boundary"].encode()

    form = parse_multipart((body.stream if hasattr(body, "stream") else body), header_params)
    for key, value in form.items():
        if type(value) is list and len(value) is 1:
            form[key] = value[0]
    return form
