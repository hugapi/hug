"""hug/output_format.py

Defines Hug's built-in output formatting methods

Copyright (C) 2016  Timothy Edmund Crosley

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
from __future__ import absolute_import

import base64
import mimetypes
import os
import re
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps
from io import BytesIO
from operator import itemgetter
from uuid import UUID

import falcon
from falcon import HTTP_NOT_FOUND

from hug import introspect
from hug.format import camelcase, content_type
from hug.json_module import json as json_converter

try:
    import numpy
except ImportError:
    numpy = False

IMAGE_TYPES = ('png', 'jpg', 'bmp', 'eps', 'gif', 'im', 'jpeg', 'msp', 'pcx', 'ppm', 'spider', 'tiff', 'webp', 'xbm',
               'cur', 'dcx', 'fli', 'flc', 'gbr', 'gd', 'ico', 'icns', 'imt', 'iptc', 'naa', 'mcidas', 'mpo', 'pcd',
               'psd', 'sgi', 'tga', 'wal', 'xpm', 'svg', 'svg+xml')

VIDEO_TYPES = (('flv', 'video/x-flv'), ('mp4', 'video/mp4'), ('m3u8', 'application/x-mpegURL'), ('ts', 'video/MP2T'),
               ('3gp', 'video/3gpp'), ('mov', 'video/quicktime'), ('avi', 'video/x-msvideo'), ('wmv', 'video/x-ms-wmv'))
RE_ACCEPT_QUALITY = re.compile("q=(?P<quality>[^;]+)")
json_converters = {}
stream = tempfile.NamedTemporaryFile if 'UWSGI_ORIGINAL_PROC_NAME' in os.environ else BytesIO


def _json_converter(item):
    if hasattr(item, '__native_types__'):
        return item.__native_types__()

    for kind, transformer in json_converters.items():
        if isinstance(item, kind):
            return transformer(item)

    if isinstance(item, (date, datetime)):
        return item.isoformat()
    elif isinstance(item, bytes):
        try:
            return item.decode('utf8')
        except UnicodeDecodeError:
            return base64.b64encode(item)
    elif hasattr(item, '__iter__'):
        return list(item)
    elif isinstance(item, (Decimal, UUID)):
        return str(item)
    elif isinstance(item, timedelta):
        return item.total_seconds()
    raise TypeError("Type not serializable")


def json_convert(*kinds):
    """Registers the wrapped method as a JSON converter for the provided types.

    NOTE: custom converters are always globally applied
    """
    def register_json_converter(function):
        for kind in kinds:
            json_converters[kind] = function
        return function
    return register_json_converter


if numpy:
    @json_convert(numpy.ndarray)
    def numpy_listable(item):
        return item.tolist()

    @json_convert(str, numpy.unicode_)
    def numpy_stringable(item):
        return str(item)

    @json_convert(numpy.bytes_)
    def numpy_byte_decodeable(item):
        return item.decode()

    @json_convert(numpy.bool_)
    def numpy_boolable(item):
        return bool(item)

    @json_convert(numpy.integer)
    def numpy_integerable(item):
        return int(item)

    @json_convert(float, numpy.floating)
    def numpy_floatable(item):
        return float(item)


@content_type('application/json; charset=utf-8')
def json(content, request=None, response=None, ensure_ascii=False, **kwargs):
    """JSON (Javascript Serialized Object Notation)"""
    if hasattr(content, 'read'):
        return content

    if isinstance(content, tuple) and getattr(content, '_fields', None):
        content = {field: getattr(content, field) for field in content._fields}
    return json_converter.dumps(content, default=_json_converter, ensure_ascii=ensure_ascii, **kwargs).encode('utf8')


def on_valid(valid_content_type, on_invalid=json):
    """Renders as the specified content type only if no errors are found in the provided data object"""
    invalid_kwargs = introspect.generate_accepted_kwargs(on_invalid, 'request', 'response')
    invalid_takes_response = introspect.takes_all_arguments(on_invalid, 'response')

    def wrapper(function):
        valid_kwargs = introspect.generate_accepted_kwargs(function, 'request', 'response')
        valid_takes_response = introspect.takes_all_arguments(function, 'response')

        @content_type(valid_content_type)
        @wraps(function)
        def output_content(content, response, **kwargs):
            if type(content) == dict and 'errors' in content:
                response.content_type = on_invalid.content_type
                if invalid_takes_response:
                    kwargs['response'] = response
                return on_invalid(content, **invalid_kwargs(kwargs))

            if valid_takes_response:
                kwargs['response'] = response
            return function(content, **valid_kwargs(kwargs))
        return output_content
    return wrapper


@content_type('text/plain; charset=utf-8')
def text(content, **kwargs):
    """Free form UTF-8 text"""
    if hasattr(content, 'read'):
        return content

    return str(content).encode('utf8')


@content_type('text/html; charset=utf-8')
def html(content, **kwargs):
    """HTML (Hypertext Markup Language)"""
    if hasattr(content, 'read'):
        return content
    elif hasattr(content, 'render'):
        return content.render().encode('utf8')

    return str(content).encode('utf8')


def _camelcase(content):
    if isinstance(content, dict):
        new_dictionary = {}
        for key, value in content.items():
            if isinstance(key, str):
                key = camelcase(key)
            new_dictionary[key] = _camelcase(value)
        return new_dictionary
    elif isinstance(content, list):
        new_list = []
        for element in content:
            new_list.append(_camelcase(element))
        return new_list
    else:
        return content


@content_type('application/json; charset=utf-8')
def json_camelcase(content, **kwargs):
    """JSON (Javascript Serialized Object Notation) with all keys camelCased"""
    return json(_camelcase(content), **kwargs)


@content_type('application/json; charset=utf-8')
def pretty_json(content, **kwargs):
    """JSON (Javascript Serialized Object Notion) pretty printed and indented"""
    return json(content, indent=4, separators=(',', ': '), **kwargs)


def image(image_format, doc=None):
    """Dynamically creates an image type handler for the specified image type"""
    @on_valid('image/{0}'.format(image_format))
    def image_handler(data, **kwargs):
        if hasattr(data, 'read'):
            return data
        elif hasattr(data, 'save'):
            output = stream()
            if introspect.takes_all_arguments(data.save, 'format') or introspect.takes_kwargs(data.save):
                data.save(output, format=image_format.upper())
            else:
                data.save(output)
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
    """Dynamically creates a video type handler for the specified video type"""
    @on_valid(video_mime)
    def video_handler(data, **kwargs):
        if hasattr(data, 'read'):
            return data
        elif hasattr(data, 'save'):
            output = stream()
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


@on_valid('file/dynamic')
def file(data, response, **kwargs):
    """A dynamically retrieved file"""
    if not data:
        response.content_type = 'text/plain'
        return ''

    if hasattr(data, 'read'):
        name, data = getattr(data, 'name', ''), data
    elif os.path.isfile(data):
        name, data = data, open(data, 'rb')
    else:
        response.content_type = 'text/plain'
        response.status = HTTP_NOT_FOUND
        return 'File not found!'

    response.content_type = mimetypes.guess_type(name, None)[0] or 'application/octet-stream'
    return data


def on_content_type(handlers, default=None, error='The requested content type does not match any of those allowed'):
    """Returns a content in a different format based on the clients provided content type,
       should pass in a dict with the following format:

            {'[content-type]': action,
             ...
            }
    """
    def output_type(data, request, response):
        handler = handlers.get(request.content_type.split(';')[0], default)
        if not handler:
            raise falcon.HTTPNotAcceptable(error)

        response.content_type = handler.content_type
        return handler(data, request=request, response=response)
    output_type.__doc__ = 'Supports any of the following formats: {0}'.format(', '.join(
        function.__doc__ or function.__name__ for function in handlers.values()))
    output_type.content_type = ', '.join(handlers.keys())
    return output_type


def accept_quality(accept, default=1):
    """Separates out the quality score from the accepted content_type"""
    quality = default
    if accept and ";" in accept:
        accept, rest = accept.split(";", 1)
        accept_quality = RE_ACCEPT_QUALITY.search(rest)
        if accept_quality:
            quality = float(accept_quality.groupdict().get('quality', quality).strip())

    return (quality, accept.strip())


def accept(handlers, default=None, error='The requested content type does not match any of those allowed'):
    """Returns a content in a different format based on the clients defined accepted content type,
       should pass in a dict with the following format:

            {'[content-type]': action,
             ...
            }
    """
    def output_type(data, request, response):
        accept = request.accept
        if accept in ('', '*', '/'):
            handler = default or handlers and next(iter(handlers.values()))
        else:
            handler = default
            accepted = [accept_quality(accept_type) for accept_type in accept.split(',')]
            accepted.sort(key=itemgetter(0))
            for quality, accepted_content_type in reversed(accepted):
                if accepted_content_type in handlers:
                    handler = handlers[accepted_content_type]
                    break

        if not handler:
            raise falcon.HTTPNotAcceptable(error)

        response.content_type = handler.content_type
        return handler(data, request=request, response=response)
    output_type.__doc__ = 'Supports any of the following formats: {0}'.format(', '.join(function.__doc__ for function in
                                                                                        handlers.values()))
    output_type.content_type = ', '.join(handlers.keys())
    return output_type


def suffix(handlers, default=None, error='The requested suffix does not match any of those allowed'):
    """Returns a content in a different format based on the suffix placed at the end of the URL route
       should pass in a dict with the following format:

            {'[suffix]': action,
             ...
            }
    """
    def output_type(data, request, response):
        path = request.path
        handler = default
        for suffix_test, suffix_handler in handlers.items():
            if path.endswith(suffix_test):
                handler = suffix_handler
                break

        if not handler:
            raise falcon.HTTPNotAcceptable(error)

        response.content_type = handler.content_type
        return handler(data, request=request, response=response)
    output_type.__doc__ = 'Supports any of the following formats: {0}'.format(', '.join(function.__doc__ for function in
                                                                                        handlers.values()))
    output_type.content_type = ', '.join(handlers.keys())
    return output_type


def prefix(handlers, default=None, error='The requested prefix does not match any of those allowed'):
    """Returns a content in a different format based on the prefix placed at the end of the URL route
       should pass in a dict with the following format:

            {'[prefix]': action,
             ...
            }
    """
    def output_type(data, request, response):
        path = request.path
        handler = default
        for prefix_test, prefix_handler in handlers.items():
            if path.startswith(prefix_test):
                handler = prefix_handler
                break

        if not handler:
            raise falcon.HTTPNotAcceptable(error)

        response.content_type = handler.content_type
        return handler(data, request=request, response=response)
    output_type.__doc__ = 'Supports any of the following formats: {0}'.format(', '.join(function.__doc__ for function in
                                                                                        handlers.values()))
    output_type.content_type = ', '.join(handlers.keys())
    return output_type
