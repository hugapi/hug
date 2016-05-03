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
from cgi import parse_multipart
from urllib.parse import parse_qs as urlencoded_converter

from falcon.util.uri import parse_query_string

from hug.format import content_type, underscore


@content_type('text/plain')
def text(body, header_params={'charset': 'utf-8'}):
    """Takes plain text data"""
    encoding = header_params and header_params.get('charset', None)
    data = body.read()
    if encoding:
        return data.decode(encoding)
    return data.decode()


@content_type('application/json')
def json(body, header_params={'charset': 'utf-8'}):
    """Takes JSON formatted data, converting it into native Python objects"""
    return json_converter.loads(text(body, header_params=header_params))


def _underscore_dict(dictionary):
    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = _underscore_dict(value)
        if isinstance(key, str):
            key = underscore(key)
        new_dictionary[key] = value
    return new_dictionary


def json_underscore(body, header_params={'charset': 'utf-8'}):
    """Converts JSON formatted date to native Python objects.

    The keys in any JSON dict are transformed from camelcase to underscore separated words.
    """
    return _underscore_dict(json(body, header_params=header_params))


@content_type('application/x-www-form-urlencoded')
def urlencoded(body, header_params={'charset': 'ascii'}):
    """Converts query strings into native Python objects"""
    return parse_query_string(text(body, header_params=header_params), False)


@content_type('multipart/form-data')
def multipart(body, header_params=None):
    """Converts multipart form data into native Python objects"""
    if 'boundary' in header_params:
        if type(header_params['boundary']) is str:
            header_params['boundary'] = header_params['boundary'].encode()
    form = parse_multipart(body, header_params)
    for k, v in form.items():
        if type(v) is list and len(v) is 1:
            form[k] = v[0]
    return form
