"""tests/test_types.py.

Tests the type validators included with hug

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
import json
import urllib
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import hug
import pytest
from hug.exceptions import InvalidTypeData
from marshmallow import Schema, ValidationError, fields
from marshmallow.decorators import validates_schema

api = hug.API(__name__)


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
    assert hug.types.DelimitedList[int](',')('1,2') == [1, 2]
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
    assert hug.types.boolean('1')
    assert hug.types.boolean('T')
    assert not hug.types.boolean('')
    assert hug.types.boolean('False')
    assert not hug.types.boolean(False)


def test_mapping():
    """Test to ensure the mapping type works as expected"""
    mapping_type = hug.types.mapping({'n': None, 'l': [], 's': set()})
    assert mapping_type('n') is None
    assert mapping_type('l') == []
    assert mapping_type('s') == set()
    assert 'n' in mapping_type.__doc__
    with pytest.raises(KeyError):
        mapping_type('bacon')


def test_smart_boolean():
    """Test to ensure that the smart boolean type works as expected"""
    assert hug.types.smart_boolean('true')
    assert hug.types.smart_boolean('t')
    assert hug.types.smart_boolean('1')
    assert hug.types.smart_boolean(1)
    assert not hug.types.smart_boolean('')
    assert not hug.types.smart_boolean('false')
    assert not hug.types.smart_boolean('f')
    assert not hug.types.smart_boolean('0')
    assert not hug.types.smart_boolean(0)
    assert hug.types.smart_boolean(True)
    assert not hug.types.smart_boolean(None)
    assert not hug.types.smart_boolean(False)
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
    int_dict = hug.types.InlineDictionary[int, int]()
    assert int_dict('1:2') == {1: 2}
    assert int_dict('1:2|3:4') == {1: 2, 3: 4}
    assert hug.types.inline_dictionary('1:2') == {'1': '2'}
    assert hug.types.inline_dictionary('1:2|3:4') == {'1': '2', '3': '4'}
    with pytest.raises(ValueError):
        hug.types.inline_dictionary('1')

    int_dict = hug.types.InlineDictionary[int]()
    assert int_dict('1:2') == {1: '2'}

    int_dict = hug.types.InlineDictionary[int, int, int]()
    assert int_dict('1:2') == {1: 2}



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
    assert multi_type('t')
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
    assert nullable_type(None) is None
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
        name = fields.Int()

    schema_type = hug.types.MarshmallowInputSchema(UserSchema())
    assert schema_type({"name": 23}, {}) == {"name": 23}
    assert schema_type("""{"name": 23}""", {}) == {"name": 23}
    assert schema_type.__doc__ == 'UserSchema'
    with pytest.raises(InvalidTypeData):
        schema_type({"name": "test"}, {})

    schema_type = hug.types.MarshmallowReturnSchema(UserSchema())
    assert schema_type({"name": 23}) == {"name": 23}
    assert schema_type.__doc__ == 'UserSchema'
    with pytest.raises(InvalidTypeData):
        schema_type({"name": "test"})


def test_create_type():
    """Test hug's new type creation decorator works as expected"""
    @hug.type(extend=hug.types.text, exception_handlers={TypeError: ValueError, LookupError: 'Hi!'},
              error_text='Invalid')
    def prefixed_string(value):
        if value == 'hi':
            raise TypeError('Repeat of prefix')
        elif value == 'bye':
            raise LookupError('Never say goodbye!')
        elif value == '1+1':
            raise ArithmeticError('Testing different error types')
        return 'hi-' + value

    assert prefixed_string('there') == 'hi-there'
    with pytest.raises(ValueError):
        prefixed_string([])
    with pytest.raises(ValueError):
        prefixed_string('hi')
    with pytest.raises(ValueError):
        prefixed_string('bye')

    @hug.type(extend=hug.types.text, exception_handlers={TypeError: ValueError})
    def prefixed_string(value):
        if value == '1+1':
            raise ArithmeticError('Testing different error types')
        return 'hi-' + value

    with pytest.raises(ArithmeticError):
        prefixed_string('1+1')

    @hug.type(extend=hug.types.text)
    def prefixed_string(value):
        return 'hi-' + value

    assert prefixed_string('there') == 'hi-there'

    @hug.type(extend=hug.types.one_of)
    def numbered(value):
        return int(value)

    assert numbered(['1', '2', '3'])('1') == 1


