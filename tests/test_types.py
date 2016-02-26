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
import json
import urllib
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from marshmallow import Schema, fields

import hug
from hug.exceptions import InvalidTypeData


def test_type():
    """Test to ensure the abstract Type object can't be used"""
    with pytest.raises(NotImplementedError):
        hug.types.Type()('value')


def test_number():
    """Tests that hug's number type correctly converts and validates input"""
    assert hug.types.number('1') == 1
    assert hug.types.number(1) == 1
    with pytest.raises(ValueError):
        hug.types.number('bacon')


def test_range():
    """Tests that hug's range type successfully handles ranges of numbers"""
    assert hug.types.in_range(1, 10)('1') == 1
    assert hug.types.in_range(1, 10)(1) == 1
    assert '1' in hug.types.in_range(1, 10).__doc__
    with pytest.raises(ValueError):
        hug.types.in_range(1, 10)('bacon')
    with pytest.raises(ValueError):
        hug.types.in_range(1, 10)('15')
    with pytest.raises(ValueError):
        hug.types.in_range(1, 10)(-34)


def test_less_than():
    """Tests that hug's less than type successfully limits the values passed in"""
    assert hug.types.less_than(10)('1') == 1
    assert hug.types.less_than(10)(1) == 1
    assert hug.types.less_than(10)(-10) == -10
    assert '10' in hug.types.less_than(10).__doc__
    with pytest.raises(ValueError):
        assert hug.types.less_than(10)(10)


def test_greater_than():
    """Tests that hug's greater than type succefully limis the values passed in"""
    assert hug.types.greater_than(10)('11') == 11
    assert hug.types.greater_than(10)(11) == 11
    assert hug.types.greater_than(10)(1000) == 1000
    assert '10' in hug.types.greater_than(10).__doc__
    with pytest.raises(ValueError):
        assert hug.types.greater_than(10)(9)


def test_multiple():
    """Tests that hug's multile type correctly forces values to come back as lists, but not lists of lists"""
    assert hug.types.multiple('value') == ['value']
    assert hug.types.multiple(['value1', 'value2']) == ['value1', 'value2']


def test_delimited_list():
    """Test to ensure hug's custom delimited list type function works as expected"""
    assert hug.types.delimited_list(',')('value1,value2') == ['value1', 'value2']
    assert hug.types.delimited_list(',')(['value1', 'value2']) == ['value1', 'value2']
    assert hug.types.delimited_list('|-|')('value1|-|value2|-|value3,value4') == ['value1', 'value2', 'value3,value4']
    assert ',' in hug.types.delimited_list(',').__doc__


def test_comma_separated_list():
    """Tests that hug's comma separated type correctly converts into a Python list"""
    assert hug.types.comma_separated_list('value') == ['value']
    assert hug.types.comma_separated_list('value1,value2') == ['value1', 'value2']


def test_float_number():
    """Tests to ensure the float type correctly allows floating point values"""
    assert hug.types.float_number('1.1') == 1.1
    assert hug.types.float_number('1') == float(1)
    assert hug.types.float_number(1.1) == 1.1
    with pytest.raises(ValueError):
        hug.types.float_number('bacon')


def test_decimal():
    """Tests to ensure the decimal type correctly allows decimal values"""
    assert hug.types.decimal('1.1') == Decimal('1.1')
    assert hug.types.decimal('1') == Decimal('1')
    assert hug.types.decimal(1.1) == Decimal(1.1)
    with pytest.raises(ValueError):
        hug.types.decimal('bacon')


def test_boolean():
    """Test to ensure the custom boolean type correctly supports boolean conversion"""
    assert hug.types.boolean('1') == True
    assert hug.types.boolean('T') == True
    assert hug.types.boolean('') == False
    assert hug.types.boolean('False') == True
    assert hug.types.boolean(False) == False


def test_mapping():
    """Test to ensure the mapping type works as expected"""
    mapping_type = hug.types.mapping({'n': None, 'l': [], 's': set()})
    assert mapping_type('n') == None
    assert mapping_type('l') == []
    assert mapping_type('s') == set()
    assert 'n' in mapping_type.__doc__
    with pytest.raises(KeyError):
        mapping_type('bacon')


