"""tests/test_exceptions.py.

Tests to ensure custom exceptions work and are formatted as expected

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
import hug
import pytest


def test_invalid_type_data():
    try:
        raise hug.exceptions.InvalidTypeData('not a good type')
    except hug.exceptions.InvalidTypeData as exception:
        error = exception

    assert error.message == 'not a good type'
    assert error.reasons is None

    try:
        raise hug.exceptions.InvalidTypeData('not a good type', [1, 2, 3])
    except hug.exceptions.InvalidTypeData as exception:
        error = exception

    assert error.message == 'not a good type'
    assert error.reasons == [1, 2, 3]

    with pytest.raises(Exception):
        try:
            raise hug.exceptions.InvalidTypeData()
        except hug.exceptions.InvalidTypeData as exception:
            pass
