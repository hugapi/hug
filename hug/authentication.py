"""hug/authentication.py

Provides the basic built-in authentication helper functions

Copyright (C) 2015  Timothy Edmund Crosley

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
import base64
import binascii

from falcon import HTTPUnauthorized


def authenticator(function):
    def wrapper(verify_user):
        def authenticate(request, response, **kwargs):
            result = function(request, response, verify_user, **kwargs)
            if result is None:
                raise HTTPUnauthorized('Authentication Required',
                                       'Please provided valid {0} credentials'.format(function.__doc__))
            if result is False:
                raise HTTPUnauthorized('Invalid Authentication',
                                       'Provided {0} credentials were invalid'.format(function.__doc__))
            request.context['user'] = result
            return True

        return authenticate
    wrapper.__doc__ = function.__doc__
    return wrapper


@authenticator
def basic(request, response, verify_user, **kwargs):
    '''Basic HTTP Authentication'''
    http_auth = request.auth
    response.set_header('WWW-Authenticate', 'Basic')
    if http_auth is None:
        return

    if isinstance(http_auth, bytes):
        http_auth = http_auth.decode('utf8')
    try:
        auth_type, user_and_key = http_auth.split(' ', 1)
    except ValueError:
        raise HTTPUnauthorized('Authentication Error',
                               'Authentication header is improperly formed')


    if auth_type.lower() == 'basic':
        try:
            user_id, key = base64.decodebytes(bytes(user_and_key.strip(), 'utf8')).decode('utf8').split(':', 1)
            user = verify_user(user_id, key)
            if user:
                response.set_header('WWW-Authenticate', '')
                return user
        except (binascii.Error, ValueError):
            raise HTTPUnauthorized('Authentication Error',
                                   'Unable to determine user and password with provided encoding')
    return False


def verify(user, password):
    '''Returns a simple verification callback that simply verifies that the users and password match that provided'''
    def verify_user(user_name, user_password):
        if user_name == user and user_password == password:
            return user_name
        return False
    return verify_user
