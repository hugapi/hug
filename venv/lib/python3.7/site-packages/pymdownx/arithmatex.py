r"""
Arithmatex.

pymdownx.arithmatex
Extension that preserves the following for MathJax use:

```
$Equation$, \(Equation\)

$$
  Display Equations
$$

\[
  Display Equations
\]

\begin{align}
  Display Equations
\end{align}
```

and `$Inline MathJax Equations$`

Inline and display equations are converted to scripts tags. You can optionally generate previews.

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
from markdown import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.blockprocessors import BlockProcessor
from markdown import util as md_util
from . import util
import re

RE_SMART_DOLLAR_INLINE = r'(?:(?<!\\)((?:\\{2})+)(?=\$)|(?<!\\)(\$)(?!\s)((?:\\.|[^\$])+?)(?<!\s)(?:\$))'
RE_DOLLAR_INLINE = r'(?:(?<!\\)((?:\\{2})+)(?=\$)|(?<!\\)(\$)((?:\\.|[^\$])+?)(?:\$))'
RE_BRACKET_INLINE = r'(?:(?<!\\)((?:\\{2})+?)(?=\\\()|(?<!\\)(\\\()((?:\\[^)]|[^\\])+?)(?:\\\)))'

RE_DOLLAR_BLOCK = r'(?P<dollar>[$]{2})(?P<math>.+?)(?P=dollar)'
RE_TEX_BLOCK = r'(?P<math2>\\begin\{(?P<env>[a-z]+\*?)\}.+?\\end\{(?P=env)\})'
RE_BRACKET_BLOCK = r'\\\[(?P<math3>(?:\\[^\]]|[^\\])+?)\\\]'


def _escape(txt):
    """Basic html escaping."""

    txt = txt.replace('&', '&amp;')
    txt = txt.replace('<', '&lt;')
    txt = txt.replace('>', '&gt;')
    txt = txt.replace('"', '&quot;')
    return txt


def _inline_mathjax_format(math, preview=False):
    """Inline math formatter."""

    if preview:
        el = md_util.etree.Element('span')
        pre = md_util.etree.SubElement(el, 'span', {'class': 'MathJax_Preview'})
        pre.text = md_util.AtomicString(math)
        script = md_util.etree.SubElement(el, 'script', {'type': 'math/tex'})
        script.text = md_util.AtomicString(math)
    else:
        el = md_util.etree.Element('script', {'type': 'math/tex'})
        el.text = md_util.AtomicString(math)
    return el


def _fence_mathjax_format(math, preview=False):
    """Block math formatter."""

    text = ''
    if preview:
        text += (
            '<div>\n' +
            '<div class="MathJax_Preview">\n' +
            _escape(math) +
            '\n</div>\n'
        )

    text += (
        '<script type="math/tex; mode=display">\n' +
        _escape(math) +
        '\n</script>\n'
    )
    if preview:
        text += '</div>'

    return text


# Formatters usable with InlineHilite
def inline_mathjax_preview_format(math, language='math', class_name='arithmatex', md=None):
    """Inline math formatter with preview."""

    return _inline_mathjax_format(math, True)


def inline_mathjax_format(math, language='math', class_name='arithmatex', md=None):
    """Inline math formatter."""

    return _inline_mathjax_format(math, False)


def inline_generic_format(math, language='math', class_name='arithmatex', md=None, wrap='\\(%s\\)'):
    """Inline generic formatter."""

    el = md_util.etree.Element('span', {'class': class_name})
    el.text = md_util.AtomicString(wrap % math)
    return el


# Formatters usable with SuperFences
def fence_mathjax_preview_format(math, language='math', class_name='arithmatex', options=None, md=None):
    """Block MathJax formatter with preview."""

    return _fence_mathjax_format(math, True)


def fence_mathjax_format(math, language='math', class_name='arithmatex', options=None, md=None):
    """Block MathJax formatter."""

    return _fence_mathjax_format(math, False)


def fence_generic_format(math, language='math', class_name='arithmatex', options=None, md=None, wrap='\\[\n%s\n\\]'):
    """Generic block formatter."""

    return '<div class="%s">%s</div>' % (class_name, (wrap % math))


class InlineArithmatexPattern(InlineProcessor):
    """Arithmatex inline pattern handler."""

    ESCAPED_BSLASH = '%s%s%s' % (md_util.STX, ord('\\'), md_util.ETX)

    def __init__(self, pattern, config):
        """Initialize."""

        # Generic setup
        self.generic = config.get('generic', False)
        wrap = config.get('tex_inline_wrap', ["\\(", "\\)"])
        self.wrap = wrap[0] + '%s' + wrap[1]

        # Default setup
        self.preview = config.get('preview', True)
        InlineProcessor.__init__(self, pattern)

    def handleMatch(self, m, data):
        """Handle notations and switch them to something that will be more detectable in HTML."""

        # Handle escapes
        escapes = m.group(1)
        if not escapes:
            escapes = m.group(4)
        if escapes:
            return escapes.replace('\\\\', self.ESCAPED_BSLASH), m.start(0), m.end(0)

        # Handle Tex
        math = m.group(3)
        if not math:
            math = m.group(6)

        if self.generic:
            return inline_generic_format(math, wrap=self.wrap), m.start(0), m.end(0)
        else:
            return _inline_mathjax_format(math, self.preview), m.start(0), m.end(0)


class BlockArithmatexProcessor(BlockProcessor):
    """MathJax block processor to find $$MathJax$$ content."""

    def __init__(self, pattern, config, md):
        """Initialize."""

        # Generic setup
        self.generic = config.get('generic', False)
        wrap = config.get('tex_block_wrap', ['\\[', '\\]'])
        self.wrap = wrap[0] + '%s' + wrap[1]

        # Default setup
        self.preview = config.get('preview', False)

        self.match = None
        self.pattern = re.compile(pattern)

        BlockProcessor.__init__(self, md.parser)

    def test(self, parent, block):
        """Return 'True' for future Python Markdown block compatibility."""

        self.match = self.pattern.match(block) if self.pattern is not None else None
        return self.match is not None

    def mathjax_output(self, parent, math):
        """Default MathJax output."""

        if self.preview:
            grandparent = parent
            parent = md_util.etree.SubElement(grandparent, 'div')
            preview = md_util.etree.SubElement(parent, 'div', {'class': 'MathJax_Preview'})
            preview.text = md_util.AtomicString(math)
        el = md_util.etree.SubElement(parent, 'script', {'type': 'math/tex; mode=display'})
        el.text = md_util.AtomicString(math)

    def generic_output(self, parent, math):
        """Generic output."""

        el = md_util.etree.SubElement(parent, 'div', {'class': 'arithmatex'})
        el.text = md_util.AtomicString(self.wrap % math)

    def run(self, parent, blocks):
        """Find and handle block content."""

        blocks.pop(0)

        math = self.match.group('math')
        if not math:
            math = self.match.group('math2')
        if not math:
            math = self.match.group('math3')

        if self.generic:
            self.generic_output(parent, math)
        else:
            self.mathjax_output(parent, math)

        return True


class ArithmatexExtension(Extension):
    """Adds delete extension to Markdown class."""

    def __init__(self, *args, **kwargs):
        """Initialize."""

        self.config = {
            'tex_inline_wrap': [
                ["\\(", "\\)"],
                "Wrap inline content with the provided text ['open', 'close'] - Default: ['', '']"
            ],
            'tex_block_wrap': [
                ["\\[", "\\]"],
                "Wrap blick content with the provided text ['open', 'close'] - Default: ['', '']"
            ],
            "smart_dollar": [True, "Use Arithmatex's smart dollars - Default True"],
            "block_syntax": [
                ['dollar', 'square', 'begin'],
                'Enable block syntax: "dollar" ($$...$$), "square" (\\[...\\]), and '
                '"begin" (\\begin{env}...\\end{env}). - Default: ["dollar", "square", "begin"]'
            ],
            "inline_syntax": [
                ['dollar', 'round'],
                'Enable block syntax: "dollar" ($$...$$), "bracket" (\\(...\\)) '
                ' - Default: ["dollar", "round"]'
            ],
            'generic': [False, "Output in a generic format for non MathJax libraries - Default: False"],
            'preview': [
                True,
                "Insert a preview for scripts. - Default: False"
            ]
        }

        super(ArithmatexExtension, self).__init__(*args, **kwargs)

    def extendMarkdown(self, md):
        """Extend the inline and block processor objects."""

        md.registerExtension(self)
        util.escape_chars(md, ['$'])

        config = self.getConfigs()

        # Inline patterns
        allowed_inline = set(config.get('inline_syntax', ['dollar', 'round']))
        smart_dollar = config.get('smart_dollar', True)
        inline_patterns = []
        if 'dollar' in allowed_inline:
            inline_patterns.append(RE_SMART_DOLLAR_INLINE if smart_dollar else RE_DOLLAR_INLINE)
        if 'round' in allowed_inline:
            inline_patterns.append(RE_BRACKET_INLINE)
        if inline_patterns:
            inline = InlineArithmatexPattern('(?:%s)' % '|'.join(inline_patterns), config)
            md.inlinePatterns.register(inline, 'arithmatex-inline', 189.9)

        # Block patterns
        allowed_block = set(config.get('block_syntax', ['dollar', 'square', 'begin']))
        block_pattern = []
        if 'dollar' in allowed_block:
            block_pattern.append(RE_DOLLAR_BLOCK)
        if 'square' in allowed_block:
            block_pattern.append(RE_BRACKET_BLOCK)
        if 'begin' in allowed_block:
            block_pattern.append(RE_TEX_BLOCK)
        if block_pattern:
            block = BlockArithmatexProcessor(r'(?s)^(?:%s)[ ]*$' % '|'.join(block_pattern), config, md)
            md.parser.blockprocessors.register(block, "arithmatex-block", 79.9)


def makeExtension(*args, **kwargs):
    """Return extension."""

    return ArithmatexExtension(*args, **kwargs)