def test_marshmallow_custom_context():
    custom_context = dict(context='global', factory=0, delete=0, marshmallow=0)

    @hug.context_factory(apply_globally=True)
    def create_context(*args, **kwargs):
        custom_context['factory'] += 1
        return custom_context

    @hug.delete_context(apply_globally=True)
    def delete_context(context, *args, **kwargs):
        assert context == custom_context
        custom_context['delete'] += 1

    class MarshmallowContextSchema(Schema):
        name = fields.String()

        @validates_schema
        def check_context(self, data):
            assert self.context == custom_context
            self.context['marshmallow'] += 1

    @hug.get()
    def made_up_hello(test: MarshmallowContextSchema()):
        return 'hi'

    assert hug.test.get(api, '/made_up_hello', {'test': {'name': 'test'}}).data == 'hi'
    assert custom_context['factory'] == 1
    assert custom_context['delete'] == 1
    assert custom_context['marshmallow'] == 1


def test_extending_types_with_context_with_no_error_messages():
    custom_context = dict(context='global', the_only_right_number=42)

    @hug.context_factory()
    def create_context(*args, **kwargs):
        return custom_context

    @hug.delete_context()
    def delete_context(*args, **kwargs):
        pass

    @hug.type(chain=True, extend=hug.types.number)
    def check_if_positive(value):
        if value < 0:
            raise ValueError('Not positive')
        return value

    @hug.type(chain=True, extend=check_if_positive, accept_context=True)
    def check_if_near_the_right_number(value, context):
        the_only_right_number = context['the_only_right_number']
        if value not in [
            the_only_right_number - 1,
            the_only_right_number,
            the_only_right_number + 1,
        ]:
            raise ValueError('Not near the right number')
        return value

    @hug.type(chain=True, extend=check_if_near_the_right_number, accept_context=True)
    def check_if_the_only_right_number(value, context):
        if value != context['the_only_right_number']:
            raise ValueError('Not the right number')
        return value

    @hug.type(chain=False, extend=hug.types.number, accept_context=True)
    def check_if_string_has_right_value(value, context):
        if str(context['the_only_right_number']) not in value:
            raise ValueError('The value does not contain the only right number')
        return value

    @hug.type(chain=False, extend=hug.types.number)
    def simple_check(value):
        if value != 'simple':
            raise ValueError('This is not simple')
        return value

    @hug.get('/check_the_types')
    def check_the_types(
        first: check_if_positive,
        second: check_if_near_the_right_number,
        third: check_if_the_only_right_number,
        forth: check_if_string_has_right_value,
        fifth: simple_check,
    ):
        return 'hi'

    test_cases = [
        (
            (42, 42, 42, '42', 'simple',),
            (
                None,
                None,
                None,
                None,
                None,
            ),
        ),
        (
            (43, 43, 43, '42', 'simple',),
            (
                None,
                None,
                'Not the right number',
                None,
                None,
            ),
        ),
        (
            (40, 40, 40, '42', 'simple',),
            (
                None,
                'Not near the right number',
                'Not near the right number',
                None,
                None,
            ),
        ),
        (
            (-42, -42, -42, '53', 'not_simple',),
            (
                'Not positive',
                'Not positive',
                'Not positive',
                'The value does not contain the only right number',
                'This is not simple',
            ),
        ),
    ]

    for provided_values, expected_results in test_cases:
        response = hug.test.get(api, '/check_the_types', **{
            'first': provided_values[0],
            'second': provided_values[1],
            'third': provided_values[2],
            'forth': provided_values[3],
            'fifth': provided_values[4]
        })
        if response.data == 'hi':
            errors = (None, None, None, None, None)
        else:
            errors = []
            for key in ['first', 'second', 'third', 'forth', 'fifth']:
                if key in response.data['errors']:
                    errors.append(response.data['errors'][key])
                else:
                    errors.append(None)
            errors = tuple(errors)
        assert errors == expected_results


