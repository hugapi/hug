"""tests/test_decorators.py.

Tests that class based hug routes interact as expected

Copyright (C) 2015 Timothy Edmund Crosley

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
import sys
import hug

api = sys.modules[__name__]


def test_simple_class_based_view():
    '''Test creating class based routers'''
    @hug.classy.urls('/endpoint', requires=())
    class MyClass(object):

        @hug.classy.get()
        def my_method(self):
            return 'hi there!'

        @hug.classy.post()
        def my_method_two(self):
            return 'bye'

    assert hug.test.get(api, 'endpoint').data == 'hi there!'
    assert hug.test.post(api, 'endpoint').data == 'bye'


def test_simple_class_based_method_view():
    '''Test creating class based routers using method mappings'''
    @hug.classy.auto_http_methods()
    class EndPoint(object):

        def get(self):
            return 'hi there!'

        def post(self):
            return 'bye'

    assert hug.test.get(api, 'endpoint').data == 'hi there!'
    assert hug.test.post(api, 'endpoint').data == 'bye'


def test_routing_class_based_method_view_with_sub_routing():
    '''Test creating class based routers using method mappings, then overriding url on sub method'''
    @hug.classy.auto_http_methods()
    class EndPoint(object):

        def get(self):
            return 'hi there!'

        @hug.classy.urls('/home/')
        def post(self):
            return 'bye'

    assert hug.test.get(api, 'endpoint').data == 'hi there!'
    assert hug.test.post(api, 'home').data == 'bye'


def test_routing_instance():
    '''Test to ensure its possible to route a class after it is instanciated'''
    class EndPoint(object):

        @hug.classy
        def one(self):
            return 'one'

        @hug.classy
        def two(self):
            return 2

    hug.classy.get()(EndPoint())
    assert hug.test.get(api, 'one').data == 'one'
    assert hug.test.get(api, 'two').data == 2
