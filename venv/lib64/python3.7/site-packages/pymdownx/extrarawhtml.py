"""
ExtraRawHtml.

Split out extra raw html parsing from Python Markdown.

---
Python-Markdown Extra Extension
===============================
See <https://pythonhosted.org/Markdown/extensions/extra.html>
for documentation.
Copyright The Python Markdown Project
License: [BSD](http://www.opensource.org/licenses/bsd-license.php)
"""
from __future__ import unicode_literals
from markdown import Extension
from markdown.extensions import extra
import re


class ExtraRawHtmExtension(Extension):
    """Add raw HTML extensions to Markdown class."""

    def extendMarkdown(self, md):
        """Register extension instances."""

        md.registerExtension(self)
        # Turn on processing of markdown text within raw html
        md.preprocessors['html_block'].markdown_in_raw = True
        md.parser.blockprocessors.register(
            extra.MarkdownInHtmlProcessor(md.parser), 'markdown_block', 105
        )
        md.parser.blockprocessors.tag_counter = -1
        md.parser.blockprocessors.contain_span_tags = re.compile(
            r'^(p|h[1-6]|li|dd|dt|td|th|legend|address)$',
            re.IGNORECASE
        )


def makeExtension(*args, **kwargs):
    """Return extension."""

    return ExtraRawHtmExtension(*args, **kwargs)
