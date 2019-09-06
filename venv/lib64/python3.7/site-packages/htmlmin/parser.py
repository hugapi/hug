"""
Copyright (c) 2013, Dave Mankoff
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Dave Mankoff nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL DAVE MANKOFF BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import unicode_literals
import logging
import sys

import re
from .python3html.parser import HTMLParser

from . import escape

# https://www.w3.org/TR/html5/single-page.html#space-character
HTML_SPACE_RE = re.compile('[\x20\x09\x0a\x0c\x0d]+')
HTML_ALL_SPACE_RE = re.compile('^[\x20\x09\x0a\x0c\x0d]+$')
HTML_LEADING_SPACE_RE = re.compile(
  '^[\x20\x09\x0a\x0c\x0d]+')
HTML_TRAILING_SPACE_RE = re.compile(
  '[\x20\x09\x0a\x0c\x0d]+$')
HTML_LEADING_TRAILING_SPACE_RE = re.compile(
  '(^[\x20\x09\x0a\x0c\x0d]+)|([\x20\x09\x0a\x0c\x0d]+$)')

PRE_TAGS = ('pre', 'textarea')  # styles and scripts are never minified
# http://www.w3.org/TR/html51/syntax.html#elements-0
NO_CLOSE_TAGS = ('area', 'base', 'br', 'col', 'command', 'embed', 'hr', 'img',
                 'input', 'keygen', 'link', 'meta', 'param', 'source', 'track',
                 'wbr')
# http://www.w3.org/TR/html51/index.html#attributes-1
BOOLEAN_ATTRIBUTES = {
  'audio': ('autoplay', 'controls', 'hidden', 'loop', 'muted',),
  'button': ('autofocus', 'disabled', 'formnovalidate', 'hidden',),
  'command': ('checked', 'disabled', 'hidden'),
  'dialog': ('hidden', 'open',),
  'fieldset': ('disabled', 'hidden',),
  'form': ('hidden', 'novalidate',),
  'iframe': ('hidden', 'seamless',),
  'img': ('hidden', 'ismap',),
  'input': ('autofocus', 'checked', 'disabled', 'formnovalidate', 'hidden',
            'multiple', 'readonly', 'required',),
  'keygen': ('autofocus', 'disabled', 'hidden',),
  'object': ('hidden', 'typesmustmatch',),
  'ol': ('hidden', 'reversed',),
  'optgroup': ('disabled', 'hidden',),
  'option': ('disabled', 'hidden', 'selected',),
  'script': ('async', 'defer', 'hidden',),
  'select': ('autofocus', 'disabled', 'hidden', 'multiple', 'required',),
  'style': ('hidden', 'scoped',),
  'textarea': ('autofocus', 'disabled', 'hidden', 'readonly', 'required',),
  'track': ('default', 'hidden', ),
  'video': ('autoplay', 'controls', 'hidden', 'loop', 'muted',),
  '*': ('hidden',),
}

# a list of tags and tags that they are closed by
TAG_SETS = {
  'li': ('li',),
  'dd': ('dd', 'dt'),
  'rp': ('rp', 'rt'),
  'p': ('address', 'article', 'aside', 'blockquote', 'dir', 'div', 'dl',
        'fieldset', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'header', 'hgroup', 'hr', 'menu', 'nav', 'ol', 'p', 'pre', 'section',
        'table', 'ul'),
  'optgroup': ('optgroup',),
  'option': ('option', 'optgroup'),
  'colgroup': '*',
  'tbody': ('tbody', 'tfoot'),
  'tfoot': ('tbody',),
  'tr': ('tr',),
  'td': ('td', 'th'),
}
TAG_SETS['dt'] = TAG_SETS['dd']
TAG_SETS['rt'] = TAG_SETS['rp']
TAG_SETS['thead'] = TAG_SETS['tbody']
TAG_SETS['th'] = TAG_SETS['td']

# Tag omission rules:
# http://www.w3.org/TR/html51/syntax.html#optional-tags

class HTMLMinError(Exception): pass
class ParseError(HTMLMinError): pass
class OpenTagNotFoundError(ParseError): pass

class HTMLMinParser(HTMLParser):
  def __init__(self,
               remove_comments=False,
               remove_empty_space=False,
               remove_all_empty_space=False,
               reduce_empty_attributes=True,
               reduce_boolean_attributes=False,
               remove_optional_attribute_quotes=True,
               convert_charrefs=True,
               keep_pre=False,
               pre_tags=PRE_TAGS,
               pre_attr='pre'):
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
      # convert_charrefs is True by default in Python 3.5.0 and newer. It was
      # introduced in 3.4.
      HTMLParser.__init__(self, convert_charrefs=False)
    else:
      HTMLParser.__init__(self)
    self.keep_pre = keep_pre
    self.pre_tags = pre_tags
    self.remove_comments = remove_comments
    self.remove_empty_space = remove_empty_space
    self.remove_all_empty_space = remove_all_empty_space
    self.reduce_empty_attributes = reduce_empty_attributes
    self.reduce_boolean_attributes = reduce_boolean_attributes
    self.remove_optional_attribute_quotes = remove_optional_attribute_quotes
    self.convert_charrefs = convert_charrefs
    self.pre_attr = pre_attr
    self.reset()

  def _tag_lang(self):
    return self._tag_stack[0][2] if self._tag_stack else None

  def build_tag(self, tag, attrs, close_tag):
    has_pre = False

    if self.reduce_boolean_attributes:
      bool_attrs = BOOLEAN_ATTRIBUTES.get(tag, BOOLEAN_ATTRIBUTES['*'])
    else:
      bool_attrs = False

    lang = self._tag_lang()
    attrs = list(attrs)  # We're modifying it in place
    last_quoted = last_no_slash = i = -1
    for k, v in attrs:
      pre_prefix = k.startswith("{}-".format(self.pre_attr))
      if pre_prefix:
        k = k[len(self.pre_attr)+1:]
      if k == self.pre_attr:
        has_pre = True
        if not self.keep_pre and not pre_prefix:
          continue
      if v and self.convert_charrefs and not pre_prefix:
        v = HTMLParser.unescape(self, v)
      if k == 'lang':
        lang = v
        if v == self._tag_lang():
          continue

      i += 1
      if not pre_prefix:
        k = escape.escape_attr_name(k)
      if (v is None or (not v and self.reduce_empty_attributes) or
          (bool_attrs and k in bool_attrs)):
        # For our use case, we treat boolean attributes as quoted because they
        # don't require space between them and "/>" in closing tags.
        attrs[i] = k
        last_quoted = i
      else:
        if pre_prefix:
          has_double_quotes = '"' in v
          has_single_quotes = "'" in v
          if not has_double_quotes:
            if not has_single_quotes and self.remove_optional_attribute_quotes:
              q = escape.NO_QUOTES
            else:
              q = escape.DOUBLE_QUOTE
          elif not has_single_quotes:
            q = escape.SINGLE_QUOTES
          else:
            logging.error('Unsafe content found in pre-attribute. Escaping.')
            (v, q) = escape.escape_attr_value(
              v, double_quote=not self.remove_optional_attribute_quotes)
        else:
          (v, q) = escape.escape_attr_value(
            v, double_quote=not self.remove_optional_attribute_quotes)
        if q == escape.NO_QUOTES:
          attrs[i] = '%s=%s' % (k, v)
          if v[-1] != '/':
            last_no_slash = i
        else:
          q = '"' if q == escape.DOUBLE_QUOTE else "'"
          attrs[i] = '%s=%s%s%s' % (k, q, v, q)
          last_quoted = i

    i += 1
    if i != len(attrs):
      del attrs[i:]

    # 1. If there are no attributes, no additional space is necessary.
    # 2. If last attribute is quoted, no additional space is necessary.
    # 3. Two things are happening here:
    #    a) according to the standard, <foo bar=baz/> should be treated as <foo
    #       bar="baz/"> so space is necessary if this is self-closing tag,
    #       however
    #    b) reportedly (https://github.com/mankyd/htmlmin/pull/12), older
    #       versions of WebKit interpret <foo bar=baz/> as self-closing tag so
    #       we need the space if the last argument ends with a slash.
    space_maybe = ''
    if attrs:
      needs_space = lambda last_attr: (last_attr[-1] not in '"\'' and
                                       (close_tag or last_attr[-1] == '/'))
      if needs_space(attrs[-1][-1]):
        # If moving attributes around can help, do it.  Otherwise bite the
        # bullet and put the space in.
        i = last_no_slash if last_quoted == -1 else last_quoted
        if i == -1 or needs_space(attrs[i]):
          space_maybe = ' '
        else:
          attrs.append(attrs[i])
          del attrs[i]

    return has_pre, '<%s%s%s%s%s>' % (escape.escape_tag(tag),
                                      ' ' if attrs else '',
                                      ' '.join(attrs),
                                      space_maybe,
                                      '/' if close_tag else ''), lang

  def handle_decl(self, decl):
    if (len(self._data_buffer) == 1 and 
        HTML_SPACE_RE.match(self._data_buffer[0][0])):
      self._data_buffer = []
    self._data_buffer.append('<!' + decl + '>')
    self._after_doctype = True

  def _close_tags_up_to(self, tag):
    num_pres = 0
    i = 0
    for i, t in enumerate(self._tag_stack):
      if t[1]:
        num_pres += 1
      if t[0] == tag:
        break

      # Only the html tag can close out everything. Put on the brakes if
      # we encounter a closing tag that we didn't recognize.
      if tag != 'html' and t[0] in ('body', 'html', 'head'):
        raise OpenTagNotFoundError()

    self._tag_stack = self._tag_stack[i+1:]

    return num_pres

  def handle_starttag(self, tag, attrs):
    self._after_doctype = False
    if tag == 'head':
      self._in_head = True
    elif self._in_head and tag == 'title':
      self._in_title = True
      self._title_newly_opened = True

    for t in self._tag_stack:
      closed_by_tags = TAG_SETS.get(t[0])
      if closed_by_tags and (closed_by_tags == '*' or tag in closed_by_tags):
        self._in_pre_tag -= self._close_tags_up_to(t[0])
        break

    has_pre, data, lang = self.build_tag(tag, attrs, False)
    start_pre = False
    if (has_pre or self._in_pre_tag > 0 or
        tag == 'script' or tag == 'style' or tag in self.pre_tags):
      self._in_pre_tag += 1
      start_pre = True

    self._tag_stack.insert(0, (tag, start_pre, lang))
    self._data_buffer.append(data)

  def handle_endtag(self, tag):
    # According to the spec, <p> tags don't get closed when a parent a
    # tag closes them. Here's some logic that addresses this.
    if tag == 'a':
      contains_p = False
      for i, t in enumerate(self._tag_stack):
        if t[0] == 'p':
          contains_p = True
        elif t[0] == 'a':
          break
      if contains_p: # the p tag, and all its children should be left open
        a_tag = self._tag_stack.pop(i)
        if a_tag[1]:
          self._in_pre_tag -= 1
    else:
      if tag == 'head':
        # TODO: Did we know that we were in an head tag?! If not, we need to
        # reminify everything to remove extra spaces.
        self._in_head = False
      elif tag == 'title':
        self._in_title = False
        self._title_newly_opened = False
      try:
        self._in_pre_tag -= self._close_tags_up_to(tag)
      except OpenTagNotFoundError:
        # Some tags don't require a start tag. Most do. Either way, we leave
        # closing tags along since they affect output. For instance, a '</p>'
        # results in a '<p></p>' in Chrome.
        pass
    if tag not in NO_CLOSE_TAGS:
      self._data_buffer.extend(['</', escape.escape_tag(tag), '>'])

  def handle_startendtag(self, tag, attrs):
    self._after_doctype = False
    data = self.build_tag(tag, attrs, tag not in NO_CLOSE_TAGS)[1]
    self._data_buffer.append(data)

  def handle_comment(self, data):
    if not self.remove_comments or re.match(r'^(?:!|\[if\s)', data):
      self._data_buffer.append('<!--{}-->'.format(
          data[1:] if len(data) and data[0] == '!' else data))

  def handle_data(self, data):
    if self._in_pre_tag > 0:
      self._data_buffer.append(data)
    else:
      # remove_all_empty_space matches everything. remove_empty_space only
      # matches if there's a newline involved.
      if self.remove_all_empty_space or self._in_head or self._after_doctype:
        if HTML_ALL_SPACE_RE.match(data):
          return
      elif (self.remove_empty_space and HTML_ALL_SPACE_RE.match(data) and
            ('\n' in data or '\r' in data)):
        return

      # if we're in the title, remove leading and trailing whitespace.
      # note that the title may be parsed in chunks if entityref's or charrefs
      # are encountered.
      if self._in_title:
        if self.__title_trailing_whitespace:
          self._data_buffer.append(' ')
        self.__title_trailing_whitespace = (
          HTML_ALL_SPACE_RE.match(data[-1]) is not None)
        if self._title_newly_opened:
          self._title_newly_opened = False
          data = HTML_LEADING_TRAILING_SPACE_RE.sub('', data)
        else:
          data = HTML_TRAILING_SPACE_RE.sub(
            '', HTML_LEADING_TRAILING_SPACE_RE.sub(' ', data))

      data = HTML_SPACE_RE.sub(' ', data)
      if not data:
        return

      if self._in_pre_tag == 0 and self._data_buffer:
        # If we're not in a pre block, its possible that we append two spaces
        # together, which we want to avoid. For instance, if we remove a comment
        # from between two blocks of text: a <!-- B --> c => a  c.
        if data[0] == ' ' and self._data_buffer[-1][-1] == ' ':
          data = data[1:]
          if not data:
            return
      self._data_buffer.append(data)

  def handle_entityref(self, data):
    if self._in_title:
      if not self._title_newly_opened and self.__title_trailing_whitespace:
        self._data_buffer.append(' ')
        self.__title_trailing_whitespace = False
      self._title_newly_opened = False
    self._data_buffer.append('&{};'.format(data))

  def handle_charref(self, data):
    if self._in_title:
      if not self._title_newly_opened and self.__title_trailing_whitespace:
        self._data_buffer.append(' ')
        self.__title_trailing_whitespace = False
      self._title_newly_opened = False
    self._data_buffer.append('&#{};'.format(data))

  def handle_pi(self, data):
    self._data_buffer.append('<?' + data + '>')

  def unknown_decl(self, data):
    self._data_buffer.append('<![' + data + ']>')

  def reset(self):
    self._data_buffer = []
    self._in_pre_tag = 0
    self._in_head = False
    self._in_title = False
    self._after_doctype = False
    self._tag_stack = []
    self._title_newly_opened = False
    self.__title_trailing_whitespace = False
    HTMLParser.reset(self)

  def unescape(self, val):
    """Override this method so that we can handle char ref conversion ourself.
    """
    return val

  @property
  def result(self):
    return ''.join(self._data_buffer)
