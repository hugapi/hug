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


def test_from_object():
    """Test to ensure it's possible to rechieve an API singleton from an arbitrary object"""
    assert hug.api.from_object(TestAPI) == api
