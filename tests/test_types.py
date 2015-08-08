"""tests/test_types.py.

Tests the type validators included with hug

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
from datetime import datetime


def test_number():
    assert hug.types.number('1') == 1
    assert hug.types.number(1) == 1
    with pytest.raises(ValueError):
        hug.types.number('bacon')


def test_multiple():
    assert hug.types.multiple('value') == ['value']
    assert hug.types.multiple(['value1', 'value2']) == ['value1', 'value2']


def test_comma_separated_list():
    assert hug.types.comma_separated_list('value') == ['value']
    assert hug.types.comma_separated_list('value1,value2') == ['value1', 'value2']


def test_decimal():
    assert hug.types.decimal('1.1') == 1.1
    assert hug.types.decimal('1') == float(1)
    assert hug.types.decimal(1.1) == 1.1
    with pytest.raises(ValueError):
        hug.types.decimal('bacon')


def test_text():
    assert hug.types.text('1') == '1'
    assert hug.types.text(1) == '1'
    assert hug.types.text('text') == 'text'


def test_inline_dictionary():
    assert hug.types.inline_dictionary('1:2') == {'1': '2'}
    assert hug.types.inline_dictionary('1:2|3:4') == {'1': '2', '3': '4'}
    with pytest.raises(ValueError):
        hug.types.inline_dictionary('1')


def test_one_of():
    assert hug.types.one_of(('bacon', 'sausage', 'pancakes'))('bacon') == 'bacon'
    assert hug.types.one_of(['bacon', 'sausage', 'pancakes'])('sausage') == 'sausage'
    assert hug.types.one_of({'bacon', 'sausage', 'pancakes'})('pancakes') == 'pancakes'
    with pytest.raises(KeyError):
        hug.types.one_of({'bacon', 'sausage', 'pancakes'})('syrup')

