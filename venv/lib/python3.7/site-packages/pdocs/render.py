import os.path
import re
import typing

from mako.exceptions import TopLevelLookupException
from mako.lookup import TemplateLookup

import pdocs.doc

html_module_suffix = ".html"
html_package_name = "index.html"
"""
The file name to use for a package's `__init__.py` module.
"""

_template_path = [os.path.join(os.path.dirname(__file__), "templates")]
"""
A list of paths to search for Mako templates used to produce the
plain text and HTML output. Each path is tried until a template is
found.
"""

tpl_lookup = TemplateLookup(
    directories=_template_path, cache_args={"cached": True, "cache_type": "memory"}
)
"""
A `mako.lookup.TemplateLookup` object that knows how to load templates
from the file system. You may add additional paths by modifying the
object's `directories` attribute.
"""


def _get_tpl(name):
    """
    Returns the Mako template with the given name. If the template cannot be
    found, a nicer error message is displayed.
    """
    try:
        t = tpl_lookup.get_template(name)
    except TopLevelLookupException:
        locs = [os.path.join(p, name.lstrip("/")) for p in _template_path]
        raise IOError(2, "No template at any of: %s" % ", ".join(locs))
    return t


def html_index(roots: typing.Sequence[pdocs.doc.Module], link_prefix: str = "/") -> str:
    """
        Render an HTML module index.
    """
    t = _get_tpl("/html_index.mako")
    t = t.render(roots=roots, link_prefix=link_prefix)
    return t.strip()


def html_module(
    mod: pdocs.doc.Module, external_links: bool = False, link_prefix: str = "/", source: bool = True
) -> str:
    """
    Returns the documentation for the module `module_name` in HTML
    format. The module must be importable.

    If `external_links` is `True`, then identifiers to external modules
    are always turned into links.

    If `link_prefix` is `True`, then all links will have that prefix.
    Otherwise, links are always relative.

    If `source` is `True`, then source code will be retrieved for
    every Python object whenever possible. This can dramatically
    decrease performance when documenting large modules.
    """
    t = _get_tpl("/html_module.mako")
    t = t.render(
        module=mod, external_links=external_links, link_prefix=link_prefix, show_source_code=source
    )
    return t.strip()


def text(mod: pdocs.doc.Module, source: bool = True) -> str:
    """Returns the documentation for the module `module_name` in plain
    text format. The module must be importable.

    *source* - If set to True (the default) source will be included in the produced output.
    """
    t = _get_tpl("/text.mako")
    text, _ = re.subn("\n\n\n+", "\n\n", t.render(module=mod, show_source_code=source).strip())
    return text
