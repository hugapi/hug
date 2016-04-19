"""tests/test_output_format.py.

Tests the output format handlers included with Hug

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
import os
from collections import namedtuple
from datetime import datetime
from decimal import Decimal
from io import BytesIO

import pytest

import hug

from .constants import BASE_DIRECTORY


def test_text():
    """Ensure that it's possible to output a Hug API method as text"""
    hug.output_format.text("Hello World!") == "Hello World!"
    hug.output_format.text(str(1)) == "1"


def test_html():
    """Ensure that it's possible to output a Hug API method as HTML"""
    hug.output_format.html("<html>Hello World!</html>") == "<html>Hello World!</html>"
    hug.output_format.html(str(1)) == "1"
    with open(os.path.join(BASE_DIRECTORY, 'README.md'), 'rb') as html_file:
        assert hasattr(hug.output_format.html(html_file), 'read')

    class FakeHTMLWithRender():
        def render(self):
            return 'test'

    assert hug.output_format.html(FakeHTMLWithRender()) == b'test'


def test_json():
    """Ensure that it's possible to output a Hug API method as JSON"""
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
    converted = hug.input_format.json(BytesIO(hug.output_format.json(data)))
    assert converted == {'name': 'name', 'value': 'value'}

    data = set((1, 2, 3, 3))
    assert hug.input_format.json(BytesIO(hug.output_format.json(data))) == [1, 2, 3]

    data = (number for number in range(1, 4))
    assert hug.input_format.json(BytesIO(hug.output_format.json(data))) == [1, 2, 3]

    data = [Decimal(1.5), Decimal("155.23"), Decimal("1234.25")]
    assert hug.input_format.json(BytesIO(hug.output_format.json(data))) == ["1.5", "155.23", "1234.25"]

    with open(os.path.join(BASE_DIRECTORY, 'README.md'), 'rb') as json_file:
        assert hasattr(hug.output_format.json(json_file), 'read')

    assert hug.input_format.json(BytesIO(hug.output_format.json(b'\x9c'))) == 'nA=='

    class MyCrazyObject(object):
        pass

    @hug.output_format.json_convert(MyCrazyObject)
    def convert(instance):
        return 'Like anyone could convert this'

    assert hug.input_format.json(BytesIO(hug.output_format.json(MyCrazyObject()))) == 'Like anyone could convert this'


def test_pretty_json():
    """Ensure that it's possible to output a Hug API method as prettified and indented JSON"""
    test_data = {'text': 'text'}
    assert hug.output_format.pretty_json(test_data).decode('utf8') == ('{\n'
                                                                       '    "text": "text"\n'
                                                                       '}')


def test_json_camelcase():
    """Ensure that it's possible to output a Hug API method as camelCased JSON"""
    test_data = {'under_score': {'values_can': 'Be Converted'}}
    output = hug.output_format.json_camelcase(test_data).decode('utf8')
    assert 'underScore' in output
    assert 'valuesCan' in output
    assert 'Be Converted' in output


def test_image():
    """Ensure that it's possible to output images with hug"""
    logo_path = os.path.join(BASE_DIRECTORY, 'artwork', 'logo.png')
    assert hasattr(hug.output_format.png_image(logo_path, hug.Response()), 'read')
    with open(logo_path, 'rb') as image_file:
        assert hasattr(hug.output_format.png_image(image_file, hug.Response()), 'read')

    assert hug.output_format.png_image('Not Existent', hug.Response()) is None

    class FakeImageWithSave():
        def save(self, to, format):
            to.write(b'test')
    assert hasattr(hug.output_format.png_image(FakeImageWithSave(), hug.Response()), 'read')

    class FakeImageWithRender():
        def render(self):
            return 'test'
    assert hug.output_format.svg_xml_image(FakeImageWithRender(), hug.Response()) == 'test'

    class FakeImageWithSaveNoFormat():
        def save(self, to):
            to.write(b'test')
    assert hasattr(hug.output_format.png_image(FakeImageWithSaveNoFormat(), hug.Response()), 'read')


def test_file():
    """Ensure that it's possible to easily output files"""
    class FakeResponse(object):
        pass

    logo_path = os.path.join(BASE_DIRECTORY, 'artwork', 'logo.png')
    fake_response = FakeResponse()
    assert hasattr(hug.output_format.file(logo_path, fake_response), 'read')
    assert fake_response.content_type == 'image/png'
    with open(logo_path, 'rb') as image_file:
        hasattr(hug.output_format.file(image_file, fake_response), 'read')

    assert not hasattr(hug.output_format.file('NON EXISTENT FILE', fake_response), 'read')


