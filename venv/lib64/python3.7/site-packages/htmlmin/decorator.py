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

from .main import Minifier

def htmlmin(*args, **kwargs):
  """Minifies HTML that is returned by a function.

  A simple decorator that minifies the HTML output of any function that it
  decorates. It supports all the same options that :class:`htmlmin.minify` has.
  With no options, it uses ``minify``'s default settings::

      @htmlmin
      def foobar():
         return '   minify me!   '

  or::

      @htmlmin(remove_comments=True)
      def foobar():
         return '   minify me!  <!-- and remove me! -->'
  """
  def _decorator(fn):
    minify = Minifier(**kwargs).minify
    def wrapper(*a, **kw):
      return minify(fn(*a, **kw))
    return wrapper

  if len(args) == 1:
    if callable(args[0]) and not kwargs:
      return _decorator(args[0])
    else:
      raise RuntimeError(
          'htmlmin decorator does accept positional arguments')
  elif len(args) > 1:
    raise RuntimeError(
      'htmlmin decorator does accept positional arguments')
  else:
    return _decorator
        
