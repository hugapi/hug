"""This module defines the programmatic API that can be used to interact with `pdocs`
   to generate and view documentation from Python source code.

   If you want to extend `pdocs` or use it directly from within Python - this is the place
   to start.
"""
import os
import pathlib
import sys
import tempfile
import webbrowser

import hug

import pdocs.extract
import pdocs.logo
import pdocs.render
import pdocs.static
from pdocs import defaults


def as_html(
    modules: list,
    output_dir: str = defaults.HTML_OUTPUT_DIRECTORY,
    overwrite: bool = False,
    external_links: bool = False,
    exclude_source: bool = False,
    link_prefix: str = "",
    template_dir: str = "",
) -> str:
    """Produces HTML formatted output into the specified output_dir.

    - *modules*: One or more python module names. These may be import paths resolvable in the
      current environment, or file paths to a Python module or package.
    - *output_dir*: The directory to output HTML files to.
    - *overwrite*: If set, will overwrites any existing files in the output location.
    - *external_links*: When set, identifiers to external modules are turned into links.
    - *exclude_source*: When set, source code will not be viewable in the generated HTML.
    - *link_prefix*: A prefix to use for every link in the generated documentation otherwise
      relative links will be used.
    - *template_dir*: Specify a directory containing override Mako templates.

    Returns the `output_dir` on success.
    """
    if template_dir:
        pdocs.render.tpl_lookup.directories.insert(0, template_dir)

    roots = _get_root_modules(modules)
    destination = _destination(output_dir, roots, overwrite)
    pdocs.static.html_out(
        destination,
        roots,
        external_links=external_links,
        source=not exclude_source,
        link_prefix=link_prefix,
    )
    return output_dir


def as_markdown(
    modules: list,
    output_dir: str = defaults.MARKDOWN_OUTPUT_DIRECTORY,
    overwrite: bool = False,
    exclude_source: bool = False,
    template_dir: str = "",
) -> str:
    """Produces Markdown formatted output into the specified output_dir.

    - *modules*: One or more python module names. These may be import paths resolvable in the
      current environment, or file paths to a Python module or package.
    - *output_dir*: The directory to output HTML files to.
    - *overwrite*: If set, will overwrites any existing files in the output location.
    - *exclude_source*: When set, source code will not be viewable in the generated Markdown.
    - *template_dir*: Specify a directory containing override Mako templates.

    Returns the `output_dir` on success.
    """
    if template_dir:
        pdocs.render.tpl_lookup.directories.insert(0, template_dir)

    roots = _get_root_modules(modules)
    destination = _destination(output_dir, roots, overwrite)
    pdocs.static.md_out(destination, roots, source=not exclude_source)
    return output_dir


def server(
    modules: list,
    external_links: bool = False,
    exclude_source: bool = False,
    link_prefix: str = "",
    template_dir: str = "",
    open_browser: bool = False,
    port: int = defaults.SERVER_PORT,
    host: str = defaults.SERVER_HOST,
) -> None:
    """Runs a development webserver enabling you to browse documentation locally.

    - *modules*: One or more python module names. These may be import paths resolvable in the
      current environment, or file paths to a Python module or package.
    - *external_links*: When set, identifiers to external modules are turned into links.
    - *exclude_source*: When set, source code will not be viewable in the generated HTML.
    - *link_prefix*: A prefix to use for every link in the generated documentation otherwise
      relative links will be used.
    - *template_dir*: Specify a directory containing override Mako templates.
    - *open_browser*: If true a browser will be opened pointing at the documentation server
    - *port*: The port to expose your documentation on (defaults to: `8000`)
    - *host*: The host to expose your documentation on (defaults to `"127.0.0.1"`)
    """
    with tempfile.TemporaryDirectory() as output_dir:
        as_html(
            modules,
            overwrite=True,
            output_dir=output_dir,
            external_links=external_links,
            template_dir=template_dir,
        )

        if len(modules) == 1:
            output_dir = os.path.join(output_dir, modules[0])

        api = hug.API("Doc Server")

        @hug.static("/", api=api)
        def my_static_dirs():  # pragma: no cover
            return (output_dir,)

        @hug.startup(api=api)
        def custom_startup(*args, **kwargs):  # pragma: no cover
            print(pdocs.logo.ascii_art)
            if open_browser:
                webbrowser.open_new(f"http://{host}:{port}")

        api.http.serve(host=host, port=port, no_documentation=True, display_intro=False)


def _get_root_modules(module_names):
    if not module_names:
        sys.exit("Please provide one or more modules")
    try:
        return [pdocs.extract.extract_module(module_name) for module_name in module_names]
    except pdocs.extract.ExtractError as error:
        sys.exit(str(error))


def _destination(directory, root_modules, overwrite):
    destination = pathlib.Path(directory)
    if not overwrite and pdocs.static.would_overwrite(destination, root_modules):
        sys.exit("Rendering would overwrite files, but --overwrite is not set")
    return destination
