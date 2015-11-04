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
import sys
import pytest

import hug
from hug.middleware import SessionMiddleware

from falcon.request import SimpleCookie

api = sys.modules[__name__]


def test_session_middleware():
    class TestSessionStore:
        def __init__(self):
            self.sessions = {}

        def get(self, sid):
            data = self.sessions.get(sid, None)
            if data is None:
                raise SessionNotFound
            return data

        def exists(self, sid):
            return sid in self.sessions

        def set(self, sid, data):
            self.sessions[sid] = data

    @hug.get()
    def count(request):
        counter = request.context.get('counter', 0) + 1
        request.context['counter'] = counter
        return counter

    session_store = TestSessionStore()
    middleware = SessionMiddleware(session_store, cookie_name='test-sid')
    __hug__.add_middleware(middleware)

    # Session will be created upon first visit
    response = hug.test.get(api, '/count')

    simple_cookie = SimpleCookie(response.headers_dict['set-cookie'])
    cookies = {morsel.key: morsel.value for morsel in simple_cookie.values()}
    assert response.data == 1
    assert 'test-sid' in cookies
    sid = cookies['test-sid']
    assert sid in session_store.sessions

    # Session will persist throughout the requests
    headers = {'Cookie': 'test-sid={}'.format(sid)}
    assert hug.test.get(api, '/count', headers=headers).data == 2