def test_video():
    """Ensure that it's possible to output videos with hug"""
    gif_path = os.path.join(BASE_DIRECTORY, 'artwork', 'example.gif')
    assert hasattr(hug.output_format.mp4_video(gif_path, hug.Response()), 'read')
    with open(gif_path, 'rb') as image_file:
        assert hasattr(hug.output_format.mp4_video(image_file, hug.Response()), 'read')

    assert hug.output_format.mp4_video('Not Existent', hug.Response()) is None

    class FakeVideoWithSave():
        def save(self, to, format):
            to.write(b'test')
    assert hasattr(hug.output_format.mp4_video(FakeVideoWithSave(), hug.Response()), 'read')

    class FakeVideoWithSave():
        def render(self):
            return 'test'
    assert hug.output_format.avi_video(FakeVideoWithSave(), hug.Response()) == 'test'


def test_on_valid():
    """Test to ensure formats that use on_valid content types gracefully handle error dictionaries"""
    error_dict = {'errors': {'so': 'many'}}
    expected = hug.output_format.json(error_dict)

    assert hug.output_format.mp4_video(error_dict, hug.Response()) == expected
    assert hug.output_format.png_image(error_dict, hug.Response()) == expected

    @hug.output_format.on_valid('image', hug.output_format.file)
    def my_output_format(data):
        raise ValueError('This should never be called')

    assert my_output_format(error_dict, hug.Response())


def test_on_content_type():
    """Ensure that it's possible to route the output type format by the requested content-type"""
    formatter = hug.output_format.on_content_type({'application/json': hug.output_format.json,
                                                   'text/plain': hug.output_format.text})

    class FakeRequest(object):
        content_type = 'application/json'

    request = FakeRequest()
    response = FakeRequest()
    converted = hug.input_format.json(formatter(BytesIO(hug.output_format.json({'name': 'name'})), request, response))
    assert converted == {'name': 'name'}

    request.content_type = 'text/plain'
    assert formatter('hi', request, response) == b'hi'

    with pytest.raises(hug.HTTPNotAcceptable):
        request.content_type = 'undefined; always'
        formatter('hi', request, response)


def test_accept():
    """Ensure that it's possible to route the output type format by the requests stated accept header"""
    formatter = hug.output_format.accept({'application/json': hug.output_format.json,
                                          'text/plain': hug.output_format.text})

    class FakeRequest(object):
        accept = 'application/json'

    request = FakeRequest()
    response = FakeRequest()
    converted = hug.input_format.json(formatter(BytesIO(hug.output_format.json({'name': 'name'})), request, response))
    assert converted == {'name': 'name'}

    request.accept = 'text/plain'
    assert formatter('hi', request, response) == b'hi'

    request.accept = 'application/json, text/plain; q=0.5'
    assert formatter('hi', request, response) == b'"hi"'

    request.accept = 'text/plain; q=0.5, application/json'
    assert formatter('hi', request, response) == b'"hi"'

    request.accept = 'application/json;q=0.4,text/plain; q=0.5'
    assert formatter('hi', request, response) == b'hi'

    request.accept = '*'
    assert formatter('hi', request, response) in [b'"hi"', b'hi']

    request.accept = 'undefined; always'
    with pytest.raises(hug.HTTPNotAcceptable):
        formatter('hi', request, response)


    formatter = hug.output_format.accept({'application/json': hug.output_format.json,
                                          'text/plain': hug.output_format.text}, hug.output_format.json)
    assert formatter('hi', request, response) == b'"hi"'


def test_suffix():
    """Ensure that it's possible to route the output type format by the suffix of the requested URL"""
    formatter = hug.output_format.suffix({'.js': hug.output_format.json, '.html': hug.output_format.text})

    class FakeRequest(object):
        path = 'endpoint.js'

    request = FakeRequest()
    response = FakeRequest()
    converted = hug.input_format.json(formatter(BytesIO(hug.output_format.json({'name': 'name'})), request, response))
    assert converted == {'name': 'name'}

    request.path = 'endpoint.html'
    assert formatter('hi', request, response) == b'hi'

    with pytest.raises(hug.HTTPNotAcceptable):
        request.path = 'undefined.always'
        formatter('hi', request, response)


def test_prefix():
    """Ensure that it's possible to route the output type format by the prefix of the requested URL"""
    formatter = hug.output_format.prefix({'js/': hug.output_format.json, 'html/': hug.output_format.text})

    class FakeRequest(object):
        path = 'js/endpoint'

    request = FakeRequest()
    response = FakeRequest()
    converted = hug.input_format.json(formatter(BytesIO(hug.output_format.json({'name': 'name'})), request, response))
    assert converted == {'name': 'name'}

    request.path = 'html/endpoint'
    assert formatter('hi', request, response) == b'hi'

    with pytest.raises(hug.HTTPNotAcceptable):
        request.path = 'undefined.always'
        formatter('hi', request, response)
