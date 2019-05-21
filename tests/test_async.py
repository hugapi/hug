"""hug/test.py.

Tests the support for asynchronous method using asyncio async def

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

import asyncio

import hug

loop = asyncio.get_event_loop()
api = hug.API(__name__)


def test_basic_call_async():
    """ The most basic Happy-Path test for Hug APIs using async """

    @hug.call()
    async def hello_world():
        return "Hello World!"

    assert loop.run_until_complete(hello_world()) == "Hello World!"


def tested_nested_basic_call_async():
    """Test to ensure the most basic call still works if applied to a method"""

    @hug.call()
    async def hello_world(self=None):
        return await nested_hello_world()

    @hug.local()
    async def nested_hello_world(self=None):
        return "Hello World!"

    assert hello_world.interface.http
    assert loop.run_until_complete(hello_world()) == "Hello World!"
    assert hug.test.get(api, "/hello_world").data == "Hello World!"


def test_basic_call_on_method_async():
    """Test to ensure the most basic call still works if applied to a method"""

    class API(object):
        @hug.call()
        async def hello_world(self=None):
            return "Hello World!"

    api_instance = API()
    assert api_instance.hello_world.interface.http
    assert loop.run_until_complete(api_instance.hello_world()) == "Hello World!"
    assert hug.test.get(api, "/hello_world").data == "Hello World!"


def test_basic_call_on_method_through_api_instance_async():
    """Test to ensure instance method calling via async works as expected"""

    class API(object):
        def hello_world(self):
            return "Hello World!"

    api_instance = API()

    @hug.call()
    async def hello_world():
        return api_instance.hello_world()

    assert api_instance.hello_world() == "Hello World!"
    assert hug.test.get(api, "/hello_world").data == "Hello World!"


def test_basic_call_on_method_registering_without_decorator_async():
    """Test to ensure async methods can be used without decorator"""

    class API(object):
        def __init__(self):
            hug.call()(self.hello_world_method)

        async def hello_world_method(self):
            return "Hello World!"

    api_instance = API()

    assert loop.run_until_complete(api_instance.hello_world_method()) == "Hello World!"
    assert hug.test.get(api, "/hello_world_method").data == "Hello World!"
