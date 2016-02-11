"""hug/types.py

Defines hugs built-in supported types / validators

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
from decimal import Decimal
from json import loads as load_json
from abc import ABCMeta, abstractmethod

class constraint(object):
    __metaclass__ = ABCMeta
    
    @abstractmethod
    def validate(self, value):
        pass

    def __call__(self, value):
        return self.validate(value)
    

class accept(constraint):
    def __init__(self, formatter, doc=None, error_text=None, cli_behaviour=None, exception_handlers=None):
        self.formatter = formatter
        self.__doc__ = doc or self.formatter.__doc__
        self.error_text = error_text
        self.exception_handlers = exception_handlers or {}

        new_cli_behaviour = getattr(self.formatter, 'cli_behaviour', {})
        if cli_behaviour:
            new_cli_behaviour.update(cli_behaviour)

        if new_cli_behaviour:
            self.cli_behaviour = new_cli_behaviour

    def validate(self, value):
        if self.exception_handlers or self.error_text:
            try:
                return self.formatter(value)
            except Exception as exception:
                for take_exception, rewrite in self.exception_handlers.items():
                    if isinstance(exception, take_exception):
                        if isinstance(rewrite, str):
                            raise ValueError(rewrite)
                        else:
                            raise rewrite(value)
                if self.error_text:
                    raise ValueError(self.error_text)
                raise exception
        else:
            return self.formatter(value)

number = accept(int, 'A whole number', 'Invalid whole number provided')
float_number = accept(float, 'A float number', 'Invalid float number provided')
decimal = accept(Decimal, 'A decimal number', 'Invalid decimal number provided')
text = accept(str, 'Basic text / string value', 'Invalid text value provided')
boolean = accept(bool, 'Providing any value will set this to true',
                 'Invalid boolean value provided', cli_behaviour={'action': 'store_true'})

class list_constraint(constraint):
    '''Multiple Values'''
    cli_behaviour = {'action': 'append', 'type':text}
    def validate(self, value):
        return value if isinstance(value, list) else [value]

multiple = list_constraint()
        
class delimited_list(constraint):
    def __init__(self, using=","):
        self.using = using
        self.__doc__ = '''Multiple values, separated by "{0}"'''.format(self.using)

    def validate(self, value):
        return value if type(value) in (list, tuple) else value.split(self.using)

comma_separated_list = delimited_list(using=",")

class boolean_constraint(constraint):
    '''Accepts a true or false value'''
    cli_behaviour = {'action': 'store_true'}

    def validate(self, value):
        if type(value) == bool or value in (None, 1, 0):
            return bool(value)

        value = value.lower()
        if value in ('true', 't', '1'):
            return True
        elif value in ('false', 'f', '0', ''):
            return False

        raise KeyError('Invalid value passed in for true/false field')

smart_boolean = boolean_constraint()

class dictionary_constraint(constraint):
    '''A single line dictionary, where items are separted by commas and key:value are separated by a pipe'''
    def validate(self, value):
        return {key.strip(): value.strip() for key, value in (item.split(":") for item in value.split("|"))}

inline_dictionary = dictionary_constraint()

class one_of(constraint):
    def __init__(self, values):
        self.values = values
        self.__doc__ = 'Accepts one of the following values: ({0})'.format("|".join(values))
        self.cli_behaviour = {'choices': values}

    def validate(self, value):
        if not value in self.values:
            raise KeyError('Invalid value passed. The accepted values are: ({0})'.format("|".join(self.values)))
        return value

class mapping(constraint):
    '''Ensures the value is one of an acceptable set of values mapping those values to a Python equivelent'''
    def __init__(self, value_map):
        self.value_map = value_map
        self.values = value_map.keys()
        self.__doc__ = 'Accepts one of the following values: ({0})'.format("|".join(self.values))
        self.cli_behaviour = {'choices': self.values}

    def validate(self, value):
        if not value in self.values:
            raise KeyError('Invalid value passed. The accepted values are: ({0})'.format("|".join(self.values)))
        return self.value_map[value]

class json_constraint(constraint):
    '''Accepts a JSON formatted data structure'''
    def validate(self, value):
        if type(value) in (str, bytes):
            try:
                return load_json(value)
            except Exception:
                raise ValueError('Incorrectly formatted JSON provided')
        else:
            return value

json = json_constraint()

class multi(constraint):
    '''Enables accepting one of multiple type methods'''
    def __init__(self, *types):
       self.types = types
       type_strings = (type_method.__doc__ for type_method in types)
       self.__doc__ = 'Accepts any of the following value types:{0}\n'.format('\n  - '.join(type_strings))

    def validate(self, value):
        for type_method in self.types:
            try:
                return type_method(value)
            except:
                pass
        raise ValueError(self.__doc__)

class in_range(constraint):
    def __init__(self, lower, upper, convert=number):
        self.lower = lower
        self.upper = upper
        self.convert = convert
        self.__doc__ = ("{0} that is greater or equal to {1} and less than {2}".format(
                        convert.__doc__, lower, upper))

    def validate(self, value):
        value = self.convert(value)
        if value < self.lower:
            raise ValueError("'{0}' is less than the lower limit {1}".format(value, self.lower))
        if value >= self.upper:
            raise ValueError("'{0}' reaches the limit of {1}".format(value, self.upper))
        return value

class less_than(constraint):
    def __init__(self, limit, convert=number):
        self.limit = limit
        self.convert = convert
        self.__doc__ = "{0} that is less than {1}".format(convert.__doc__, limit)

    def validate(self, value):
        value = self.convert(value)
        if not value < self.limit:
            raise ValueError("'{0}' must be less than {1}".format(value, self.limit))
        return value

class greater_than(constraint):
    def __init__(self, minimum, convert=number):
        self.minimum = minimum
        self.convert = convert
        self.__doc__ = "{0} that is greater than {1}".format(convert.__doc__, minimum)

    def validate(self, value):
        value = self.convert(value)
        if not value > self.minimum:
            raise ValueError("'{0}' must be greater than {1}".format(value, self.minimum))
        return value

class length(constraint):
    def __init__(self, lower, upper, convert=text):
        self.lower = lower
        self.upper = upper
        self.convert = convert
        self.__doc__ = ("{0} that has a length longer or equal to {1} and less then {2}".format(
                        convert.__doc__, lower, upper))

    def validate(self, value):
        value = self.convert(value)
        length = len(value)
        if length < self.lower:
            raise ValueError("'{0}' is shorter than the lower limit of {1}".format(value, self.lower))
        if length >= self.upper:
            raise ValueError("'{0}' is longer then the allowed limit of {1}".format(value, self.upper))
        return value

class shorter_than(constraint):
    """Accepts a text value shorter than the specified length limit"""
    def __init__(self, limit, convert=text):
        self.limit = limit
        self.convert = convert
        self.__doc__ = "{0} with a length of no more than {1}".format(convert.__doc__, limit)

    def validate(self, value):
        value = self.convert(value)
        length = len(value)
        if not length < self.limit:
            raise ValueError("'{0}' is longer then the allowed limit of {1}".format(value, self.limit))
        return value

class longer_than(constraint):
    def __init__(self, limit, convert=text):
        self.limit = limit
        self.convert = convert
        self.__doc__ = "{0} with a length longer than {1}".format(convert.__doc__, limit)

    def validate(self, value):
        value = self.convert(value)
        length = len(value)
        if not length > self.limit:
            raise ValueError("'{0}' must be longer than {1}".format(value, self.limit))
        return value

class cut_off(constraint):
    """Cuts off the provided value at the specified index"""
    def __init__(self, limit, convert=text):
        self.limit = limit
        self.convert = convert
        self.__doc__ = "'{0}' with anything over the length of {1} being ignored".format(convert.__doc__, limit)

    def validate(self, value):
        return self.convert(value)[:self.limit]
