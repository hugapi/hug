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

import cgi

from . import parser

def minify(input,
           remove_comments=False,
           remove_empty_space=False,
           remove_all_empty_space=False,
           reduce_empty_attributes=True,
           reduce_boolean_attributes=False,
           remove_optional_attribute_quotes=True,
           convert_charrefs=True,
           keep_pre=False,
           pre_tags=parser.PRE_TAGS,
           pre_attr='pre',
           cls=parser.HTMLMinParser):
  """Minifies HTML in one shot.

  :param input: A string containing the HTML to be minified.
  :param remove_comments: Remove comments found in HTML. Individual comments can
    be maintained by putting a ``!`` as the first character inside the comment.
    Thus::

       <!-- FOO --> <!--! BAR -->

    Will become simply::

       <!-- BAR -->

    The added exclamation is removed.
  :param remove_empty_space: Remove empty space found in HTML between an opening
    and a closing tag and when it contains a newline or carriage return. If
    whitespace is found that is only spaces and/or tabs, it will be turned into
    a single space. Be careful, this can have unintended consequences.
  :param remove_all_empty_space: A more extreme version of
    ``remove_empty_space``, this removes all empty whitespace found between
    tags. This is almost guaranteed to break your HTML unless you are very
    careful.
  :param reduce_boolean_attributes: Where allowed by the HTML5 specification,
    attributes such as 'disabled' and 'readonly' will have their value removed,
    so 'disabled="true"' will simply become 'disabled'. This is generally a
    good option to turn on except when JavaScript relies on the values.
  :param remove_optional_attribute_quotes: When True, optional quotes around
    attributes are removed. When False, all attribute quotes are left intact.
    Defaults to True.
  :param conver_charrefs: Decode character references such as &amp; and &#46;
    to their single charater values where safe. This currently only applies to
    attributes. Data content between tags will be left encoded.
  :param keep_pre: By default, htmlmin uses the special attribute ``pre`` to
    allow you to demarcate areas of HTML that should not be minified. It removes
    this attribute as it finds it. Setting this value to ``True`` tells htmlmin
    to leave the attribute in the output.
  :param pre_tags: A list of tag names that should never be minified. You are
    free to change this list as you see fit, but you will probably want to
    include ``pre`` and ``textarea`` if you make any changes to the list. Note
    that ``<script>`` and ``<style>`` tags are never minimized.
  :param pre_attr: Specifies the attribute that, when found in an HTML tag,
    indicates that the content of the tag should not be minified. Defaults to
    ``pre``. You can also prefix individual tag attributes with 
    ``{pre_attr}-`` to prevent the contents of the individual attribute from
    being changed.
  :return: A string containing the minified HTML.

  If you are going to be minifying multiple HTML documents, each with the same
  settings, consider using :class:`.Minifier`.
  """
  minifier = cls(
      remove_comments=remove_comments,
      remove_empty_space=remove_empty_space,
      remove_all_empty_space=remove_all_empty_space,
      reduce_empty_attributes=reduce_empty_attributes,
      reduce_boolean_attributes=reduce_boolean_attributes,
      remove_optional_attribute_quotes=remove_optional_attribute_quotes,
      convert_charrefs=convert_charrefs,
      keep_pre=keep_pre,
      pre_tags=pre_tags,
      pre_attr=pre_attr)
  minifier.feed(input)
  minifier.close()
  return minifier.result

class Minifier(object):
  """An object that supports HTML Minification.

  Options are passed into this class at initialization time and are then
  persisted across each use of the instance. If you are going to be minifying
  multiple peices of HTML, this will be more efficient than using
  :class:`htmlmin.minify`.

  See :class:`htmlmin.minify` for an explanation of options.
  """

  def __init__(self,
               remove_comments=False,
               remove_empty_space=False,
               remove_all_empty_space=False,
               reduce_empty_attributes=True,
               reduce_boolean_attributes=False,
               remove_optional_attribute_quotes=True,
               convert_charrefs=True,
               keep_pre=False,
               pre_tags=parser.PRE_TAGS,
               pre_attr='pre',
               cls=parser.HTMLMinParser):
    """Initialize the Minifier.

    See :class:`htmlmin.minify` for an explanation of options.
    """
    self._parser = cls(
      remove_comments=remove_comments,
      remove_empty_space=remove_empty_space,
      remove_all_empty_space=remove_all_empty_space,
      reduce_empty_attributes=reduce_empty_attributes,
      reduce_boolean_attributes=reduce_boolean_attributes,
      remove_optional_attribute_quotes=remove_optional_attribute_quotes,
      convert_charrefs=convert_charrefs,
      keep_pre=keep_pre,
      pre_tags=pre_tags,
      pre_attr=pre_attr)

  def minify(self, *input):
    """Runs HTML through the minifier in one pass.

    :param input: HTML to be fed into the minimizer. Multiple chunks of HTML
      can be provided, and they are fed in sequentially as if they were
      concatenated.
    :returns: A string containing the minified HTML.

    This is the simplest way to use an existing ``Minifier`` instance. This
    method takes in HTML and minfies it, returning the result. Note that this
    method resets the internal state of  the parser before it does any work. If
    there is pending HTML in the buffers, it will be lost.
    """
    self._parser.reset()
    self.input(*input)
    return self.finalize()

  def input(self, *input):
    """Feed more HTML into the input stream

    :param input: HTML to be fed into the minimizer. Multiple chunks of HTML
      can be provided, and they are fed in sequentially as if they were
      concatenated. You can also call this method multiple times to achieve
      the same effect.
    """
    for i in input:
      self._parser.feed(i)

  @property
  def output(self):
    """Retrieve the minified output generated thus far.
    """
    return self._parser.result

  def finalize(self):
    """Finishes current input HTML and returns mininified result.

    This method flushes any remaining input HTML and returns the minified
    result. It resets the state of the internal parser in the process so that
    new HTML can be minified. Be sure to call this method before you reuse
    the ``Minifier`` instance on a new HTML document.
    """
    self._parser.close()
    result = self._parser.result
    self._parser.reset()
    return result
