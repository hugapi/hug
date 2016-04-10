"""hug/introspect.py

Defines built in hug functions to aid in introspection

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

import inspect
from types import MethodType


def is_method(function):
    """Returns True if the passed in function is identified as a method (NOT a function)"""
    return isinstance(function, MethodType)

def is_coroutine(function):
    """Returns True if the passed in function is a coroutine"""
    return function.__code__.co_flags & 0x0080 or getattr(function, '_is_coroutine', False)

def arguments(function, extra_arguments=0):
    """Returns the name of all arguments a function takes"""
    if not hasattr(function, '__code__'):
        return ()

    """#if asyncio_iscoroutinefunction(function):  # pragma: no cover
        #signature = inspect.signature(function)
        #if extra_arguments:
            #excluded_types = ()
        #else:
            #excluded_types = (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
        #return [p.name for p in signature.parameters.values() if p.kind not in excluded_types]"""

    return function.__code__.co_varnames[:function.__code__.co_argcount + extra_arguments]


def takes_kwargs(function):
    """Returns True if the supplied function takes keyword arguments"""
    """#if asyncio_iscoroutinefunction(function):   # pragma: no cover
        #signature = inspect.signature(function)
        #return any(p for p in signature.parameters.values()
                   #if p.kind == inspect.Parameter.VAR_KEYWORD)"""

    return bool(function.__code__.co_flags & 0x08)


def takes_kargs(function):
    """Returns True if the supplied functions takes extra non-keyword arguments"""
    """#if asyncio_iscoroutinefunction(function):   # pragma: no cover
        #signature = inspect.signature(function)
        #return any(p for p in signature.parameters.values()
                   #if p.kind == inspect.Parameter.VAR_POSITIONAL)"""

    return bool(function.__code__.co_flags & 0x04)


def takes_arguments(function, *named_arguments):
    """Returns the arguments that a function takes from a list of requested arguments"""
    return set(named_arguments).intersection(arguments(function))


def takes_all_arguments(function, *named_arguments):
    """Returns True if all supplied arguments are found in the function"""
    return bool(takes_arguments(function, *named_arguments) == set(named_arguments))


def generate_accepted_kwargs(function, *named_arguments):
    """Dynamically creates a function that when called with dictionary of arguments will produce a kwarg that's
       compatible with the supplied function
    """
    if hasattr(function, '__code__') and takes_kwargs(function):
        function_takes_kwargs = True
        function_takes_arguments = []
    else:
        function_takes_kwargs = False
        function_takes_arguments = takes_arguments(function, *named_arguments)

    def accepted_kwargs(kwargs):
        if function_takes_kwargs:
            return kwargs
        elif function_takes_arguments:
            return {key: value for key, value in kwargs.items() if key in function_takes_arguments}
        else:
            return {}
    return accepted_kwargs
