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

class HTMLMinMiddleware(object):
  """WSGI Middleware that minifies html on the way out.

  :param by_default: Specifies if minification should be turned on or off by
    default. Defaults to ``True``.
  :param keep_header: The middleware recognizes one custom HTTP header that 
    can be used to turn minification on or off on a per-request basis:
    ``X-HTML-Min-Enable``. Setting the header to ``true`` will turn minfication
    on; anything else will turn minification off. If ``by_default`` is set to 
    ``False``, this header is how you would turn minification back on. The
    middleware, by default, removes the header from the output. Setting this
    to ``True`` leaves the header in tact.
  :param debug: A quick setting to turn all minification off. The middleware
    is effectively bypassed.

  This simple middleware minifies any HTML content that passes through it. Any
  additional keyword arguments beyond the three settings the middleware has are
  passed on to the internal minifier. The documentation for the options can
  be found under :class:`htmlmin.minify`.
  """
  def __init__(self, app, by_default=True, keep_header=False, 
               debug=False, **kwargs):
    self.app = app
    self.by_default = by_default
    self.debug = debug
    self.keep_header = keep_header
    self.minifier = Minifier(**kwargs)
    
  def __call__(self, environ, start_response):
    if self.debug:
      return self.app(environ, start_response)

    should_minify = []  # need to use a mutable object so we can change it
                        # in a different scope.
    def minified_start_response(status, headers, exc_info=None):
      should_minify.append(self.should_minify(headers))
      if not self.keep_header:
        headers = [(header, value) for header, value in 
                   headers if header != 'X-HTML-Min-Enable']
      start_response(status, headers, exc_info)

    html = [i for i in self.app(environ, minified_start_response)]
    if should_minify[0]:
      return [self.minifier.minify(*html)]
    return html
  
  def should_minify(self, headers):
    is_html = False
    flag_header = None
    for header, value in headers:
      if not is_html and header == 'Content-Type' and value == 'text/html':
        is_html = True
        if flag_header is not None:
          break

      if flag_header is None and header == 'X-HTML-Min-Enable':
        flag_header = (value.lower() == 'true')
        if is_html:
          break

    return is_html and (
      (self.by_default and flag_header != False) or 
      (not self.by_default and flag_header))
