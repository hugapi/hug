"""tests/test_transform.py.

Test to ensure hugs built in transform functions work as expected

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


def test_content_type():
    """Test to ensure the transformer used can change based on the provided content-type"""
    transformer = hug.transform.content_type({"application/json": int, "text/plain": str})

    class FakeRequest(object):
        content_type = "application/json"

    request = FakeRequest()
    assert transformer("1", request) == 1

    request.content_type = "text/plain"
    assert transformer(2, request) == "2"

    request.content_type = "undefined"
    transformer({"data": "value"}, request) == {"data": "value"}


def test_suffix():
    """Test to ensure transformer content based on the end suffix of the URL works as expected"""
    transformer = hug.transform.suffix({".js": int, ".txt": str})

    class FakeRequest(object):
        path = "hey.js"

    request = FakeRequest()
    assert transformer("1", request) == 1

    request.path = "hey.txt"
    assert transformer(2, request) == "2"

    request.path = "hey.undefined"
    transformer({"data": "value"}, request) == {"data": "value"}


def test_prefix():
    """Test to ensure transformer content based on the end prefix of the URL works as expected"""
    transformer = hug.transform.prefix({"js/": int, "txt/": str})

    class FakeRequest(object):
        path = "js/hey"

    request = FakeRequest()
    assert transformer("1", request) == 1

    request.path = "txt/hey"
    assert transformer(2, request) == "2"

    request.path = "hey.undefined"
    transformer({"data": "value"}, request) == {"data": "value"}


def test_all():
    """Test to ensure transform.all allows chaining multiple transformations as expected"""

    def annotate(data, response):
        return {"Text": data}

    assert hug.transform.all(str, annotate)(1, response="hi") == {"Text": "1"}