def test_smart_boolean():
    """Test to ensure that the smart boolean type works as expected"""
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
    """Tests that hug's text validator correctly handles basic values"""
    assert hug.types.text('1') == '1'
    assert hug.types.text(1) == '1'
    assert hug.types.text('text') == 'text'
    with pytest.raises(ValueError):
        hug.types.text(['one', 'two'])

def test_uuid():
    """Tests that hug's text validator correctly handles UUID values
       Examples were taken from https://docs.python.org/3/library/uuid.html"""

    assert hug.types.uuid('{12345678-1234-5678-1234-567812345678}') == UUID('12345678-1234-5678-1234-567812345678')
    assert hug.types.uuid('12345678-1234-5678-1234-567812345678') == UUID('12345678123456781234567812345678')
    assert hug.types.uuid('12345678123456781234567812345678') == UUID('12345678-1234-5678-1234-567812345678')
    assert hug.types.uuid('urn:uuid:12345678-1234-5678-1234-567812345678') == \
           UUID('12345678-1234-5678-1234-567812345678')

    with pytest.raises(ValueError):
        hug.types.uuid(1)

    with pytest.raises(ValueError):
        # Invalid HEX character
        hug.types.uuid('12345678-1234-5678-1234-56781234567G')

    with pytest.raises(ValueError):
        # One character added
        hug.types.uuid('12345678-1234-5678-1234-5678123456781')
    with pytest.raises(ValueError):
        # One character removed
        hug.types.uuid('12345678-1234-5678-1234-56781234567')



def test_length():
    """Tests that hug's length type successfully handles a length range"""
    assert hug.types.length(1, 10)('bacon') == 'bacon'
    assert hug.types.length(1, 10)(42) == '42'
    assert '42' in hug.types.length(1, 42).__doc__
    with pytest.raises(ValueError):
        hug.types.length(1, 10)('bacon is the greatest food known to man')
    with pytest.raises(ValueError):
        hug.types.length(1, 10)('')
    with pytest.raises(ValueError):
        hug.types.length(1, 10)('bacon is th')


def test_shorter_than():
    """Tests that hug's shorter than type successfully limits the values passed in"""
    assert hug.types.shorter_than(10)('hi there') == 'hi there'
    assert hug.types.shorter_than(10)(1) == '1'
    assert hug.types.shorter_than(10)('') == ''
    assert '10' in hug.types.shorter_than(10).__doc__
    with pytest.raises(ValueError):
        assert hug.types.shorter_than(10)('there is quite a bit of text here, in fact way more than allowed')


def test_longer_than():
    """Tests that hug's greater than type succefully limis the values passed in"""
    assert hug.types.longer_than(10)('quite a bit of text here should be') == 'quite a bit of text here should be'
    assert hug.types.longer_than(10)(12345678910) == '12345678910'
    assert hug.types.longer_than(10)(100123456789100) == '100123456789100'
    assert '10' in hug.types.longer_than(10).__doc__
    with pytest.raises(ValueError):
        assert hug.types.longer_than(10)('short')


def test_cut_off():
    """Test to ensure that hug's cut_off type works as expected"""
    assert hug.types.cut_off(10)('text') == 'text'
    assert hug.types.cut_off(10)(10) == '10'
    assert hug.types.cut_off(10)('some really long text') == 'some reall'
    assert '10' in hug.types.cut_off(10).__doc__


def test_inline_dictionary():
    """Tests that inline dictionary values are correctly handled"""
    assert hug.types.inline_dictionary('1:2') == {'1': '2'}
    assert hug.types.inline_dictionary('1:2|3:4') == {'1': '2', '3': '4'}
    with pytest.raises(ValueError):
        hug.types.inline_dictionary('1')


