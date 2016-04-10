"""tests/test_store.py.

Tests to ensure that the native stores work correctly.

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

from hug.exceptions import StoreKeyNotFound
from hug.store import InMemoryStore

stores_to_test = [
    InMemoryStore()
]


@pytest.mark.parametrize('store', stores_to_test)
def test_stores_generically(store):
    key = 'test-key'
    data = {
        'user': 'foo',
        'authenticated': False
    }

    # Key should not exist
    assert not store.exists(key)

    # Set key with custom data, verify the key exists and expect correct data to be returned
    store.set(key, data)
    assert store.exists(key)
    assert store.get(key) == data

    # Expect exception if unknown session key was requested
    with pytest.raises(StoreKeyNotFound):
        store.get('unknown')

    # Delete key
    store.delete(key)
    assert not store.exists(key)
