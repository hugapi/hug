"""tests/test_interface.py.

Tests hug's defined interfaces (HTTP, CLI, & Local)

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


@hug.http(("/namer", "/namer/{name}"), ("GET", "POST"), versions=(None, 2))
def namer(name=None):
    return name


class TestHTTP(object):
    """Tests the functionality provided by hug.interface.HTTP"""

    def test_urls(self):
        """Test to ensure HTTP interface correctly returns URLs associated with it"""
        assert namer.interface.http.urls() == ["/namer", "/namer/{name}"]

    def test_url(self):
        """Test to ensure HTTP interface correctly automatically returns URL associated with it"""
        assert namer.interface.http.url() == "/namer"
        assert namer.interface.http.url(name="tim") == "/namer/tim"
        assert namer.interface.http.url(name="tim", version=2) == "/v2/namer/tim"

        with pytest.raises(KeyError):
            namer.interface.http.url(undefined="not a variable")

        with pytest.raises(KeyError):
            namer.interface.http.url(version=10)

    def test_gather_parameters(self):
        """Test to ensure gathering parameters works in the expected way"""

        @hug.get()
        def my_example_api(body):
            return body

        assert (
            hug.test.get(
                __hug__, "my_example_api", body="", headers={"content-type": "application/json"}
            ).data
            == None
        )


class TestLocal(object):
    """Test to ensure hug.interface.Local functionality works as expected"""

    def test_local_method(self):
        class MyObject(object):
            @hug.local()
            def my_method(self, argument_1: hug.types.number):
                return argument_1

        instance = MyObject()
        assert instance.my_method(10) == 10
