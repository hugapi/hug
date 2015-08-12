"""tests/test_output_format.py.

Tests the output format handlers included with Hug

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
import pytest
import hug
from datetime import datetime


def test_text():
    '''Ensure that it's possible to output a Hug API method as text'''
    hug.output_format.text("Hello World!") == "Hello World!"
    hug.output_format.text(str(1)) == "1"


def test_json():
    '''Ensure that it's possible to output a Hug API method as JSON'''
    now = datetime.now()
    test_data = {'text': 'text', 'datetime': now, 'bytes': b'bytes'}
    output = hug.output_format.json(test_data).decode('utf8')
    assert 'text' in output
    assert 'bytes' in output
    assert now.isoformat() in output

    class NewObject(object):
        pass
    test_data['non_serializable'] = NewObject()
    with pytest.raises(TypeError):
        hug.output_format.json(test_data).decode('utf8')


def test_pretty_json():
    '''Ensure that it's possible to output a Hug API method as prettified and indented JSON'''
    test_data = {'text': 'text'}
    assert hug.output_format.pretty_json(test_data).decode('utf8') == ('{\n'
                                                                       '    "text": "text"\n'
                                                                       '}')


def test_json_camelcase():
    '''Ensure that it's possible to output a Hug API method as camelCased JSON'''
    test_data = {'under_score': {'values_can': 'Be Converted'}}
    output = hug.output_format.json_camelcase(test_data).decode('utf8')
    assert 'underScore' in output
    assert 'valuesCan' in output
    assert 'Be Converted' in output

