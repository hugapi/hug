import os
import re
import sys

import markdown
import pygments
import pygments.formatters
import pygments.lexers

import pdocs.doc
import pdocs.render
from pdocs import defaults

# From language reference, but adds '.' to allow fully qualified names.
pyident = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]+$")
indent = re.compile(r"^\s*")

_markdown = markdown.Markdown(
    output_format="html5",
    extensions=defaults.MARKDOWN_EXTENSIONS,
    extension_configs=defaults.MARKDOWN_EXTENSION_CONFIGS,
)


def _markdown_render(text):
    return _markdown.reset().convert(text)


def decode(s):
    if sys.version_info[0] < 3 and isinstance(s, str):
        return s.decode("utf-8", "ignore")
    return s


def ident(s):
    return '<span class="ident">%s</span>' % s


def sourceid(dobj):
    return "source-%s" % dobj.refname


def clean_source_lines(lines):
    """
  Cleans the source code so that pygments can render it well.

  Returns one string with all of the source code.
  """
    base_indent = len(indent.match(lines[0]).group(0))
    base_indent = 0
    for line in lines:
        if len(line.strip()) > 0:
            base_indent = len(indent.match(lines[0]).group(0))
            break
    lines = [line[base_indent:] for line in lines]

    if sys.version_info[0] < 3:
        pylex = pygments.lexers.PythonLexer()
    else:
        pylex = pygments.lexers.Python3Lexer()

    htmlform = pygments.formatters.HtmlFormatter(cssclass="codehilite")
    return pygments.highlight("".join(lines), pylex, htmlform)


def linkify(parent, match, link_prefix):
    matched = match.group(0)
    ident = matched[1:-1]
    name, url = lookup(parent, ident, link_prefix)
    if name is None:
        return matched
    return "[`%s`](%s)" % (name, url)


def mark(text, module_list=None, linky=True):
    if linky:
        text, _ = re.subn("\b\n\b", " ", text)
    return _markdown_render(text.strip())


def glimpse(s, length=100):
    if len(s) < length:
        return s
    return s[0:length] + "..."


def module_url(parent, m, link_prefix):
    """
        Returns a URL for `m`, which must be an instance of `Module`.
        Also, `m` must be a submodule of the module being documented.

        Namely, '.' import separators are replaced with '/' URL
        separators. Also, packages are translated as directories
        containing `index.html` corresponding to the `__init__` module,
        while modules are translated as regular HTML files with an
        `.m.html` suffix. (Given default values of
        `pdoc.html_module_suffix` and `pdoc.html_package_name`.)
    """
    if parent.name == m.name:
        return ""

    base = m.name.replace(".", "/")
    if len(link_prefix) == 0:
        base = os.path.relpath(base, parent.name.replace(".", "/"))
    url = base[len("../") :] if base.startswith("../") else "" if base == ".." else base
    if m.submodules:
        index = pdocs.render.html_package_name
        url = url + "/" + index if url else index
    else:
        url += pdocs.render.html_module_suffix
    return link_prefix + url


def external_url(refname):
    """
        Attempts to guess an absolute URL for the external identifier
        given.

        Note that this just returns the refname with an ".ext" suffix.
        It will be up to whatever is interpreting the URLs to map it
        to an appropriate documentation page.
    """
    return "/%s.ext" % refname


def is_external_linkable(name):
    return pyident.match(name) and "." in name


def lookup(module, refname, link_prefix):
    """
        Given a fully qualified identifier name, return its refname
        with respect to the current module and a value for a `href`
        attribute. If `refname` is not in the public interface of
        this module or its submodules, then `None` is returned for
        both return values. (Unless this module has enabled external
        linking.)

        In particular, this takes into account sub-modules and external
        identifiers. If `refname` is in the public API of the current
        module, then a local anchor link is given. If `refname` is in the
        public API of a sub-module, then a link to a different page with
        the appropriate anchor is given. Otherwise, `refname` is
        considered external and no link is used.
    """
    d = module.find_ident(refname)
    if isinstance(d, pdocs.doc.External):
        if is_external_linkable(refname):
            return d.refname, external_url(d.refname)
        else:
            return None, None
    if isinstance(d, pdocs.doc.Module):
        return d.refname, module_url(module, d, link_prefix)
    if module.is_public(d.refname):
        return d.name, "#%s" % d.refname
    return d.refname, "%s#%s" % (module_url(module, d.module, link_prefix), d.refname)


def link(parent, refname, link_prefix):
    """
        A convenience wrapper around `href` to produce the full
        `a` tag if `refname` is found. Otherwise, plain text of
        `refname` is returned.
    """
    name, url = lookup(parent, refname, link_prefix)
    if name is None:
        return refname
    return '<a href="%s">%s</a>' % (url, name)
