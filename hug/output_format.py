"""hug/output_format.py

Defines Hug's built-in output formatting methods

Copyright (C) 2015  Timothy Edmund Crosley

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
import json as json_converter
from datetime import date, datetime

from hug.format import content_type


def _json_converter(item):
    if isinstance(item, (date, datetime)):
        return item.isoformat()
    elif isinstance(item, bytes):
        return item.decode('utf8')
    elif getattr(item, '__native_types__', None):
        return item.__native_types__()
    raise TypeError("Type not serializable")


@content_type('application/json')
def json(content, **kwargs):
    '''JSON (Javascript Serialized Object Notation)'''
    if isinstance(content, tuple) and getattr(content, '_fields', None):
        content = {field: getattr(content, field) for field in content._fields}
    return json_converter.dumps(content, default=_json_converter, **kwargs).encode('utf8')


@content_type('text/plain')
def text(content):
    '''Free form UTF8 text'''
    return str(content).encode('utf8')


def _camelcase(dictionary):
    if not isinstance(dictionary, dict):
        return dictionary

    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(key, str):
            key = key[0] + "".join(key.title().split('_'))[1:]
        new_dictionary[key] = _camelcase(value)
    return new_dictionary


@content_type('application/json')
def json_camelcase(content):
    '''JSON (Javascript Serialized Object Notation) with all keys camelCased'''
    return json(_camelcase(content))


@content_type('application/json')
def pretty_json(content):
    '''JSON (Javascript Serialized Object Notion) pretty printed and indented'''
    return json(content, indent=4, separators=(',', ': '))
