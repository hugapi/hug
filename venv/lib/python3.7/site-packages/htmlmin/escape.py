"""
Copyright (c) 2015, Dave Mankoff
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

import re

try:
  from html import escape
except ImportError:
  from cgi import escape

import re

NO_QUOTES = 0
SINGLE_QUOTE = 1
DOUBLE_QUOTE = 2

UPPER_A = ord('A')
UPPER_F = ord('F')
UPPER_Z = ord('Z')
LOWER_A = ord('a')
LOWER_F = ord('f')
LOWER_Z = ord('z')
ZERO = ord('0')
NINE = ord('9')


# https://www.w3.org/TR/html5/syntax.html#attributes-0
CHARS_TO_QUOTE_RE = re.compile(u'[\x20\x09\x0a\x0c\x0d=><`]')

def escape_tag(val):
  return escape(val)

def escape_attr_name(val):
  return escape(val)

def escape_attr_value(val, double_quote=False):
  val = escape_ambiguous_ampersand(val)
  has_html_tag = '<' in val or '>' in val
  if double_quote:
    return (val.replace('"', '&#34;'), DOUBLE_QUOTE)

  double_quote_count = 0
  single_quote_count = 0
  for ch in val:
    if ch == '"':
      double_quote_count += 1
    elif ch == "'":
      single_quote_count += 1
  if double_quote_count > single_quote_count:
    return (val.replace("'", '&#39;'), SINGLE_QUOTE)
  elif single_quote_count:
    return (val.replace('"', '&#34;'), DOUBLE_QUOTE)

  if not val or CHARS_TO_QUOTE_RE.search(val):
    return (val, DOUBLE_QUOTE)
  return (val, NO_QUOTES)

def escape_ambiguous_ampersand(val):
  # TODO: this function could probably me made a lot faster.
  if not '&' in val:  # short circuit for speed
    return val

  state = 0
  result = []
  amp_buff = []
  for c in val:
    if state == 0:  # beginning
      if c == '&':
        state = 1
      else:
        result.append(c)
    elif state == 1:  # ampersand
      ord_c = ord(c)
      if (UPPER_A <= ord_c <= UPPER_Z or
            LOWER_A <= ord_c <= LOWER_Z or
            ZERO <= ord_c <= NINE):
        amp_buff.append(c)  # TODO: use "name character references" section
        # https://html.spec.whatwg.org/multipage/syntax.html#named-character-references
      elif c == '#':
        state = 2
      elif c == ';':
        if amp_buff:
          result.append('&')
          result.extend(amp_buff)
          result.append(';')
        else:
          result.append('&;')
        state = 0
        amp_buff = []
      elif c == '&':
        if amp_buff:
          result.append('&amp;')
          result.extend(amp_buff)
        else:
          result.append('&')
        amp_buff = []
      else:
        result.append('&')
        result.extend(amp_buff)
        result.append(c)
        state = 0
        amp_buff = []
    elif state == 2:  # numeric character reference
      ord_c = ord(c)
      if c == 'x' or c == 'X':
        state = 3
      elif ZERO <= ord_c <= NINE:
        amp_buff.append(c)
      elif c == ';':
        if amp_buff:
          result.append('&#')
          result.extend(amp_buff)
          result.append(';')
        else:
          result.append('&#;')
        state = 0
        amp_buff = []
      elif c == '&':
        if amp_buff:
          result.append('&amp;#')
          result.extend(amp_buff)
        else:
          result.append('&#')
        state = 1
        amp_buff = []
      else:
        if amp_buff:
          result.append('&amp;#')
          result.extend(amp_buff)
          result.append(c)
        else:
          result.append('&#')
          result.append(c)
        state = 0
        amp_buff = []
    elif state == 3:  # hex character reference
      ord_c = ord(c)
      if (UPPER_A <= ord_c <= UPPER_F or
          LOWER_A <= ord_c <= LOWER_F or
          ZERO <= ord_c <= NINE):
        amp_buff.append(c)
      elif c == ';':
        if amp_buff:
          result.append('&#x')
          result.extend(amp_buff)
          result.append(';')
        else:
          result.append('&#x;')
        state = 0
        amp_buff = []
      elif c == '&':
        if amp_buff:
          result.append('&amp;#x')
          result.extend(amp_buff)
        else:
          result.append('&#x')
        state = 1
        amp_buff = []
      else:
        if amp_buff:
          result.append('&amp;#x')
          result.extend(amp_buff)
          result.append(c)
        else:
          result.append('&#x')
          result.append(c)
        state = 0
        amp_buff = []

  if state == 1:
    result.append('&amp;')
    result.extend(amp_buff)
  elif state == 2:
    result.append('&amp;#')
    result.extend(amp_buff)
  elif state == 3:
    result.append('&amp;#x')
    result.extend(amp_buff)

  return ''.join(result)
