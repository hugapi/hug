"""hug/transform.py

Defines Hug's built-in output transforming functions

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


def content_type(transformers, default=None):
    """Returns a different transformer depending on the content type passed in.
       If none match and no default is given no transformation takes place.

       should pass in a dict with the following format:

            {'[content-type]': transformation_action,
             ...
            }
    """
    def transform(data, request):
        transformer = transformers.get(request.content_type.split(';')[0], default)
        if not transformer:
            return data

        return transformer(data)
    return transform


def suffix(transformers, default=None):
    """Returns a different transformer depending on the suffix at the end of the requested URL.
       If none match and no default is given no transformation takes place.

       should pass in a dict with the following format:

            {'[suffix]': transformation_action,
             ...
            }
    """
    def transform(data, request):
        path = request.path
        transformer = default
        for suffix_test, suffix_transformer in transformers.items():
            if path.endswith(suffix_test):
                transformer = suffix_transformer
                break

        return transformer(data) if transformer else data
    return transform


def prefix(transformers, default=None):
    """Returns a different transformer depending on the prefix at the end of the requested URL.
       If none match and no default is given no transformation takes place.

       should pass in a dict with the following format:

            {'[prefix]': transformation_action,
             ...
            }
    """
    def transform(data, request):
        path = request.path
        transformer = default
        for prefix_test, prefix_transformer in transformers.items():
            if path.startswith(prefix_test):
                transformer = prefix_transformer
                break

        return transformer(data) if transformer else data
    return transform


def all(*transformers):
    """Returns the results of applying all passed in transformers to data

       should pass in list of transformers

            [transformer_1, transformer_2...]
    """
    def transform(data):
        for transformer in transformers:
            data = transformer(data)

        return data
    return transform
