"""
SuperFences.

pymdownx.superfences
Nested Fenced Code Blocks

This is a modification of the original Fenced Code Extension.
Algorithm has been rewritten to allow for fenced blocks in blockquotes,
lists, etc.  And also , allow for special UML fences like 'flow' for flowcharts
and `sequence` for sequence diagrams.

Modified: 2014 - 2017 Isaac Muse <isaacmuse@gmail.com>
---

Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

See <https://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html>
for documentation.

Original code Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).


All changes Copyright 2008-2014 The Python Markdown Project

License: [BSD](http://www.opensource.org/licenses/bsd-license.php)
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.postprocessors import Postprocessor
from markdown.blockprocessors import CodeBlockProcessor
from markdown import util as md_util
import functools
import re

SOH = '\u0001'  # start
EOT = '\u0004'  # end

PREFIX_CHARS = ('>', ' ', '\t')

RE_NESTED_FENCE_START = re.compile(
    r'''(?x)
    (?P<fence>~{3,}|`{3,})[ \t]*                                                   # Fence opening
    (\{?                                                                           # Language opening
    \.?(?P<lang>[\w#.+-]*))?[ \t]*                                                 # Language
    (?P<options>(?:\b[a-zA-Z][a-zA-Z0-9_]*=(?:(?P<quot>"|').*?(?P=quot))?[ \t]*)*) # Options
    }?[ \t]*$                                                                      # Language closing
    '''
)

RE_HL_LINES = re.compile(r'(?P<hl_lines>\d+(?:[ \t]+\d+)*)')
RE_LINENUMS = re.compile(r'(?P<linestart>[\d]+)(?:[ \t]+(?P<linestep>[\d]+))?(?:[ \t]+(?P<linespecial>[\d]+))?')
RE_OPTIONS = re.compile(r'''(?P<key>[a-zA-Z][a-zA-Z0-9_]*)=(?:(?P<quot>"|')(?P<value>.*?)(?P=quot))?''')

RE_TABS = re.compile(r'((?:<p><superfences>.*?</superfences></p>\s*)+)', re.DOTALL)

TAB = r'''<superfences><input name="__tabs_%%(index)s" type="radio" id="__tab_%%(index)s_%%(tab_index)s" %%(state)s/>
<label for="__tab_%%(index)s_%%(tab_index)s">%(title)s</label>
<div class="superfences-content">%(code)s</div></superfences>'''

NESTED_FENCE_END = r'%s[ \t]*$'

FENCED_BLOCK_RE = re.compile(
    r'^([\> ]*)%s(%s)%s$' % (
        md_util.HTML_PLACEHOLDER[0],
        md_util.HTML_PLACEHOLDER[1:-1] % r'([0-9]+)',
        md_util.HTML_PLACEHOLDER[-1]
    )
)


def _escape(txt):
    """Basic html escaping."""

    txt = txt.replace('&', '&amp;')
    txt = txt.replace('<', '&lt;')
    txt = txt.replace('>', '&gt;')
    return txt


class CodeStash(object):
    """
    Stash code for later retrieval.

    Store original fenced code here in case we were
    too greedy and need to restore in an indented code
    block.
    """

    def __init__(self):
        """Initialize."""

        self.stash = {}

    def __len__(self):  # pragma: no cover
        """Length of stash."""

        return len(self.stash)

    def get(self, key, default=None):
        """Get the code from the key."""

        code = self.stash.get(key, default)
        return code

    def remove(self, key):
        """Remove the stashed code."""

        del self.stash[key]

    def store(self, key, code, indent_level):
        """Store the code in the stash."""

        self.stash[key] = (code, indent_level)

    def clear_stash(self):
        """Clear the stash."""

        self.stash = {}


def fence_code_format(source, language, css_class, options, md):
    """Format source as code blocks."""

    return '<pre class="%s"><code>%s</code></pre>' % (css_class, _escape(source))


def fence_div_format(source, language, css_class, options, md):
    """Format source as div."""

    return '<div class="%s">%s</div>' % (css_class, _escape(source))


def highlight_validator(language, options):
    """Highlight validator."""

    okay = True
    # Check for invalid keys
    for k in options.keys():
        if k not in ('hl_lines', 'linenums'):
            okay = False
            break

    # Check format of valid keys
    if okay:
        for opt, validator in (('hl_lines', RE_HL_LINES), ('linenums', RE_LINENUMS)):
            if opt in options:
                value = options[opt]
                if value is True or validator.match(options[opt]) is None:
                    okay = False
                    break

    return okay


def default_validator(language, options):
    """Default validator."""

    return len(options) == 0


def _validator(language, options, validator=None):
    """Validator wrapper."""

    return validator(language, options)


def _formatter(source, language, options, md, class_name="", fmt=None):
    """Formatter wrapper."""

    return fmt(source, language, class_name, options, md)


def _test(language, test_language=None):
    """Test language."""

    return test_language is None or language == test_language


class SuperFencesCodeExtension(Extension):
    """SuperFences code block extension."""

    def __init__(self, *args, **kwargs):
        """Initialize."""

        self.superfences = []
        self.config = {
            'disable_indented_code_blocks': [False, "Disable indented code blocks - Default: False"],
            'custom_fences': [[], 'Specify custom fences. Default: See documentation.'],
            'highlight_code': [True, "Highlight code - Default: True"],
            'css_class': [
                '',
                "Set class name for wrapper element. The default of CodeHilite or Highlight will be used"
                "if nothing is set. - "
                "Default: ''"
            ],
            'preserve_tabs': [False, "Preserve tabs in fences - Default: False"]
        }
        super(SuperFencesCodeExtension, self).__init__(*args, **kwargs)

    def extend_super_fences(self, name, formatter, validator):
        """Extend SuperFences with the given name, language, and formatter."""

        self.superfences.append(
            {
                "name": name,
                "test": functools.partial(_test, test_language=name),
                "formatter": formatter,
                "validator": validator
            }
        )

    def extendMarkdown(self, md):
        """Add fenced block preprocessor to the Markdown instance."""

        # Not super yet, so let's make it super
        md.registerExtension(self)
        config = self.getConfigs()

        # Default fenced blocks
        self.superfences.insert(
            0,
            {
                "name": "superfences",
                "test": _test,
                "formatter": None,
                "validator": functools.partial(_validator, validator=highlight_validator)
            }
        )

        # Custom Fences
        custom_fences = config.get('custom_fences', [])
        for custom in custom_fences:
            name = custom.get('name')
            class_name = custom.get('class')
            fence_format = custom.get('format', fence_code_format)
            validator = custom.get('validator', default_validator)
            if name is not None and class_name is not None:
                self.extend_super_fences(
                    name,
                    functools.partial(_formatter, class_name=class_name, fmt=fence_format),
                    functools.partial(_validator, validator=validator)
                )

        self.md = md
        self.patch_fenced_rule()
        self.stash = CodeStash()

    def patch_fenced_rule(self):
        """
        Patch Python Markdown with our own fenced block extension.

        We don't attempt to protect against a user loading the `fenced_code` extension with this.
        Most likely they will have issues, but they shouldn't have loaded them together in the first place :).
        """

        config = self.getConfigs()

        fenced = SuperFencesBlockPreprocessor(self.md)
        fenced.config = config
        fenced.extension = self
        self.superfences[0]["formatter"] = fenced.highlight
        self.md.preprocessors.register(fenced, "fenced_code_block", 25)

        indented_code = SuperFencesCodeBlockProcessor(self.md.parser)
        indented_code.config = config
        indented_code.extension = self
        self.md.parser.blockprocessors.register(indented_code, "code", 80)

        if config["preserve_tabs"]:
            # Need to squeeze in right after critic.
            raw_fenced = SuperFencesRawBlockPreprocessor(self.md)
            raw_fenced.config = config
            raw_fenced.extension = self
            self.md.preprocessors.register(raw_fenced, "fenced_raw_block", 31.05)
            self.md.registerExtensions(["pymdownx._bypassnorm"], {})

        self.md.postprocessors.register(SuperFencesTabPostProcessor(self.md), "fenced_tabs", 25)

        # Add the highlight extension, but do so in a disabled state so we can just retrieve default configurations
        self.md.registerExtensions(["pymdownx.highlight"], {"pymdownx.highlight": {"_enabled": False}})

    def reset(self):
        """Clear the stash."""

        self.stash.clear_stash()


class SuperFencesTabPostProcessor(Postprocessor):
    """Post processor for grouping tabs."""

    def repl(self, m):
        """Replace grouped superfences tabs with a tab group."""

        self.count += 1
        tab_count = 0
        tabs = []
        for entry in [x.strip() for x in m.group(1).split('</superfences></p>')]:
            tabs.append(
                entry.replace('<p><superfences>', '') % {
                    'index': self.count,
                    'tab_index': tab_count,
                    'state': ('checked="checked" ' if tab_count == 0 else ''),
                    'tab_title': 'Tab %d' % (tab_count + 1)
                }
            )
            tab_count += 1
        return '<div class="superfences-tabs">\n' + '\n'.join(tabs) + '</div>\n'

    def run(self, text):
        """Search for superfences tab and group consecutive tabs together."""

        self.count = 0
        return RE_TABS.sub(self.repl, text)


class SuperFencesBlockPreprocessor(Preprocessor):
    """
    Preprocessor to find fenced code blocks.

    Because this is done as a preprocessor, it might be too greedy.
    We will stash the blocks code and restore if we mistakenly processed
    text from an indented code block.
    """

    CODE_WRAP = '<pre%s><code%s>%s</code></pre>'

    def __init__(self, md):
        """Initialize."""

        super(SuperFencesBlockPreprocessor, self).__init__(md)
        self.tab_len = self.md.tab_length
        self.checked_hl_settings = False
        self.codehilite_conf = {}

    def normalize_ws(self, text):
        """Normalize whitespace."""

        return text.expandtabs(self.tab_len)

    def rebuild_block(self, lines):
        """Dedent the fenced block lines."""

        return '\n'.join([line[self.ws_virtual_len:] for line in lines])

    def get_hl_settings(self):
        """Check for CodeHilite extension to get its configurations."""

        if not self.checked_hl_settings:
            self.checked_hl_settings = True
            self.highlight_code = self.config['highlight_code']

            config = None
            self.highlighter = None
            for ext in self.md.registeredExtensions:
                try:
                    config = getattr(ext, "get_pymdownx_highlight_settings")()
                    self.highlighter = getattr(ext, "get_pymdownx_highlighter")()
                    break
                except AttributeError:
                    pass

            css_class = self.config['css_class']
            self.css_class = css_class if css_class else config['css_class']

            self.extend_pygments_lang = config.get('extend_pygments_lang', None)
            self.guess_lang = config['guess_lang']
            self.pygments_style = config['pygments_style']
            self.use_pygments = config['use_pygments']
            self.noclasses = config['noclasses']
            self.linenums = config['linenums']
            self.linenums_style = config.get('linenums_style', 'table')
            self.linenums_special = config.get('linenums_special', -1)

    def clear(self):
        """Reset the class variables."""

        self.ws = None
        self.ws_len = 0
        self.ws_virtual_len = 0
        self.fence = None
        self.lang = None
        self.quote_level = 0
        self.code = []
        self.empty_lines = 0
        self.fence_end = None
        self.tab = None
        self.options = {}

    def eval_fence(self, ws, content, start, end):
        """Evaluate a normal fence."""

        if (ws + content).strip() == '':
            # Empty line is okay
            self.empty_lines += 1
            self.code.append(ws + content)
        elif len(ws) != self.ws_virtual_len and content != '':
            # Not indented enough
            self.clear()
        elif self.fence_end.match(content) is not None and not content.startswith((' ', '\t')):
            # End of fence
            self.process_nested_block(ws, content, start, end)
        else:
            # Content line
            self.empty_lines = 0
            self.code.append(ws + content)

    def eval_quoted(self, ws, content, quote_level, start, end):
        """Evaluate fence inside a blockquote."""

        if quote_level > self.quote_level:
            # Quote level exceeds the starting quote level
            self.clear()
        elif quote_level <= self.quote_level:
            if content == '':
                # Empty line is okay
                self.code.append(ws + content)
                self.empty_lines += 1
            elif len(ws) < self.ws_len:
                # Not indented enough
                self.clear()
            elif self.empty_lines and quote_level < self.quote_level:
                # Quote levels don't match and we are signified
                # the end of the block with an empty line
                self.clear()
            elif self.fence_end.match(content) is not None:
                # End of fence
                self.process_nested_block(ws, content, start, end)
            else:
                # Content line
                self.empty_lines = 0
                self.code.append(ws + content)

    def get_tab(self, code, title):
        """Wrap code in tab div."""

        return TAB % {'code': code.replace('%', '%%'), 'title': title}

    def process_nested_block(self, ws, content, start, end):
        """Process the contents of the nested block."""

        self.last = ws + self.normalize_ws(content)
        code = None
        for entry in reversed(self.extension.superfences):
            if entry["test"](self.lang):
                code = entry["formatter"](self.rebuild_block(self.code), self.lang, self.options, self.md)
                if self.tab is not None:
                    code = self.get_tab(code, self.tab)
                break

        if code is not None:
            self._store(self.normalize_ws('\n'.join(self.code)) + '\n', code, start, end)
        self.clear()

    def parse_hl_lines(self, hl_lines):
        """Parse the lines to highlight."""

        return list(map(int, hl_lines.strip().split())) if hl_lines else []

    def parse_line_start(self, linestart):
        """Parse line start."""

        return int(linestart) if linestart else -1

    def parse_line_step(self, linestep):
        """Parse line start."""

        step = int(linestep) if linestep else -1

        return step if step > 1 else -1

    def parse_line_special(self, linespecial):
        """Parse line start."""

        return int(linespecial) if linespecial else -1

    def parse_fence_line(self, line):
        """Parse fence line."""

        ws_len = 0
        ws_virtual_len = 0
        ws = []
        index = 0
        for c in line:
            if ws_virtual_len >= self.ws_virtual_len:
                break
            if c not in PREFIX_CHARS:
                break
            ws_len += 1
            if c == '\t':
                tab_size = self.tab_len - (index % self.tab_len)
                ws_virtual_len += tab_size
                ws.append(' ' * tab_size)
            else:
                tab_size = 1
                ws_virtual_len += 1
                ws.append(c)
            index += tab_size

        return ''.join(ws), line[ws_len:]

    def parse_whitespace(self, line):
        """Parse the whitespace (blockquote syntax is counted as well)."""

        self.ws_len = 0
        self.ws_virtual_len = 0
        ws = []
        for c in line:
            if c not in PREFIX_CHARS:
                break
            self.ws_len += 1
            ws.append(c)

        ws = self.normalize_ws(''.join(ws))
        self.ws_virtual_len = len(ws)

        return ws

    def parse_options(self, string):
        """Get options."""

        okay = True

        self.options = {}
        for m in RE_OPTIONS.finditer(string):
            key = m.group('key')
            value = m.group('value')
            if value is None:
                value = True
            self.options[key] = value

        # Global options (remove as we handle them)
        if 'tab' in self.options:
            self.tab = self.options['tab']
            if not self.tab or self.tab is True:
                self.tab = self.lang
            if not self.tab:
                self.tab = '%(tab_title)s'
            del self.options['tab']

        # Run per language validator
        for entry in reversed(self.extension.superfences):
            if entry["test"](self.lang):
                validator = entry.get("validator", functools.partial(_validator, validator=default_validator))
                okay = validator(self.lang, self.options)
                break

        return okay

    def search_nested(self, lines):
        """Search for nested fenced blocks."""

        count = 0
        for line in lines:
            # Strip carriage returns if the lines end with them.
            # This is necessary since we are handling preserved tabs
            # Before whitespace normalization.
            line = line.rstrip('\r')
            if self.fence is None:
                ws = self.parse_whitespace(line)

                # Found the start of a fenced block.
                m = RE_NESTED_FENCE_START.match(line, self.ws_len)
                if m is not None:
                    start = count
                    self.first = ws + self.normalize_ws(m.group(0))
                    self.ws = ws
                    self.quote_level = self.ws.count(">")
                    self.empty_lines = 0
                    self.fence = m.group('fence')
                    self.lang = m.group('lang')
                    if self.parse_options(m.group('options')):
                        self.fence_end = re.compile(NESTED_FENCE_END % self.fence)
                    else:
                        # Option parsing failed, abandon fence
                        self.clear()
            else:
                # Evaluate lines
                # - Determine if it is the ending line or content line
                # - If is a content line, make sure it is all indented
                #   with the opening and closing lines (lines with just
                #   whitespace will be stripped so those don't matter).
                # - When content lines are inside blockquotes, make sure
                #   the nested block quote levels make sense according to
                #   blockquote rules.
                ws, content = self.parse_fence_line(line)

                end = count + 1
                quote_level = ws.count(">")

                if self.quote_level:
                    # Handle blockquotes
                    self.eval_quoted(ws, content, quote_level, start, end)
                elif quote_level == 0:
                    # Handle all other cases
                    self.eval_fence(ws, content, start, end)
                else:
                    # Looks like we got a blockquote line
                    # when not in a blockquote.
                    self.clear()

            count += 1

        return self.reassemble(lines)

    def reassemble(self, lines):
        """Reassemble text."""

        # Now that we are done iterating the lines,
        # let's replace the original content with the
        # fenced blocks.
        while len(self.stack):
            fenced, start, end = self.stack.pop()
            lines = lines[:start] + [fenced] + lines[end:]
        return lines

    def highlight(self, src, language, options, md):
        """
        Syntax highlight the code block.

        If configuration is not empty, then the CodeHilite extension
        is enabled, so we call into it to highlight the code.
        """

        # Default format options
        linestep = None
        linestart = None
        linespecial = None
        hl_lines = None
        if 'hl_lines' in options:
            m = RE_HL_LINES.match(options['hl_lines'])
            hl_lines = m.group('hl_lines')
        if 'linenums' in options:
            m = RE_LINENUMS.match(options['linenums'])
            linestart = m.group('linestart')
            linestep = m.group('linestep')
            linespecial = m.group('linespecial')

        if self.highlight_code:
            linestep = self.parse_line_step(linestep)
            linestart = self.parse_line_start(linestart)
            linespecial = self.parse_line_special(linespecial)
            hl_lines = self.parse_hl_lines(hl_lines)

            el = self.highlighter(
                guess_lang=self.guess_lang,
                pygments_style=self.pygments_style,
                use_pygments=self.use_pygments,
                noclasses=self.noclasses,
                linenums=self.linenums,
                linenums_style=self.linenums_style,
                linenums_special=self.linenums_special,
                extend_pygments_lang=self.extend_pygments_lang
            ).highlight(
                src,
                language,
                self.css_class,
                hl_lines=hl_lines,
                linestart=linestart,
                linestep=linestep,
                linespecial=linespecial
            )
        else:
            # Format as a code block.
            el = self.CODE_WRAP % ('', '', _escape(src))
        return el

    def _store(self, source, code, start, end):
        """
        Store the fenced blocks in the stack to be replaced when done iterating.

        Store the original text in case we need to restore if we are too greedy.
        """
        # Save the fenced blocks to add once we are done iterating the lines
        placeholder = self.md.htmlStash.store(code)
        self.stack.append(('%s%s' % (self.ws, placeholder), start, end))
        if not self.disabled_indented:
            # If an indented block consumes this placeholder,
            # we can restore the original source
            self.extension.stash.store(
                placeholder[1:-1],
                "%s\n%s%s" % (self.first, self.normalize_ws(source), self.last),
                self.ws_virtual_len
            )

    def reindent(self, text, pos, level):
        """Reindent the code to where it is supposed to be."""

        indented = []
        for line in text.split('\n'):
            index = pos - level
            indented.append(line[index:])
        return indented

    def restore_raw_text(self, lines):
        """Revert a prematurely converted fenced block."""

        new_lines = []
        for line in lines:
            m = FENCED_BLOCK_RE.match(line)
            if m:
                key = m.group(2)
                indent_level = len(m.group(1))
                original = None
                original, pos = self.extension.stash.get(key)
                if original is not None:
                    code = self.reindent(original, pos, indent_level)
                    new_lines.extend(code)
                    self.extension.stash.remove(key)
                if original is None:  # pragma: no cover
                    # Too much work to test this. This is just a fall back in case
                    # we find a placeholder, and we went to revert it and it wasn't in our stash.
                    # Most likely this would be caused by someone else. We just want to put it
                    # back in the block if we can't revert it.  Maybe we can do a more directed
                    # unit test in the future.
                    new_lines.append(line)
            else:
                new_lines.append(line)
        return new_lines

    def run(self, lines):
        """Search for fenced blocks."""

        self.get_hl_settings()
        self.clear()
        self.stack = []
        self.disabled_indented = self.config.get("disable_indented_code_blocks", False)
        self.preserve_tabs = self.config.get("preserve_tabs", False)

        if self.preserve_tabs:
            lines = self.restore_raw_text(lines)
        return self.search_nested(lines)


class SuperFencesRawBlockPreprocessor(SuperFencesBlockPreprocessor):
    """Special class for preserving tabs before normalizing whitespace."""

    def process_nested_block(self, ws, content, start, end):
        """Process the contents of the nested block."""

        self.last = ws + self.normalize_ws(content)
        code = '\n'.join(self.code)
        self._store(code + '\n', code, start, end)
        self.clear()

    def _store(self, source, code, start, end):
        """
        Store the fenced blocks in the stack to be replaced when done iterating.

        Store the original text in case we need to restore if we are too greedy.
        """
        # Just get a placeholder, we won't ever actually retrieve this source
        placeholder = self.md.htmlStash.store('')
        self.stack.append(('%s%s' % (self.ws, placeholder), start, end))
        # Here is the source we'll actually retrieve.
        self.extension.stash.store(
            placeholder[1:-1],
            "%s\n%s%s" % (self.first, source, self.last),
            self.ws_virtual_len
        )

    def reassemble(self, lines):
        """Reassemble text."""

        # Now that we are done iterating the lines,
        # let's replace the original content with the
        # fenced blocks.
        while len(self.stack):
            fenced, start, end = self.stack.pop()
            lines = lines[:start] + [fenced.replace(md_util.STX, SOH, 1)[:-1] + EOT] + lines[end:]
        return lines

    def run(self, lines):
        """Search for fenced blocks."""

        self.clear()
        self.stack = []
        self.disabled_indented = self.config.get("disable_indented_code_blocks", False)
        return self.search_nested(lines)


class SuperFencesCodeBlockProcessor(CodeBlockProcessor):
    """Process indented code blocks to see if we accidentally processed its content as a fenced block."""

    def test(self, parent, block):
        """Test method that is one day to be deprecated."""

        return True

    def reindent(self, text, pos, level):
        """Reindent the code to where it is supposed to be."""

        indented = []
        for line in text.split('\n'):
            index = pos - level
            indented.append(line[index:])
        return '\n'.join(indented)

    def revert_greedy_fences(self, block):
        """Revert a prematurely converted fenced block."""

        new_block = []
        for line in block.split('\n'):
            m = FENCED_BLOCK_RE.match(line)
            if m:
                key = m.group(2)
                indent_level = len(m.group(1))
                original = None
                original, pos = self.extension.stash.get(key)
                if original is not None:
                    code = self.reindent(original, pos, indent_level)
                    new_block.append(code)
                    self.extension.stash.remove(key)
                if original is None:  # pragma: no cover
                    # Too much work to test this. This is just a fall back in case
                    # we find a placeholder, and we went to revert it and it wasn't in our stash.
                    # Most likely this would be caused by someone else. We just want to put it
                    # back in the block if we can't revert it.  Maybe we can do a more directed
                    # unit test in the future.
                    new_block.append(line)
            else:
                new_block.append(line)
        return '\n'.join(new_block)

    def run(self, parent, blocks):
        """Look for and parse code block."""

        handled = False

        if not self.config.get("disable_indented_code_blocks", False):
            handled = CodeBlockProcessor.test(self, parent, blocks[0])
            if handled:
                if self.config.get("nested", True):
                    blocks[0] = self.revert_greedy_fences(blocks[0])
                handled = CodeBlockProcessor.run(self, parent, blocks) is not False
        return handled


def makeExtension(*args, **kwargs):
    """Return extension."""

    return SuperFencesCodeExtension(*args, **kwargs)
