"""tests/test_use.py.

Tests to ensure hugs service consuming classes, that are the backbone of the seamless micro-service concept,
work as intended

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
import pytest
import hug
from hug import use
import requests


class TestService(object):
    """Test to ensure the base Service object works as a base Abstract service runner"""
    service = use.Service(version=1, timeout=100, raise_on=(500, ))

    def test_init(self):
        """Test to ensure base service instantiation populates expected attributes"""
        assert self.service.version == 1
        assert self.service.raise_on == (500, )
        assert self.service.timeout == 100

    def test_request(self):
        """Test to ensure the abstract service request method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.request('POST', 'endpoint')

    def test_get(self):
        """Test to ensure the abstract service get method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.get('endpoint')

    def test_post(self):
        """Test to ensure the abstract service post method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.post('endpoint')

    def test_delete(self):
        """Test to ensure the abstract service delete method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.delete('endpoint')

    def test_put(self):
        """Test to ensure the abstract service put method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.put('endpoint')

    def test_trace(self):
        """Test to ensure the abstract service trace method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.trace('endpoint')

    def test_patch(self):
        """Test to ensure the abstract service patch method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.patch('endpoint')

    def test_options(self):
        """Test to ensure the abstract service options method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.options('endpoint')

    def test_head(self):
        """Test to ensure the abstract service head method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.head('endpoint')

    def test_connect(self):
        """Test to ensure the abstract service connect method raises NotImplementedError to show its abstract nature"""
        with pytest.raises(NotImplementedError):
            self.service.connect('endpoint')


class TestHTTP(object):
    """Test to ensure the HTTP Service object enables pulling data from external HTTP services"""
    service = use.HTTP('http://www.google.com/', raise_on=404)

    def test_init(self):
        """Test to ensure HTTP service instantiation populates expected attributes"""
        assert self.service.endpoint == 'http://www.google.com/'
        assert self.service.raise_on == (404, )

    def test_request(self):
        """Test so ensure the HTTP service can successfully be used to pull data from an external service"""
        response = self.service.request('GET', 'search', query='api')
        assert response
        assert response.data

        with pytest.raises(requests.HTTPError):
            self.service.request('GET', 'not_found', query='api')


class TestLocal(object):
    """Test to ensure the Local Service object enables pulling data from internal hug APIs with minimal overhead"""
    service = use.Local(__name__)

    def test_init(self):
        """Test to ensure the Local service instantiation populates the expected attributes"""
        assert isinstance(self.service.api, hug.API)

    def test_request(self):
        """Test to ensure requesting data from a local service works as expected"""
        assert self.service.get('hello_world').data == 'Hi!'
        assert self.service.get('not_there').status_code == 404
        assert self.service.get('validation_error').status_code == 400

        self.service.raise_on = (404, 500)
        with pytest.raises(requests.HTTPError):
            assert self.service.get('not_there')

        with pytest.raises(requests.HTTPError):
            assert self.service.get('exception')


@hug.get()
def hello_world():
    return 'Hi!'


@hug.get()
def exception(response):
    response.status = hug.HTTP_500


@hug.get()
def validation_error(data):
    return data
