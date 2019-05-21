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

from falcon import *

from hug import (
    defaults,
    directives,
    exceptions,
    format,
    input_format,
    introspect,
    middleware,
    output_format,
    redirect,
    route,
    test,
    transform,
    types,
    use,
    validate,
)
from hug._version import current
from hug.api import API
from hug.decorators import (
    context_factory,
    default_input_format,
    default_output_format,
    delete_context,
    directive,
    extend_api,
    middleware_class,
    reqresp_middleware,
    request_middleware,
    response_middleware,
    startup,
    wraps,
)
from hug.route import (
    call,
    cli,
    connect,
    delete,
    exception,
    get,
    get_post,
    head,
    http,
    local,
    not_found,
    object,
    options,
    patch,
    post,
    put,
    sink,
    static,
    trace,
)
from hug.types import create as type

from hug import (
    authentication,
)  # isort:skip - must be imported last for defaults to have access to all modules

from hug import development_runner  # isort:skip

try:  # pragma: no cover - defaulting to uvloop if it is installed
    import uvloop
    import asyncio

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except (ImportError, AttributeError):
    pass

__version__ = current
