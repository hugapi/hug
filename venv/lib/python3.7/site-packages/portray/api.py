"""This module defines the programmatic API that can be used to interact with `portray`
   to generate and view documentation.

   If you want to extend `portray` or use it directly from within Python - this is the place
   to start.
"""
import os
import webbrowser
from typing import Dict, Optional, Union

import hug
import mkdocs.commands.gh_deploy

from portray import config, logo, render


def as_html(
    directory: str = "",
    config_file: str = "pyproject.toml",
    output_dir: str = "site",
    overwrite: bool = False,
    modules: list = None,
) -> None:
    """Produces HTML documentation for a Python project placing it into output_dir.

       - *directory*: The root folder of your project.
       - *config_file*: The [TOML](https://github.com/toml-lang/toml#toml)
         formatted config file you wish to use.
       - *output_dir*: The directory to place the generated HTML into.
       - *overwrite*: If set to `True` any existing documentation output will be removed
         before generating new documentation. Otherwise, if documentation exists in the
         specified `output_dir` the command will fail with a `DocumentationAlreadyExists`
         exception.
       - *modules*: One or more modules to render reference documentation for
    """
    directory = directory if directory else os.getcwd()
    render.documentation(
        project_configuration(directory, config_file, modules=modules, output_dir=output_dir),
        overwrite=overwrite,
    )
    print(logo.ascii_art)
    print(f"Documentation successfully generated into `{os.path.abspath(output_dir)}` !")


def in_browser(
    directory: str = "",
    config_file: str = "pyproject.toml",
    port: int = None,
    host: str = None,
    modules: list = None,
) -> None:
    """Opens your default webbrowser pointing to a locally started development webserver enabling
       you to browse documentation locally

       - *directory*: The root folder of your project.
       - *config_file*: The [TOML](https://github.com/toml-lang/toml#toml) formatted
         config file you wish to use.
       - *port*: The port to expose your documentation on (defaults to: `8000`)
       - *host*: The host to expose your documentation on (defaults to `"127.0.0.1"`)
       - *modules*: One or more modules to render reference documentation for
    """
    directory = directory if directory else os.getcwd()
    server(directory=directory, config_file=config_file, open_browser=True, modules=modules)


def server(
    directory: str = "",
    config_file: str = "pyproject.toml",
    open_browser: bool = False,
    port: int = None,
    host: str = None,
    modules: list = None,
) -> None:
    """Runs a development webserver enabling you to browse documentation locally.

       - *directory*: The root folder of your project.
       - *config_file*: The [TOML](https://github.com/toml-lang/toml#toml) formatted
         config file you wish to use.
       - *open_browser*: If true a browser will be opened pointing at the documentation server
       - *port*: The port to expose your documentation on (defaults to: `8000`)
       - *host*: The host to expose your documentation on (defaults to `"127.0.0.1"`)
       - *modules*: One or more modules to render reference documentation for
    """
    directory = directory if directory else os.getcwd()
    api = hug.API("Doc Server")

    project_config = project_configuration(directory, config_file, modules=modules)
    with render.documentation_in_temp_folder(project_config) as doc_folder:

        @hug.static("/", api=api)
        def my_static_dirs():  # pragma: no cover
            return (doc_folder,)

        @hug.startup(api=api)
        def custom_startup(*args, **kwargs):  # pragma: no cover
            print(logo.ascii_art)
            if open_browser:
                webbrowser.open_new(f"http://{project_config['host']}:{project_config['port']}")

        api.http.serve(
            host=host or project_config["host"],
            port=port or project_config["port"],
            no_documentation=True,
            display_intro=False,
        )


def project_configuration(
    directory: str = "",
    config_file: str = "pyproject.toml",
    modules: list = None,
    output_dir: str = "site",
) -> dict:
    """Returns the configuration associated with a project.

        - *directory*: The root folder of your project.
        - *config_file*: The [TOML](https://github.com/toml-lang/toml#toml) formatted
          config file you wish to use.
        - *modules*: One or more modules to include in the configuration for reference rendering
    """
    overrides: Dict[str, Union[str, list]] = {}
    if modules:
        overrides["modules"] = modules
    if output_dir:
        overrides["output_dir"] = output_dir
    directory = directory if directory else os.getcwd()
    return config.project(directory=directory, config_file=config_file, **overrides)


def on_github_pages(
    directory: str = "",
    config_file: str = "pyproject.toml",
    message: str = None,
    force: bool = False,
    ignore_version: bool = False,
    modules: list = None,
) -> None:
    """Regenerates and deploys the documentation to GitHub pages.

        - *directory*: The root folder of your project.
        - *config_file*: The [TOML](https://github.com/toml-lang/toml#toml) formatted
          config file you wish to use.
        - *message*: The commit message to use when uploading your documentation.
        - *force*: Force the push to the repository.
        - *ignore_version*: Ignore check that build is not being deployed with an old version.
        - *modules*: One or more modules to render reference documentation for
    """
    directory = directory if directory else os.getcwd()
    project_config = project_configuration(directory, config_file, modules)
    with render.documentation_in_temp_folder(project_config):
        conf = render._mkdocs_config(project_config["mkdocs"])
        conf.config_file_path = directory
        mkdocs.commands.gh_deploy.gh_deploy(
            conf, message=message, force=force, ignore_version=ignore_version
        )
        print(logo.ascii_art)
        print("Documentation successfully generated and pushed!")
