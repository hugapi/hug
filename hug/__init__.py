"""hug/__init__.py.

Everyone needs a hug every once in a while. Even API developers. Hug aims to make developing Python driven APIs as simple as possible, but no simpler.

Hug's Design Objectives:

- Make developing a Python driven API as succint as a written definition.
- The framework should encourage code that self-documents.
- It should be fast. Never should a developer feel the need to look somewhere else for performance reasons.
- Writing tests for APIs written on-top of Hug should be easy and intuitive.
- Magic done once, in an API, is better then pushing the problem set to the user of the API.

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
from hug.decorators import call, get, post, put, delete
from hug import run
from hug.run import terminal
from hug import types

__version__ = "0.0.2"