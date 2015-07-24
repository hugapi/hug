"""hug/types.py

Defines hugs built-in supported types
"""
def number(value):
    """A whole number"""
    return int(value)


def list(value):
    """Multiple Values"""
    return type(value) == list and value or [value]


def comma_separated_list(value):
    """Multiple values, separated by a comma"""
    return value.split(",")


def decimal(value):
    """A decimal number"""
    return float(value)


def text(value):
    """Basic text / string value"""
    return str(value)
