"""hug/format.py

Defines formatting utility methods that are common both to input and output formatting and aid in general formatting of
fields and content

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
from cgi import parse_header

from hug import _empty as empty

UNDERSCORE = (re.compile("(.)([A-Z][a-z]+)"), re.compile("([a-z0-9])([A-Z])"))


def parse_content_type(content_type):
    """Separates out the parameters from the content_type and returns both in a tuple (content_type, parameters)"""
    if content_type is not None and ";" in content_type:
        return parse_header(content_type)
    return (content_type, empty.dict)


def content_type(content_type):
    """Attaches the supplied content_type to a Hug formatting function"""

    def decorator(method):
        method.content_type = content_type
        return method

    return decorator


def underscore(text):
    """Converts text that may be camelcased into an underscored format"""
    return UNDERSCORE[1].sub(r"\1_\2", UNDERSCORE[0].sub(r"\1_\2", text)).lower()


def camelcase(text):
    """Converts text that may be underscored into a camelcase format"""
    return text[0] + "".join(text.title().split("_"))[1:]
