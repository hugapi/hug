"""hug/redirect.py

Implements convenience redirect methods that raise a redirection exception when called

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

import falcon


def to(location, code=falcon.HTTP_302):
    """Redirects to the specified location using the provided http_code (defaults to HTTP_302 FOUND)"""
    raise falcon.http_status.HTTPStatus(code, {'location': location})


def permanent(location):
    """Redirects to the specified location using HTTP 301 status code"""
    to(location, falcon.HTTP_301)


def found(location):
    """Redirects to the specified location using HTTP 302 status code"""
    to(location, falcon.HTTP_302)


def see_other(location):
    """Redirects to the specified location using HTTP 303 status code"""
    to(location, falcon.HTTP_303)


def temporary(location):
    """Redirects to the specified location using HTTP 307 status code"""
    to(location, falcon.HTTP_307)


def not_found(*args, **kwargs):
    """Redirects request handling to the not found render"""
    raise falcon.HTTPNotFound()
