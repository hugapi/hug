"""
General utilities.

MIT license.

Copyright (c) 2017 Isaac Muse <isaacmuse@gmail.com>
"""
from __future__ import unicode_literals
from markdown.inlinepatterns import InlineProcessor, util
from collections import namedtuple
import sys
import copy
import re

PY3 = sys.version_info >= (3, 0)
PY34 = sys.version_info >= (3, 4)

if PY3:
    ustr = str  # noqa
    uchr = chr  # noqa
    from urllib.request import pathname2url, url2pathname  # noqa
    from urllib.parse import urlparse, urlunparse, quote  # noqa
    from html.parser import HTMLParser  # noqa
    if PY34:
        import html  # noqa
        html_unescape = html.unescape  # noqa
    else:  # pragma: no cover
        html_unescape = HTMLParser().unescape  # noqa
else:
    ustr = unicode  # noqa
    uchr = unichr  # noqa
    from urllib import pathname2url, url2pathname, quote  # noqa
    from urlparse import urlparse, urlunparse  # noqa
    from HTMLParser import HTMLParser  # noqa
    html_unescape = HTMLParser().unescape  # noqa

RE_WIN_DRIVE_LETTER = re.compile(r"^[A-Za-z]$")
RE_WIN_DRIVE_PATH = re.compile(r"^[A-Za-z]:(?:\\.*)?$")
RE_URL = re.compile('(http|ftp)s?|data|mailto|tel|news')
IS_NARROW = sys.maxunicode == 0xFFFF
RE_WIN_DEFAULT_PROTOCOL = re.compile(r"^///[A-Za-z]:(?:/.*)?$")

if sys.platform.startswith('win'):
    _PLATFORM = "windows"
elif sys.platform == "darwin":  # pragma: no cover
    _PLATFORM = "osx"
else:
    _PLATFORM = "linux"


def is_win():  # pragma: no cover
    """Is Windows."""

    return _PLATFORM == "windows"


def is_linux():  # pragma: no cover
    """Is Linux."""

    return _PLATFORM == "linux"


def is_mac():  # pragma: no cover
    """Is macOS."""

    return _PLATFORM == "osx"


def url2path(path):
    """Path to URL."""

    return url2pathname(path)


def path2url(url):
    """URL to path."""

    path = pathname2url(url)
    # If on windows, replace the notation to use a default protocol `///` with nothing.
    if is_win() and RE_WIN_DEFAULT_PROTOCOL.match(path):
        path = path.replace('///', '', 1)
    return path


if IS_NARROW:
    def get_code_points(s):
        """Get the Unicode code points."""

        pt = []

        def is_full_point(p, point):
            """
            Check if we have a full code point.

            Surrogates are stored in point.
            """
            v = ord(p)
            if 0xD800 <= v <= 0xDBFF:
                del point[:]
                point.append(p)
                return False
            if point and 0xDC00 <= v <= 0xDFFF:
                point.append(p)
                return True
            del point[:]
            return True

        return [(''.join(pt) if pt else c) for c in s if is_full_point(c, pt)]

    def get_ord(c):
        """Get Unicode ord."""

        if len(c) == 2:
            high, low = [ord(p) for p in c]
            ordinal = (high - 0xD800) * 0x400 + low - 0xDC00 + 0x10000
        else:
            ordinal = ord(c)

        return ordinal

    def get_char(value):
        """Get the Unicode char."""
        if value > 0xFFFF:
            c = ''.join(
                [
                    uchr(int((value - 0x10000) / (0x400)) + 0xD800),
                    uchr((value - 0x10000) % 0x400 + 0xDC00)
                ]
            )
        else:
            c = uchr(value)
        return c

else:
    def get_code_points(s):
        """Get the Unicode code points."""

        return [c for c in s]

    def get_ord(c):
        """Get Unicode ord."""

        return ord(c)

    def get_char(value):
        """Get the Unicode char."""

        return uchr(value)


def escape_chars(md, echrs):
    """
    Add chars to the escape list.

    Don't just append as it modifies the global list permanently.
    Make a copy and extend **that** copy so that only this Markdown
    instance gets modified.
    """

    escaped = copy.copy(md.ESCAPED_CHARS)
    for ec in echrs:
        if ec not in escaped:
            escaped.append(ec)
    md.ESCAPED_CHARS = escaped


