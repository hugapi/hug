"""hug/store.py.

A collecton of native stores which can be used with, among others, the session middleware.

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
from hug.exceptions import StoreKeyNotFound


class InMemoryStore:
    """
    Naive store class which can be used for the session middleware and unit tests.
    It is not thread-safe and no data will survive the lifecycle of the hug process.
    Regard this as a blueprint for more useful and probably more complex store implementations, for example stores
    which make use of databases like Redis, PostgreSQL or others.
    """
    def __init__(self):
        self._data = {}

    def get(self, key):
        """Get data for given store key. Raise hug.exceptions.StoreKeyNotFound if key does not exist."""
        try:
            data = self._data[key]
        except KeyError:
            raise StoreKeyNotFound(key)
        return data

    def exists(self, key):
        """Return whether key exists or not."""
        return key in self._data

    def set(self, key, data):
        """Set data object for given store key."""
        self._data[key] = data

    def delete(self, key):
        """Delete data for given store key."""
        if key in self._data:
            del self._data[key]