def test_extending_types_with_context_with_error_messages():
    custom_context = dict(context='global', the_only_right_number=42)

    @hug.context_factory()
    def create_context(*args, **kwargs):
        return custom_context

    @hug.delete_context()
    def delete_context(*args, **kwargs):
        pass

    @hug.type(chain=True, extend=hug.types.number, error_text='error 1')
    def check_if_positive(value):
        if value < 0:
            raise ValueError('Not positive')
        return value

    @hug.type(chain=True, extend=check_if_positive, accept_context=True, error_text='error 2')
    def check_if_near_the_right_number(value, context):
        the_only_right_number = context['the_only_right_number']
        if value not in [
            the_only_right_number - 1,
            the_only_right_number,
            the_only_right_number + 1,
        ]:
            raise ValueError('Not near the right number')
        return value

    @hug.type(chain=True, extend=check_if_near_the_right_number, accept_context=True, error_text='error 3')
    def check_if_the_only_right_number(value, context):
        if value != context['the_only_right_number']:
            raise ValueError('Not the right number')
        return value

    @hug.type(chain=False, extend=hug.types.number, accept_context=True, error_text='error 4')
    def check_if_string_has_right_value(value, context):
        if str(context['the_only_right_number']) not in value:
            raise ValueError('The value does not contain the only right number')
        return value

    @hug.type(chain=False, extend=hug.types.number, error_text='error 5')
    def simple_check(value):
        if value != 'simple':
            raise ValueError('This is not simple')
        return value

    @hug.get('/check_the_types')
    def check_the_types(
        first: check_if_positive,
        second: check_if_near_the_right_number,
        third: check_if_the_only_right_number,
        forth: check_if_string_has_right_value,
        fifth: simple_check,
    ):
        return 'hi'

    test_cases = [
        (
            (42, 42, 42, '42', 'simple',),
            (
                None,
                None,
                None,
                None,
                None,
            ),
        ),
        (
            (43, 43, 43, '42', 'simple',),
            (
                None,
                None,
                'error 3',
                None,
                None,
            ),
        ),
        (
            (40, 40, 40, '42', 'simple',),
            (
                None,
                'error 2',
                'error 3',
                None,
                None,
            ),
        ),
        (
            (-42, -42, -42, '53', 'not_simple',),
            (
                'error 1',
                'error 2',
                'error 3',
                'error 4',
                'error 5',
            ),
        ),
    ]

    for provided_values, expected_results in test_cases:
        response = hug.test.get(api, '/check_the_types', **{
            'first': provided_values[0],
            'second': provided_values[1],
            'third': provided_values[2],
            'forth': provided_values[3],
            'fifth': provided_values[4]
        })
        if response.data == 'hi':
            errors = (None, None, None, None, None)
        else:
            errors = []
            for key in ['first', 'second', 'third', 'forth', 'fifth']:
                if key in response.data['errors']:
                    errors.append(response.data['errors'][key])
                else:
                    errors.append(None)
            errors = tuple(errors)
        assert errors == expected_results


