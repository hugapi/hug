#!/usr/bin/env python
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

import argparse
import codecs
import locale
import io
import sys

#import htmlmin
from . import Minifier

parser = argparse.ArgumentParser(
  description='Minify HTML',
  formatter_class=argparse.RawTextHelpFormatter
  )

parser.add_argument('input_file',
  nargs='?',
  metavar='INPUT',
  help='File path to html file to minify. Defaults to stdin.',
  )

parser.add_argument('output_file',
  nargs='?',
  metavar='OUTPUT',
  help="File path to output to. Defaults to stdout.",
  )

parser.add_argument('-c', '--remove-comments',
  help=(
'''When set, comments will be removed. They can be kept on an individual basis
by starting them with a '!': <!--! comment -->. The '!' will be removed from
the final output. If you want a '!' as the leading character of your comment,
put two of them: <!--!! comment -->.

'''),
  action='store_true')

parser.add_argument('-s', '--remove-empty-space',
  help=(
'''When set, this removes empty space betwen tags in certain cases.
Specifically, it will remove empty space if and only if there a newline
character occurs within the space. Thus, code like
'<span>x</span> <span>y</span>' will be left alone, but code such as
'   ...
  </head>
  <body>
    ...'
will become '...</head><body>...'. Note that this CAN break your
html if you spread two inline tags over two lines. Use with caution.

'''),
  action='store_true')

parser.add_argument('--remove-all-empty-space',
  help=(
'''When set, this removes ALL empty space betwen tags. WARNING: this can and
likely will cause unintended consequences. For instance, '<i>X</i> <i>Y</i>'
will become '<i>X</i><i>Y</i>'. Putting whitespace along with other text will
avoid this problem. Only use if you are confident in the result. Whitespace is
not removed from inside of tags, thus '<span> </span>' will be left alone.

'''),
  action='store_true')

parser.add_argument('--keep-optional-attribute-quotes',
  help=(
'''When set, this keeps all attribute quotes, even if they are optional.

'''),
  action='store_true')

parser.add_argument('-H', '--in-head',
  help=(
'''If you are parsing only a fragment of HTML, and the fragment occurs in the
head of the document, setting this will remove some extra whitespace.

'''),
  action='store_true')

parser.add_argument('-k', '--keep-pre-attr',
  help=(
'''HTMLMin supports the propietary attribute 'pre' that can be added to elements
to prevent minification. This attribute is removed by default. Set this flag to
keep the 'pre' attributes in place.

'''),
  action='store_true')

parser.add_argument('-a', '--pre-attr',
  help=(
'''The attribute htmlmin looks for to find blocks of HTML that it should not
minify. This attribute will be removed from the HTML unless '-k' is
specified. Defaults to 'pre'.

'''),
  default='pre')


parser.add_argument('-p', '--pre-tags',
  metavar='TAG',
  help=(
'''By default, the contents of 'pre', and 'textarea' tags are left unminified.
You can specify different tags using the --pre-tags option. 'script' and 'style'
tags are always left unmininfied.

'''),
  nargs='*',
  default=['pre', 'textarea'])
parser.add_argument('-e', '--encoding',
  help=("Encoding to read and write with. Default 'utf-8'."
        " When reading from stdin, attempts to use the system's"
        " encoding before defaulting to utf-8.\n\n"),
  default=None,
  )

def main():
  args = parser.parse_args()
  minifier = Minifier(
    remove_comments=args.remove_comments,
    remove_empty_space=args.remove_empty_space,
    remove_optional_attribute_quotes=not args.keep_optional_attribute_quotes,
    pre_tags=args.pre_tags,
    keep_pre=args.keep_pre_attr,
    pre_attr=args.pre_attr,
    )
  default_encoding = args.encoding or 'utf-8'

  if args.input_file:
    inp = codecs.open(args.input_file, encoding=default_encoding)
  else:
    encoding = args.encoding or sys.stdin.encoding \
      or locale.getpreferredencoding() or default_encoding
    inp = io.open(sys.stdin.fileno(), encoding=encoding)

  for line in inp.readlines():
    minifier.input(line)

  if args.output_file:
    codecs.open(
      args.output_file, 'w', encoding=default_encoding).write(minifier.output)
  else:
    encoding = args.encoding or sys.stdout.encoding \
      or locale.getpreferredencoding() or default_encoding
    io.open(sys.stdout.fileno(), 'w', encoding=encoding).write(minifier.output)

if __name__ == '__main__':
  main()

