"""hug/__init__.py

Everyone needs a hug every once in a while. Even API developers. Hug aims to make developing Python driven APIs as
simple as possible, but no simpler.

Hug's Design Objectives:

- Make developing a Python driven API as succint as a written definition.
- The framework should encourage code that self-documents.
- It should be fast. Never should a developer feel the need to look somewhere else for performance reasons.
- Writing tests for APIs written on-top of Hug should be easy and intuitive.
- Magic done once, in an API, is better then pushing the problem set to the user of the API.
- Be the basis for next generation Python APIs, embracing the latest technology.

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
from hug import directives, documentation, format, input_format, output_format, run, test, types
from hug._version import current
from hug.decorators import (call, cli, connect, default_input_format, default_output_format,
                            delete, directive, extend_api, get, head, not_found, options,
                            patch, post, put, request_middleware, response_middleware, trace)

from hug import defaults  # isort:skip - must be imported last for defaults to have access to all modules

__version__ = current
__all__ = ['run', 'types', 'test', 'input_format', 'output_format', 'documentation', 'call', 'delete', 'get', 'post',
           'put', 'options', 'connect', 'head', 'patch', 'trace', 'terminal', 'format', '__version__', 'defaults',
           'directives', 'default_output_format', 'default_input_format', 'extend_api', 'directive',
           'request_middleware', 'response_middleware', 'not_found', 'cli']