def test_one_of():
    """Tests that hug allows limiting a value to one of a list of values"""
    assert hug.types.one_of(('bacon', 'sausage', 'pancakes'))('bacon') == 'bacon'
    assert hug.types.one_of(['bacon', 'sausage', 'pancakes'])('sausage') == 'sausage'
    assert hug.types.one_of({'bacon', 'sausage', 'pancakes'})('pancakes') == 'pancakes'
    assert 'bacon' in hug.types.one_of({'bacon', 'sausage', 'pancakes'}).__doc__
    with pytest.raises(KeyError):
        hug.types.one_of({'bacon', 'sausage', 'pancakes'})('syrup')


def test_accept():
    """Tests to ensure the accept type wrapper works as expected"""
    custom_converter = lambda value: value + " converted"
    custom_type = hug.types.accept(custom_converter, 'A string Value')
    with pytest.raises(TypeError):
        custom_type(1)


def test_accept_custom_exception_text():
    """Tests to ensure it's easy to custom the exception text using the accept wrapper"""
    custom_converter = lambda value: value + " converted"
    custom_type = hug.types.accept(custom_converter, 'A string Value', 'Error occurred')
    assert custom_type('bacon') == 'bacon converted'
    with pytest.raises(ValueError):
        custom_type(1)


def test_accept_custom_exception_handlers():
    """Tests to ensure it's easy to custom the exception text using the accept wrapper"""
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


def test_json():
    """Test to ensure that the json type correctly handles url encoded json, as well as direct json"""
    assert hug.types.json({'this': 'works'}) == {'this': 'works'}
    assert hug.types.json(json.dumps({'this': 'works'})) == {'this': 'works'}
    with pytest.raises(ValueError):
        hug.types.json('Invalid JSON')


def test_multi():
    """Test to ensure that the multi type correctly handles a variety of value types"""
    multi_type = hug.types.multi(hug.types.json, hug.types.smart_boolean)
    assert multi_type({'this': 'works'}) == {'this': 'works'}
    assert multi_type(json.dumps({'this': 'works'})) == {'this': 'works'}
    assert multi_type('t') == True
    with pytest.raises(ValueError):
        multi_type('Bacon!')


def test_chain():
    """Test to ensure that chaining together multiple types works as expected"""
    chain_type = hug.types.Chain(hug.types.text, hug.types.LongerThan(10))
    assert chain_type(12345678901) == "12345678901"
    with pytest.raises(ValueError):
        chain_type(1)


def test_nullable():
    """Test the concept of a nullable type"""
    nullable_type = hug.types.Nullable(hug.types.text, hug.types.LongerThan(10))
    assert nullable_type(12345678901) == "12345678901"
    assert nullable_type(None) == None
    with pytest.raises(ValueError):
        nullable_type(1)


def test_schema_type():
    """Test hug's complex schema types"""
    class User(hug.types.Schema):
        username = hug.types.text
        password = hug.types.Chain(hug.types.text, hug.types.LongerThan(10))
    user_one = User({"username": "brandon", "password": "password123"})
    user_two = User(user_one)
    with pytest.raises(ValueError):
        user_three = User({"username": "brandon", "password": "123"})
    user_three = User({"username": "brandon", "password": "123"}, force=True)
    with pytest.raises(AttributeError):
        del user_one.username
    assert "username" in User.__slots__
    assert "_username" in User.__slots__
    assert user_one._username == "brandon"
    assert user_two == user_one
    assert user_three._username == "brandon"
    assert user_one.username == "brandon"
    assert user_two.username == "brandon"
    assert user_three.username == "brandon"
    assert user_one.password == "password123"
    with pytest.raises(ValueError):
        user_one.password = "test"
    assert user_one.password == "password123"


def test_marshmallow_schema():
    """Test hug's marshmallow schema support"""
    class UserSchema(Schema):
        name = fields.Str()

    schema_type = hug.types.MarshmallowSchema(UserSchema())
    assert schema_type({"name": "test"}) == {"name": "test"}
    assert schema_type("""{"name": "test"}""") == {"name": "test"}
    assert schema_type.__doc__ == 'UserSchema'
    with pytest.raises(InvalidTypeData):
        schema_type({"name": 1})
