"""tests/test_directives.py.

Tests to ensure that directives interact in the anticipated manner

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
from base64 import b64encode

import pytest

import hug

api = hug.API(__name__)

# Fix flake8 undefined names (F821)
__hug__ = __hug__  # noqa


def test_timer():
    """Tests that the timer directive outputs the correct format, and automatically attaches itself to an API"""
    timer = hug.directives.Timer()
    assert isinstance(timer.start, float)
    assert isinstance(float(timer), float)
    assert isinstance(int(timer), int)

    timer = hug.directives.Timer(3)
    assert isinstance(timer.start, float)
    assert isinstance(float(timer), float)
    assert isinstance(int(timer), int)
    assert isinstance(str(timer), str)
    assert isinstance(repr(timer), str)
    assert float(timer) < timer.start

    @hug.get()
    @hug.local()
    def timer_tester(hug_timer):
        return hug_timer

    assert isinstance(hug.test.get(api, 'timer_tester').data, float)
    assert isinstance(timer_tester(), hug.directives.Timer)


def test_module():
    """Test to ensure the module directive automatically includes the current API's module"""
    @hug.get()
    def module_tester(hug_module):
        return hug_module.__name__

    assert hug.test.get(api, 'module_tester').data == api.module.__name__


def test_api():
    """Ensure the api correctly gets passed onto a hug API function based on a directive"""
    @hug.get()
    def api_tester(hug_api):
        return hug_api == api

    assert hug.test.get(api, 'api_tester').data is True


def test_documentation():
    """Test documentation directive"""
    assert 'handlers' in hug.directives.documentation(api=api)


def test_api_version():
    """Ensure that it's possible to get the current version of an API based on a directive"""
    @hug.get(versions=1)
    def version_tester(hug_api_version):
        return hug_api_version

    assert hug.test.get(api, 'v1/version_tester').data == 1


def test_current_api():
    """Ensure that it's possible to retrieve methods from the same version of the API"""
    @hug.get(versions=1)
    def first_method():
        return "Success"

    @hug.get(versions=1)
    def version_call_tester(hug_current_api):
        return hug_current_api.first_method()

    assert hug.test.get(api, 'v1/version_call_tester').data == 'Success'

    @hug.get()
    def second_method():
        return "Unversioned"

    @hug.get(versions=2)  # noqa
    def version_call_tester(hug_current_api):
        return hug_current_api.second_method()

    assert hug.test.get(api, 'v2/version_call_tester').data == 'Unversioned'

    @hug.get(versions=3)  # noqa
    def version_call_tester(hug_current_api):
        return hug_current_api.first_method()

    with pytest.raises(AttributeError):
        hug.test.get(api, 'v3/version_call_tester').data


def test_user():
    """Ensure that it's possible to get the current authenticated user based on a directive"""
    user = 'test_user'
    password = 'super_secret'

    @hug.get(requires=hug.authentication.basic(hug.authentication.verify(user, password)))
    def authenticated_hello(hug_user):
        return hug_user

    token = b64encode('{0}:{1}'.format(user, password).encode('utf8')).decode('utf8')
    assert hug.test.get(api, 'authenticated_hello', headers={'Authorization': 'Basic {0}'.format(token)}).data == user


def test_session_directive():
    """Ensure that it's possible to retrieve the session withing a request using the built-in session directive"""
    @hug.request_middleware()
    def add_session(request, response):
        request.context['session'] = {'test': 'data'}

    @hug.local()
    @hug.get()
    def session_data(hug_session):
        return hug_session

    assert session_data() is None
    assert hug.test.get(api, 'session_data').data == {'test': 'data'}


def test_named_directives():
    """Ensure that it's possible to attach directives to named parameters"""
    @hug.get()
    def test(time: hug.directives.Timer=3):
        return time

    assert isinstance(test(1), int)

    test = hug.local()(test)
    assert isinstance(test(), hug.directives.Timer)


def test_local_named_directives():
    """Ensure that it's possible to attach directives to local function calling"""
    @hug.local()
    def test(time: __hug__.directive('timer')=3):
        return time

    assert isinstance(test(), hug.directives.Timer)

    @hug.local(directives=False)
    def test(time: __hug__.directive('timer')=3):
        return time

    assert isinstance(test(3), int)


def test_named_directives_by_name():
    """Ensure that it's possible to attach directives to named parameters using only the name of the directive"""
    @hug.get()
    @hug.local()
    def test(time: __hug__.directive('timer')=3):
        return time

    assert isinstance(test(), hug.directives.Timer)


def test_per_api_directives():
    """Test to ensure it's easy to define a directive within an API"""
    @hug.directive(apply_globally=False)
    def test(default=None, **kwargs):
        return default

    @hug.get()
    def my_api_method(hug_test='heyyy'):
        return hug_test

    assert hug.test.get(api, 'my_api_method').data == 'heyyy'


def test_user_directives():
    """Test the user directives functionality, to ensure it will provide the set user object"""
    @hug.get()  # noqa
    def try_user(user: hug.directives.user):
        return user

    assert hug.test.get(api, 'try_user').data is None

    @hug.get(requires=hug.authentication.basic(hug.authentication.verify('Tim', 'Custom password')))  # noqa
    def try_user(user: hug.directives.user):
        return user

    token = b'Basic ' + b64encode('{0}:{1}'.format('Tim', 'Custom password').encode('utf8'))
    assert hug.test.get(api, 'try_user', headers={'Authorization': token}).data == 'Tim'


def test_directives(hug_api):
    """Test to ensure cors directive works as expected"""
    assert hug.directives.cors('google.com') == 'google.com'

    @hug.get(api=hug_api)
    def cors_supported(cors: hug.directives.cors="*"):
        return True

    assert hug.test.get(hug_api, 'cors_supported').headers_dict['Access-Control-Allow-Origin'] == '*'
