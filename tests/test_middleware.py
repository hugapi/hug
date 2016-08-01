"""tests/test_middleware.py.

Tests the middleware integrated into Hug

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
from falcon.request import SimpleCookie

import hug
from hug.exceptions import SessionNotFound
from hug.middleware import LogMiddleware, SessionMiddleware
from hug.store import InMemoryStore

api = hug.API(__name__)

# Fix flake8 undefined names (F821)
__hug__ = __hug__  # noqa


def test_session_middleware():
    @hug.get()
    def count(request):
        session = request.context['session']
        counter = session.get('counter', 0) + 1
        session['counter'] = counter
        return counter

    def get_cookies(response):
        simple_cookie = SimpleCookie(response.headers_dict['set-cookie'])
        return {morsel.key: morsel.value for morsel in simple_cookie.values()}

    # Add middleware
    session_store = InMemoryStore()
    middleware = SessionMiddleware(session_store, cookie_name='test-sid')
    __hug__.http.add_middleware(middleware)

    # Get cookies from response
    response = hug.test.get(api, '/count')
    cookies = get_cookies(response)

    # Assert session cookie has been set and session exists in session store
    assert 'test-sid' in cookies
    sid = cookies['test-sid']
    assert session_store.exists(sid)
    assert session_store.get(sid) == {'counter': 1}

    # Assert session persists throughout the requests
    headers = {'Cookie': 'test-sid={}'.format(sid)}
    assert hug.test.get(api, '/count', headers=headers).data == 2
    assert session_store.get(sid) == {'counter': 2}

    # Assert a non-existing session cookie gets ignored
    headers = {'Cookie': 'test-sid=foobarfoo'}
    response = hug.test.get(api, '/count', headers=headers)
    cookies = get_cookies(response)
    assert response.data == 1
    assert not session_store.exists('foobarfoo')
    assert cookies['test-sid'] != 'foobarfoo'


def test_logging_middleware():
    output = []

    class Logger(object):
        def info(self, content):
            output.append(content)

    @hug.middleware_class()
    class CustomLogger(LogMiddleware):
        def __init__(self, logger=Logger()):
            super().__init__(logger=logger)

    @hug.get()
    def test(request):
        return 'data'

    hug.test.get(api, '/test')
    assert output[0] == 'Requested: GET /test None'
    assert len(output[1]) > 0
