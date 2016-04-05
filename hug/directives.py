"""hug/directives.py

Defines the directives built into hug. Directives allow attaching behaviour to an API handler based simply
on an argument it takes and that arguments default value. The directive gets called with the default supplied,
ther request data, and api_version. The result of running the directive method is then set as the argument value.
Directive attributes are always prefixed with 'hug_'

Copyright (C) 2016  Timothy Edmund Crosley

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
from __future__ import absolute_import

from functools import partial
from timeit import default_timer as python_timer

from hug import introspect


def _built_in_directive(directive):
    """Marks a callable as a built-in directive"""
    directive.directive = True
    return directive


@_built_in_directive
class Timer(object):
    """Keeps track of time surpased since instantiation, outputed by doing float(instance)"""
    __slots__ = ('start', 'round_to')

    def __init__(self, round_to=None, **kwargs):
        self.start = python_timer()
        self.round_to = round_to

    def __float__(self):
        time_taken = python_timer() - self.start
        return round(time_taken, self.round_to) if self.round_to else time_taken

    def __int__(self):
        return int(round(float(self)))

    def __native_types__(self):
        return self.__float__()


@_built_in_directive
def module(default=None, api=None, **kwargs):
    """Returns the module that is running this hug API function"""
    return api.module if api else default


@_built_in_directive
def api(default=None, api=None, **kwargs):
    """Returns the api instance in which this API function is being ran"""
    return api if api else default


@_built_in_directive
def api_version(default=None, api_version=None, **kwargs):
    """Returns the current api_version as a directive for use in both request and not request handling code"""
    return api_version


@_built_in_directive
def documentation(default=None, api_version=None, module=None, **kwargs):
    """returns documentation for the current api"""
    api_version = default or api_version
    api = getattr(module, '__hug__', None)
    if api:
        return api.http.documentation(base_url="", api_version=api_version)


@_built_in_directive
def session(context_name='session', request=None, **kwargs):
    """Returns the session associated with the current request"""
    return request and request.context.get(context_name, None)


@_built_in_directive
def user(default=None, request=None, **kwargs):
    """Returns the current logged in user"""
    return request and request.context.get('user', None) or default


@_built_in_directive
class CurrentAPI(object):
    """Returns quick access to all api functions on the current version of the api"""
    __slots__ = ('api_version', 'api')

    def __init__(self, default=None, api_version=None, **kwargs):
        self.api_version = api_version
        self.api = api(**kwargs)

    def __getattr__(self, name):
        function = self.api.http.versioned.get(self.api_version, {}).get(name, None)
        if not function:
            function = self.api.http.versioned.get(None, {}).get(name, None)
        if not function:
            raise AttributeError('API Function {0} not found'.format(name))

        accepts = introspect.arguments(function.interface.function)
        if 'hug_api_version' in accepts:
            function = partial(function, hug_api_version=self.api_version)
        if 'hug_current_api' in accepts:
            function = partial(function, hug_current_api=self)

        return function
