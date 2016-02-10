"""hug/validate.py

Defines hugs built-in validation methods

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


def all(*validators):
    """Validation only succeeds if all passed in validators return no errors"""
    def validate_all(fields):
        for validator in validators:
            errors = validator(fields)
            if errors:
                return errors

    validate_all.__doc__ = " and ".join(validator.__doc__ for validator in validators)
    return validate_all


def any(*validators):
    """If any of the specified validators pass the validation succeeds"""
    def validate_any(fields):
        errors = {}
        for validator in validators:
            validation_errors = validator(fields)
            if not validation_errors:
                return
            errors.update(validation_errors)
        return errors

    validate_any.__doc__ = " or ".join(validator.__doc__ for validator in validators)
    return validate_any


def contains_one_of(*fields):
    """Enables ensuring that one of multiple optional fields is set"""
    message = 'Must contain any one of the following fields: {0}'.format(', '.join(fields))
    def check_contains(endpoint_fields):
        for field in fields:
            if field in endpoint_fields:
                return

        errors = {}
        for field in fields:
            errors[field] = 'one of these must have a value'
        return errors
    check_contains.__doc__ = message
    return check_contains