def parse_url(url):
    """
    Parse the URL.

    Try to determine if the following is a file path or
    (as we will call anything else) a URL.

    We return it slightly modified and combine the path parts.

    We also assume if we see something like c:/ it is a Windows path.
    We don't bother checking if this **is** a Windows system, but
    'nix users really shouldn't be creating weird names like c: for their folder.
    """

    is_url = False
    is_absolute = False
    scheme, netloc, path, params, query, fragment = urlparse(html_unescape(url))

    if RE_URL.match(scheme):
        # Clearly a URL
        is_url = True
    elif scheme == '' and netloc == '' and path == '':
        # Maybe just a URL fragment
        is_url = True
    elif scheme == 'file' and (RE_WIN_DRIVE_PATH.match(netloc)):
        # file://c:/path or file://c:\path
        path = '/' + (netloc + path).replace('\\', '/')
        netloc = ''
        is_absolute = True
    elif scheme == 'file' and netloc.startswith('\\'):
        # file://\c:\path or file://\\path
        path = (netloc + path).replace('\\', '/')
        netloc = ''
        is_absolute = True
    elif scheme == 'file':
        # file:///path
        is_absolute = True
    elif RE_WIN_DRIVE_LETTER.match(scheme):
        # c:/path
        path = '/%s:%s' % (scheme, path.replace('\\', '/'))
        scheme = 'file'
        netloc = ''
        is_absolute = True
    elif scheme == '' and netloc != '' and url.startswith('//'):
        # //file/path
        path = '//' + netloc + path
        scheme = 'file'
        netloc = ''
        is_absolute = True
    elif scheme != '' and netloc != '':
        # A non-file path or strange URL
        is_url = True
    elif path.startswith(('/', '\\')):
        # /root path
        is_absolute = True

    return (scheme, netloc, path, params, query, fragment, is_url, is_absolute)


class PatSeqItem(namedtuple('PatSeqItem', ['pattern', 'builder', 'tags'])):
    """Pattern sequence item item."""


class PatternSequenceProcessor(InlineProcessor):
    """Processor for handling complex nested patterns such as strong and em matches."""

    PATTERNS = []

    def build_single(self, m, tag, idx):
        """Return single tag."""
        el1 = util.etree.Element(tag)
        text = m.group(2)
        self.parse_sub_patterns(text, el1, None, idx)
        return el1

    def build_double(self, m, tags, idx):
        """Return double tag."""

        tag1, tag2 = tags.split(",")
        el1 = util.etree.Element(tag1)
        el2 = util.etree.Element(tag2)
        text = m.group(2)
        self.parse_sub_patterns(text, el2, None, idx)
        el1.append(el2)
        if len(m.groups()) == 3:
            text = m.group(3)
            self.parse_sub_patterns(text, el1, el2, idx)
        return el1

    def build_double2(self, m, tags, idx):
        """Return double tags (variant 2): `<strong>text <em>text</em></strong>`."""

        tag1, tag2 = tags.split(",")
        el1 = util.etree.Element(tag1)
        el2 = util.etree.Element(tag2)
        text = m.group(2)
        self.parse_sub_patterns(text, el1, None, idx)
        text = m.group(3)
        el1.append(el2)
        self.parse_sub_patterns(text, el2, None, idx)
        return el1

    def parse_sub_patterns(self, data, parent, last, idx):
        """
        Parses sub patterns.

        `data` (`str`):
            text to evaluate.

        `parent` (`etree.Element`):
            Parent to attach text and sub elements to.

        `last` (`etree.Element`):
            Last appended child to parent. Can also be None if parent has no children.

        `idx` (`int`):
            Current pattern index that was used to evaluate the parent.

        """

        offset = 0
        pos = 0

        length = len(data)
        while pos < length:
            # Find the start of potential emphasis or strong tokens
            if self.compiled_re.match(data, pos):
                matched = False
                # See if the we can match an emphasis/strong pattern
                for index, item in enumerate(self.PATTERNS):
                    # Only evaluate patterns that are after what was used on the parent
                    if index <= idx:
                        continue
                    m = item.pattern.match(data, pos)
                    if m:
                        # Append child nodes to parent
                        # Text nodes should be appended to the last
                        # child if present, and if not, it should
                        # be added as the parent's text node.
                        text = data[offset:m.start(0)]
                        if text:
                            if last is not None:
                                last.tail = text
                            else:
                                parent.text = text
                        el = self.build_element(m, item.builder, item.tags, index)
                        parent.append(el)
                        last = el
                        # Move our position past the matched hunk
                        offset = pos = m.end(0)
                        matched = True
                if not matched:
                    # We matched nothing, move on to the next character
                    pos += 1
            else:
                # Increment position as no potential emphasis start was found.
                pos += 1

        # Append any leftover text as a text node.
        text = data[offset:]
        if text:
            if last is not None:
                last.tail = text
            else:
                parent.text = text

    def build_element(self, m, builder, tags, index):
        """Element builder."""

        if builder == 'double2':
            return self.build_double2(m, tags, index)
        elif builder == 'double':
            return self.build_double(m, tags, index)
        else:
            return self.build_single(m, tags, index)

    def handleMatch(self, m, data):
        """Parse patterns."""

        el = None
        start = None
        end = None

        for index, item in enumerate(self.PATTERNS):
            m1 = item.pattern.match(data, m.start(0))
            if m1:
                start = m1.start(0)
                end = m1.end(0)
                el = self.build_element(m1, item.builder, item.tags, index)
                break
        return el, start, end


class PymdownxDeprecationWarning(UserWarning):  # pragma: no cover
    """Deprecation warning for Pymdownx that is not hidden."""