def test_extending_types_with_exception_in_function():
    custom_context = dict(context='global', the_only_right_number=42)

    class CustomStrException(Exception):
        pass

    class CustomFunctionException(Exception):
        pass

    class CustomNotRegisteredException(ValueError):

        def __init__(self):
            super().__init__('not registered exception')


    exception_handlers = {
        CustomFunctionException: lambda exception: ValueError('function exception'),
        CustomStrException: 'string exception',
    }

    @hug.context_factory()
    def create_context(*args, **kwargs):
        return custom_context

    @hug.delete_context()
    def delete_context(*args, **kwargs):
        pass

    @hug.type(chain=True, extend=hug.types.number, exception_handlers=exception_handlers)
    def check_simple_exception(value):
        if value < 0:
            raise CustomStrException()
        elif value == 0:
            raise CustomNotRegisteredException()
        else:
            raise CustomFunctionException()

    @hug.type(chain=True, extend=hug.types.number, exception_handlers=exception_handlers, accept_context=True)
    def check_context_exception(value, context):
        if value < 0:
            raise CustomStrException()
        elif value == 0:
            raise CustomNotRegisteredException()
        else:
            raise CustomFunctionException()

    @hug.type(chain=True, extend=hug.types.number, accept_context=True)
    def no_check(value, context):
        return value

    @hug.type(chain=True, extend=no_check, exception_handlers=exception_handlers, accept_context=True)
    def check_another_context_exception(value, context):
        if value < 0:
            raise CustomStrException()
        elif value == 0:
            raise CustomNotRegisteredException()
        else:
            raise CustomFunctionException()

    @hug.type(chain=False, exception_handlers=exception_handlers, accept_context=True)
    def check_simple_no_chain_exception(value, context):
        if value == '-1':
            raise CustomStrException()
        elif value == '0':
            raise CustomNotRegisteredException()
        else:
            raise CustomFunctionException()

    @hug.type(chain=False, exception_handlers=exception_handlers, accept_context=False)
    def check_simple_no_chain_no_context_exception(value):
        if value == '-1':
            raise CustomStrException()
        elif value == '0':
            raise CustomNotRegisteredException()
        else:
            raise CustomFunctionException()


    @hug.get('/raise_exception')
    def raise_exception(
        first: check_simple_exception,
        second: check_context_exception,
        third: check_another_context_exception,
        forth: check_simple_no_chain_exception,
        fifth: check_simple_no_chain_no_context_exception
    ):
        return {}

    response = hug.test.get(api, '/raise_exception', **{
        'first': 1,
        'second': 1,
        'third': 1,
        'forth': 1,
        'fifth': 1,
    })
    assert response.data['errors'] == {
        'forth': 'function exception',
        'third': 'function exception',
        'fifth': 'function exception',
        'second': 'function exception',
        'first': 'function exception'
    }
    response = hug.test.get(api, '/raise_exception', **{
        'first': -1,
        'second': -1,
        'third': -1,
        'forth': -1,
        'fifth': -1,
    })
    assert response.data['errors'] == {
        'forth': 'string exception',
        'third': 'string exception',
        'fifth': 'string exception',
        'second': 'string exception',
        'first': 'string exception'
    }
    response = hug.test.get(api, '/raise_exception', **{
        'first': 0,
        'second': 0,
        'third': 0,
        'forth': 0,
        'fifth': 0,
    })
    assert response.data['errors'] == {
        'second': 'not registered exception',
        'forth': 'not registered exception',
        'third': 'not registered exception',
        'fifth': 'not registered exception',
        'first': 'not registered exception'
    }


def test_validate_route_args_positive_case():

    class TestSchema(Schema):
        bar = fields.String()

    @hug.get('/hello', args={
        'foo': fields.Integer(),
        'return': TestSchema()
    })
    def hello(foo: int) -> dict:
        return {'bar': str(foo)}

    response = hug.test.get(api, '/hello', **{
        'foo': 5
    })
    assert response.data == {'bar': '5'}


def test_validate_route_args_negative_case():
    @hug.get('/hello', raise_on_invalid=True, args={
        'foo': fields.Integer()
    })
    def hello(foo: int):
        return str(foo)

    with pytest.raises(ValidationError):
        hug.test.get(api, '/hello', **{
            'foo': 'a'
        })

    class TestSchema(Schema):
        bar = fields.Integer()

    @hug.get('/foo', raise_on_invalid=True, args={
        'return': TestSchema()
    })
    def foo():
        return {'bar': 'a'}

    with pytest.raises(InvalidTypeData):
        hug.test.get(api, '/foo')
