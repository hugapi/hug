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
import hug
from hug.routing import CLIRouter, ExceptionRouter, NotFoundRouter, SinkRouter, StaticRouter, URLRouter

api = hug.API(__name__)


def test_simple_class_based_view():
    '''Test creating class based routers'''
    @hug.object.urls('/endpoint', requires=())
    class MyClass(object):

        @hug.object.get()
        def my_method(self):
            return 'hi there!'

        @hug.object.post()
        def my_method_two(self):
            return 'bye'

    assert hug.test.get(api, 'endpoint').data == 'hi there!'
    assert hug.test.post(api, 'endpoint').data == 'bye'


def test_simple_class_based_method_view():
    '''Test creating class based routers using method mappings'''
    @hug.object.http_methods()
    class EndPoint(object):

        def get(self):
            return 'hi there!'

        def post(self):
            return 'bye'

    assert hug.test.get(api, 'endpoint').data == 'hi there!'
    assert hug.test.post(api, 'endpoint').data == 'bye'


def test_routing_class_based_method_view_with_sub_routing():
    '''Test creating class based routers using method mappings, then overriding url on sub method'''
    @hug.object.http_methods()
    class EndPoint(object):

        def get(self):
            return 'hi there!'

        @hug.object.urls('/home/')
        def post(self):
            return 'bye'

    assert hug.test.get(api, 'endpoint').data == 'hi there!'
    assert hug.test.post(api, 'home').data == 'bye'


def test_routing_instance():
    '''Test to ensure its possible to route a class after it is instanciated'''
    class EndPoint(object):

        @hug.object
        def one(self):
            return 'one'

        @hug.object
        def two(self):
            return 2

    hug.object.get()(EndPoint())
    assert hug.test.get(api, 'one').data == 'one'
    assert hug.test.get(api, 'two').data == 2


class TestAPIRouter(object):
    '''Test to ensure the API router enables easily reusing all other routing types while routing to an API'''
    router = hug.route.API(__name__)

    def test_route_url(self):
        '''Test to ensure you can dynamically create a URL route attached to a hug API'''
        assert self.router.urls('/hi/').route == URLRouter('/hi/', api=api).route

    def test_not_found(self):
        '''Test to ensure you can dynamically create a Not Found route attached to a hug API'''
        assert self.router.not_found().route == NotFoundRouter(api=api).route

    def test_static(self):
        '''Test to ensure you can dynamically create a static route attached to a hug API'''
        assert self.router.static().route == StaticRouter(api=api).route

    def test_sink(self):
        '''Test to ensure you can dynamically create a sink route attached to a hug API'''
        assert self.router.sink().route == SinkRouter(api=api).route

    def test_exceptions(self):
        '''Test to ensure you can dynamically create an Exception route attached to a hug API'''
        assert self.router.exceptions().route == ExceptionRouter(api=api).route

    def test_cli(self):
        '''Test to ensure you can dynamically create a CLI route attached to a hug API'''
        assert self.router.cli().route == CLIRouter(api=api).route

    def test_object(self):
        '''Test to ensure it's possible to route objects through a specified API instance'''
        assert self.router.object().route == hug.route.Object(api=api).route
