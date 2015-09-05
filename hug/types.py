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


def number(value):
    '''A whole number'''
    return int(value)


def multiple(value):
    '''Multiple Values'''
    return value if isinstance(value, list) else [value]
multiple.cli_behaviour = {'action': 'append'}


def comma_separated_list(value):
    '''Multiple values, separated by a comma'''
    return value.split(",")


def decimal(value):
    '''A decimal number'''
    return float(value)


def text(value):
    '''Basic text / string value'''
    return str(value)


def inline_dictionary(value):
    '''A single line dictionary, where items are separted by commas and key:value are separated by a pipe'''
    return {key.strip(): value.strip() for key, value in (item.split(":") for item in value.split("|"))}


def one_of(values):
    '''Ensures the value is within a set of acceptable values'''
    def matches(value):
        if not value in values:
            raise KeyError('Invalid value passed. The accepted values are: ({0})'.format("|".join(values)))
        return value

    matches.__doc__ = 'Accepts one of the following values: ({0})'.format("|".join(values))
    matches.cli_behaviour = {'choices': values}
    return matches
