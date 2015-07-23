"""hug/types.py

Defines hugs built-in supported types
"""
def number(value):
    return int(value)


def list(value):
    return type(value) == list and value or [value]


def comma_separated_list(value):
    return value.split(",")


def decimal(value):
    return float(value)


def text(value):
    return str(value)
