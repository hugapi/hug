"""hug/types.py

Defines hugs built-in supported types
"""
def number(value):
    """A whole number"""
    return int(value)


def multiple(value):
    """Multiple Values"""
    return value if isinstance(value, list) else [value]


def comma_separated_list(value):
    """Multiple values, separated by a comma"""
    return value.split(",")


def decimal(value):
    """A decimal number"""
    return float(value)


def text(value):
    """Basic text / string value"""
    return str(value)


def inline_dictionary(value):
    """A single line dictionary, where items are separted by commas and key:value are separated by a pipe"""
    return {key.strip(): value.strip() for key, value in (item.split(":") for item in value.split("|"))}


def one_of(values):
    """Ensures the value is within a set of acceptable values"""
    def matches(value):
        if not value in values:
            raise KeyError('Value one of acceptable values: ({0})'.format("|".join(values)))
        return value

    matches.__doc__ = 'One of the following values: ({0})'.format("|".join(values))
    return matches
