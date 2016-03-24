"""Example API using marshmallow fields as type annotations.


Requires marshmallow and dateutil.

    $ pip install marshmallow python-dateutil


To run the example:

    $ hug -f examples/marshmallow_example.py

Example requests using HTTPie:

    $ http :8000/dateadd value==1973-04-10 addend==63
    $ http :8000/dateadd value==2015-03-20 addend==525600 unit==minutes
"""
import datetime as dt

import hug
from marshmallow import fields
from marshmallow.validate import Range, OneOf


@hug.get('/dateadd', examples="value=1973-04-10&addend=63")
def dateadd(value: fields.DateTime(),
            addend: fields.Int(validate=Range(min=1)),
            unit: fields.Str(validate=OneOf(['minutes', 'days']))='days'):
    """Add a value to a date."""
    value = value or dt.datetime.utcnow()
    if unit == 'minutes':
        delta = dt.timedelta(minutes=addend)
    else:
        delta = dt.timedelta(days=addend)
    result = value + delta
    return {'result': result}
