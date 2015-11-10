"""hug/output_format.py

Defines Hug's built-in output formatting methods

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
import json as json_converter
import os
from datetime import date, datetime
from io import BytesIO

from hug.format import camelcase, content_type

IMAGE_TYPES = ('png', 'jpg', 'bmp', 'eps', 'gif', 'im', 'jpeg', 'msp', 'pcx', 'ppm', 'spider', 'tiff', 'webp', 'xbm',
               'cur', 'dcx', 'fli', 'flc', 'gbr', 'gd', 'ico', 'icns', 'imt', 'iptc', 'naa', 'mcidas', 'mpo', 'pcd',
               'psd', 'sgi', 'tga', 'wal', 'xpm', 'svg', 'svg+xml')

VIDEO_TYPES = (('flv', 'video/x-flv'), ('mp4', 'video/mp4'), ('m3u8', 'application/x-mpegURL'), ('ts', 'video/MP2T'),
               ('3gp', 'video/3gpp'), ('mov', 'video/quicktime'), ('avi', 'video/x-msvideo'), ('wmv', 'video/x-ms-wmv'))

def _json_converter(item):
    if isinstance(item, (date, datetime)):
        return item.isoformat()
    elif isinstance(item, bytes):
        return item.decode('utf8')
    elif isinstance(item, set):
        return list(item)
    elif getattr(item, '__native_types__', None):
        return item.__native_types__()
    raise TypeError("Type not serializable")


@content_type('application/json')
def json(content, **kwargs):
    '''JSON (Javascript Serialized Object Notation)'''
    if isinstance(content, tuple) and getattr(content, '_fields', None):
        content = {field: getattr(content, field) for field in content._fields}
    return json_converter.dumps(content, default=_json_converter, **kwargs).encode('utf8')


@content_type('text/plain')
def text(content):
    '''Free form UTF8 text'''
    return str(content).encode('utf8')


@content_type('text/html')
def html(content):
    '''HTML (Hypertext Markup Language)'''
    return str(content).encode('utf8')


def _camelcase(dictionary):
    if not isinstance(dictionary, dict):
        return dictionary

    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(key, str):
            key = camelcase(key)
        new_dictionary[key] = _camelcase(value)
    return new_dictionary


@content_type('application/json')
def json_camelcase(content):
    '''JSON (Javascript Serialized Object Notation) with all keys camelCased'''
    return json(_camelcase(content))


@content_type('application/json')
def pretty_json(content):
    '''JSON (Javascript Serialized Object Notion) pretty printed and indented'''
    return json(content, indent=4, separators=(',', ': '))


def image(image_format, doc=None):
    '''Dynamically creates an image type handler for the specified image type'''
    @content_type('image/{0}'.format(image_format))
    def image_handler(data):
        if hasattr(data, 'read'):
            return data
        elif hasattr(data, 'save'):
            output = BytesIO()
            data.save(output, format=image_format.upper())
            output.seek(0)
            return output
        elif hasattr(data, 'render'):
            return data.render()
        elif os.path.isfile(data):
            return open(data, 'rb')

    image_handler.__doc__ = doc or "{0} formatted image".format(image_format)
    return image_handler


for image_type in IMAGE_TYPES:
    globals()['{0}_image'.format(image_type.replace("+", "_"))] = image(image_type)


def video(video_type, video_mime, doc=None):
    '''Dynamically creates a video type handler for the specified video type'''
    @content_type(video_mime)
    def video_handler(data):
        if hasattr(data, 'read'):
            return data
        elif hasattr(data, 'save'):
            output = BytesIO()
            data.save(output, format=video_type.upper())
            output.seek(0)
            return output
        elif hasattr(data, 'render'):
            return data.render()
        elif os.path.isfile(data):
            return open(data, 'rb')

    video_handler.__doc__ = doc or "{0} formatted video".format(video_type)
    return video_handler


for (video_type, video_mime) in VIDEO_TYPES:
    globals()['{0}_video'.format(video_type)] = video(video_type, video_mime)
