"""
Slugs.

Additional slug outputs.

MIT license.

Copyright (c) 2014 - 2017 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
from __future__ import unicode_literals
import re
import unicodedata
from . import util

RE_TAGS = re.compile(r'</?[^>]*>', re.UNICODE)
RE_INVALID_SLUG_CHAR = re.compile(r'[^\w\- ]', re.UNICODE)
RE_SEP = re.compile(r' ', re.UNICODE)
RE_ASCII_LETTERS = re.compile(r'[A-Z]', re.UNICODE)

NO_CASED = 0
UNICODE_CASED = 1
CASED = 2


def uslugify(text, sep, cased=NO_CASED, percent_encode=False):
    """Unicode slugify (`utf-8`)."""

    # Normalize, Strip html tags, strip leading and trailing whitespace, and lower
    slug = RE_TAGS.sub('', unicodedata.normalize('NFC', text)).strip()

    if cased == NO_CASED:
        slug = slug.lower()
    elif cased == UNICODE_CASED:

        def lower(m):
            """Lowercase character."""
            return m.group(0).lower()

        slug = RE_ASCII_LETTERS.sub(lower, slug)

    # Remove non word characters, non spaces, and non dashes, and convert spaces to dashes.
    slug = RE_SEP.sub(sep, RE_INVALID_SLUG_CHAR.sub('', slug))

    return util.quote(slug.encode('utf-8')) if percent_encode else slug


def uslugify_encoded(text, sep):
    """Unicode slugify (percent encoded)."""

    return uslugify(text, sep, percent_encode=True)


def uslugify_cased(text, sep):
    """Unicode slugify cased (keep case) (`utf-8`)."""

    return uslugify(text, sep, cased=CASED)


def uslugify_cased_encoded(text, sep):
    """Unicode slugify cased (keep case) (percent encoded)."""

    return uslugify(text, sep, cased=CASED, percent_encode=True)


def gfm(text, sep):
    """Unicode slugify cased (cased Unicode only) (`utf-8`)."""

    return uslugify(text, sep, cased=UNICODE_CASED)


def gfm_encoded(text, sep):
    """Unicode slugify cased (cased Unicode only) (percent encoded)."""

    return uslugify(text, sep, cased=UNICODE_CASED, percent_encode=True)
