"""tests/test_types.py.

Tests the type validators included with Hug

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
import urllib
import json
from datetime import datetime
from decimal import Decimal

import pytest

import hug


def test_number():
    '''Tests that Hugs number type correctly converts and validates input'''
    assert hug.types.number('1') == 1
    assert hug.types.number(1) == 1
    with pytest.raises(ValueError):
        hug.types.number('bacon')


def test_range():
    '''Tests that Hugs range type successfully handles ranges of numbers'''
    assert hug.types.in_range(1, 10)('1') == 1
    assert hug.types.in_range(1, 10)(1) == 1
    with pytest.raises(ValueError):
        hug.types.in_range(1, 10)('bacon')
    with pytest.raises(ValueError):
        hug.types.in_range(1, 10)('15')


def test_multiple():
    '''Tests that Hugs multile type correctly forces values to come back as lists, but not lists of lists'''
    assert hug.types.multiple('value') == ['value']
    assert hug.types.multiple(['value1', 'value2']) == ['value1', 'value2']


def test_comma_separated_list():
    '''Tests that Hugs comma separated type correctly converts into a Python list'''
    assert hug.types.comma_separated_list('value') == ['value']
    assert hug.types.comma_separated_list('value1,value2') == ['value1', 'value2']



def test_float_number():
    '''Tests to ensure the float type correctly allows floating point values'''
    assert hug.types.float_number('1.1') == 1.1
    assert hug.types.float_number('1') == float(1)
    assert hug.types.float_number(1.1) == 1.1
    with pytest.raises(ValueError):
        hug.types.float_number('bacon')


def test_decimal():
    '''Tests to ensure the decimal type correctly allows decimal values'''
    assert hug.types.decimal('1.1') == Decimal('1.1')
    assert hug.types.decimal('1') == Decimal('1')
    assert hug.types.decimal(1.1) == Decimal(1.1)
    with pytest.raises(ValueError):
        hug.types.decimal('bacon')


def test_boolean():
    '''Test to ensure the custom boolean type correctly supports boolean conversion'''
    assert hug.types.boolean('1') == True
    assert hug.types.boolean('T') == True
    assert hug.types.boolean('') == False
    assert hug.types.boolean('False') == True
    assert hug.types.boolean(False) == False


def test_mapping():
    '''Test to ensure the mapping type works as expected'''
    mapping_type = hug.types.mapping({'n': None, 'l': [], 's': set()})
    assert mapping_type('n') == None
    assert mapping_type('l') == []
    assert mapping_type('s') == set()
    with pytest.raises(KeyError):
        mapping_type('bacon')


def test_smart_boolean():
    '''Test to ensure that the smart boolean type works as expected'''
    assert hug.types.smart_boolean('true') == True
    assert hug.types.smart_boolean('t') == True
    assert hug.types.smart_boolean('1') == True
    assert hug.types.smart_boolean(1) == True
    assert hug.types.smart_boolean('') == False
    assert hug.types.smart_boolean('false') == False
    assert hug.types.smart_boolean('f') == False
    assert hug.types.smart_boolean('0') == False
    assert hug.types.smart_boolean(0) == False
    assert hug.types.smart_boolean(True) == True
    assert hug.types.smart_boolean(None) == False
    assert hug.types.smart_boolean(False) == False
    with pytest.raises(KeyError):
        hug.types.smart_boolean('bacon')


def test_text():
    '''Tests that Hugs text validator correctly handles basic values'''
    assert hug.types.text('1') == '1'
    assert hug.types.text(1) == '1'
    assert hug.types.text('text') == 'text'


def test_inline_dictionary():
    '''Tests that inline dictionary values are correctly handled'''
    assert hug.types.inline_dictionary('1:2') == {'1': '2'}
    assert hug.types.inline_dictionary('1:2|3:4') == {'1': '2', '3': '4'}
    with pytest.raises(ValueError):
        hug.types.inline_dictionary('1')


def test_one_of():
    '''Tests that Hug allows limiting a value to one of a list of values'''
    assert hug.types.one_of(('bacon', 'sausage', 'pancakes'))('bacon') == 'bacon'
    assert hug.types.one_of(['bacon', 'sausage', 'pancakes'])('sausage') == 'sausage'
    assert hug.types.one_of({'bacon', 'sausage', 'pancakes'})('pancakes') == 'pancakes'
    with pytest.raises(KeyError):
        hug.types.one_of({'bacon', 'sausage', 'pancakes'})('syrup')


def test_accept():
    '''Tests to ensure the accept type wrapper works as expected'''
    custom_converter = lambda value: value + " converted"
    custom_type = hug.types.accept(custom_converter, 'A string Value')
    with pytest.raises(TypeError):
        custom_type(1)


def test_accept_custom_exception_text():
    '''Tests to ensure it's easy to custom the exception text using the accept wrapper'''
    custom_converter = lambda value: value + " converted"
    custom_type = hug.types.accept(custom_converter, 'A string Value', 'Error occurred')
    assert custom_type('bacon') == 'bacon converted'
    with pytest.raises(ValueError):
        custom_type(1)


def test_accept_custom_exception_handlers():
    '''Tests to ensure it's easy to custom the exception text using the accept wrapper'''
    custom_converter = lambda value: (str(int(value)) if value else value) + " converted"
    custom_type = hug.types.accept(custom_converter, 'A string Value', exception_handlers={TypeError: '0 provided'})
    assert custom_type('1') == '1 converted'
    with pytest.raises(ValueError):
        custom_type('bacon')
    with pytest.raises(ValueError):
        custom_type(0)

    custom_type = hug.types.accept(custom_converter, 'A string Value', exception_handlers={TypeError: KeyError})
    with pytest.raises(KeyError):
        custom_type(0)


def test_accept_custom_cli_behavior():
    '''Tests to ensure it's easy to customize the cli behavior using the accept wrapper'''
    custom_type = hug.types.accept(hug.types.multiple, 'Multiple values', cli_behaviour={'type': list})
    assert custom_type.cli_behaviour == {'type': list, 'action': 'append'}


def test_json():
    '''Test to ensure that the json type correctly handles url encoded json, as well as direct json'''
    assert hug.types.json({'this': 'works'}) == {'this': 'works'}
    assert hug.types.json(json.dumps({'this': 'works'})) == {'this': 'works'}
    with pytest.raises(ValueError):
        hug.types.json('Invalid JSON')


def test_multi():
    '''Test to ensure that the multi type correctly handles a variety of value types'''
    multi_type = hug.types.multi(hug.types.json, hug.types.smart_boolean)
    assert multi_type({'this': 'works'}) == {'this': 'works'}
    assert multi_type(json.dumps({'this': 'works'})) == {'this': 'works'}
    assert multi_type('t') == True
    with pytest.raises(ValueError):
        multi_type('Bacon!')
