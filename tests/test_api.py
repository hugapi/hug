"""tests/test_api.py.

Tests to ensure the API object that stores the state of each individual hug endpoint works as expected

Copyright (C) 2016 Timothy Edmund Crosley

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
import pytest

import hug

api = hug.API(__name__)


class TestAPI(object):
    """A collection of tests to ensure the hug API object interacts as expected"""

    def test_singleton(self):
        """Test to ensure there can only be one hug API per module"""
        assert hug.API(__name__) == api

    def test_context(self):
        """Test to ensure the hug singleton provides a global modifiable context"""
        assert not hasattr(hug.API(__name__), '_context')
        assert hug.API(__name__).context == {}
        assert hasattr(hug.API(__name__), '_context')

    def test_dynamic(self):
        """Test to ensure it's possible to dynamically create new modules to house APIs based on name alone"""
        new_api = hug.API('module_created_on_the_fly')
        assert new_api.module.__name__ == 'module_created_on_the_fly'
        import module_created_on_the_fly
        assert module_created_on_the_fly
        assert module_created_on_the_fly.__hug__ == new_api


def test_from_object():
    """Test to ensure it's possible to rechieve an API singleton from an arbitrary object"""
    assert hug.api.from_object(TestAPI) == api


def test_api_fixture(hug_api):
    """Ensure it's possible to dynamically insert a new hug API on demand"""
    assert isinstance(hug_api, hug.API)
    assert hug_api != api


def test_anonymous():
    """Ensure it's possible to create anonymous APIs"""
    assert hug.API() != hug.API() != api
    assert hug.API().module == None
    assert hug.API().name == ''
    assert hug.API(name='my_name').name == 'my_name'
    assert hug.API(doc='Custom documentation').doc == 'Custom documentation'


def test_api_routes(hug_api):
    """Ensure http API can return a quick mapping all urls to method"""
    hug_api.http.base_url = '/root'

    @hug.get(api=hug_api)
    def my_route():
        pass

    @hug.post(api=hug_api)
    def my_second_route():
        pass

    @hug.cli(api=hug_api)
    def my_cli_command():
        pass

    assert list(hug_api.http.urls()) == ['/root/my_route', '/root/my_second_route']
    assert list(hug_api.http.handlers()) == [my_route.interface.http, my_second_route.interface.http]
    assert list(hug_api.handlers()) == [my_route.interface.http, my_second_route.interface.http,
                                        my_cli_command.interface.cli]


def test_cli_interface_api_with_exit_codes(hug_api_error_exit_codes_enabled):
    api = hug_api_error_exit_codes_enabled

    @hug.object(api=api)
    class TrueOrFalse:
        @hug.object.cli
        def true(self):
            return True

        @hug.object.cli
        def false(self):
            return False

    api.cli(args=[None, 'true'])

    with pytest.raises(SystemExit):
        api.cli(args=[None, 'false'])


def test_cli_interface_api_without_exit_codes():
    @hug.object(api=api)
    class TrueOrFalse:
        @hug.object.cli
        def true(self):
            return True

        @hug.object.cli
        def false(self):
            return False

    api.cli(args=[None, 'true'])
    api.cli(args=[None, 'false'])
