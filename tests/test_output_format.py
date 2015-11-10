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
from collections import namedtuple
from datetime import datetime

import pytest

import hug


def test_text():
    '''Ensure that it's possible to output a Hug API method as text'''
    hug.output_format.text("Hello World!") == "Hello World!"
    hug.output_format.text(str(1)) == "1"


def test_html():
    '''Ensure that it's possible to output a Hug API method as HTML'''
    hug.output_format.html("<html>Hello World!</html>") == "<html>Hello World!</html>"
    hug.output_format.html(str(1)) == "1"


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

    class NamedTupleObject(namedtuple('BaseTuple', ('name', 'value'))):
        pass
    data = NamedTupleObject('name', 'value')
    converted = hug.input_format.json(hug.output_format.json(data).decode('utf8'))
    assert converted == {'name': 'name', 'value': 'value'}

    data = set((1, 2, 3, 3))
    assert hug.input_format.json(hug.output_format.json(data).decode('utf8')) == [1, 2, 3]


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


def test_image():
    '''Ensure that it's possible to output images with hug'''
    hasattr(hug.output_format.png_image('logo.png'), 'read')
    with open('logo.png', 'rb') as image_file:
        hasattr(hug.output_format.png_image(image_file), 'read')

    assert hug.output_format.png_image('Not Existent') == None

    class FakeImageWithSave():
        def save(self, to, format):
            to.write(b'test')
    hasattr(hug.output_format.png_image(FakeImageWithSave()), 'read')

    class FakeImageWithSave():
        def render(self):
            return 'test'
    assert hug.output_format.svg_xml_image(FakeImageWithSave()) == 'test'


def test_video():
    '''Ensure that it's possible to output videos with hug'''
    hasattr(hug.output_format.mp4_video('example.gif'), 'read')
    with open('example.gif', 'rb') as image_file:
        hasattr(hug.output_format.mp4_video(image_file), 'read')

    assert hug.output_format.mp4_video('Not Existent') == None

    class FakeVideoWithSave():
        def save(self, to, format):
            to.write(b'test')
    hasattr(hug.output_format.mp4_video(FakeVideoWithSave()), 'read')

    class FakeVideoWithSave():
        def render(self):
            return 'test'
    assert hug.output_format.avi_video(FakeVideoWithSave()) == 'test'
