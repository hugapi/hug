"""
Details.

pymdownx.details

MIT license.

Copyright (c) 2017 Isaac Muse <isaacmuse@gmail.com>

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
from __future__ import absolute_import
from __future__ import unicode_literals
from markdown import Extension
from markdown.blockprocessors import BlockProcessor
from markdown.util import etree
import re


class DetailsProcessor(BlockProcessor):
    """Details block processor."""

    START = re.compile(
        r'(?:^|\n)\?{3}(\+)? ?(?:([\w\-]+(?: +[\w\-]+)*?)?(?: +"(.*?)")|([\w\-]+(?: +[\w\-]+)*?)) *(?:\n|$)'
    )
    COMPRESS_SPACES = re.compile(r' {2,}')

    def test(self, parent, block):
        """Test block."""

        sibling = self.lastChild(parent)
        return (
            self.START.search(block) or
            (
                block.startswith(' ' * self.tab_length) and sibling is not None and
                sibling.tag.lower() == 'details'
            )
        )

    def run(self, parent, blocks):
        """Convert to details/summary block."""

        sibling = self.lastChild(parent)
        block = blocks.pop(0)

        m = self.START.search(block)
        if m:
            # remove the first line
            block = block[m.end():]

        # Get the details block and and the non-details content
        block, non_details = self.detab(block)

        if m:
            state = m.group(1)
            is_open = state is not None

            if m.group(4):
                class_name = self.COMPRESS_SPACES.sub(' ', m.group(4).lower())
                title = class_name.split(' ')[0].capitalize()
            else:
                classes = m.group(2)
                class_name = '' if classes is None else self.COMPRESS_SPACES.sub(' ', classes.lower())
                title = m.group(3)

            div = etree.SubElement(parent, 'details', ({'open': 'open'} if is_open else {}))
            if class_name:
                div.set('class', class_name)
            summary = etree.SubElement(div, 'summary')
            summary.text = title
        else:
            div = sibling

        self.parser.parseChunk(div, block)

        if non_details:
            # Insert the non-details content back into blocks
            blocks.insert(0, non_details)


class DetailsExtension(Extension):
    """Add Details extension."""

    def extendMarkdown(self, md):
        """Add Details to Markdown instance."""
        md.registerExtension(self)

        md.parser.blockprocessors.register(DetailsProcessor(md.parser), "details", 105)


def makeExtension(*args, **kwargs):
    """Return extension."""

    return DetailsExtension(*args, **kwargs)
