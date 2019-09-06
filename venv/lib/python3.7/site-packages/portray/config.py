"""Defines the configuration defaults and load functions used by `portray`"""
import ast
import os
import warnings
from typing import Any, Dict, List, Union, cast
from urllib import parse

import mkdocs.config as _mkdocs_config
import mkdocs.exceptions as _mkdocs_exceptions
from git import Repo
from toml import load as toml_load

import _ast
from portray.exceptions import NoProjectFound

PORTRAY_DEFAULTS = {
    "docs_dir": "docs",
    "output_dir": "site",
    "port": 8000,
    "host": "127.0.0.1",
    "append_directory_to_python_path": True,
    "labels": {"Cli": "CLI", "Api": "API", "Http": "HTTP", "Pypi": "PyPI"},
}

MKDOCS_DEFAULTS: Dict[str, Any] = {
    "site_name": os.path.basename(os.getcwd()),
    "config_file_path": os.getcwd(),
    "theme": {
        "name": "material",
        "palette": {"primary": "green", "accent": "lightgreen"},
        "custom_dir": os.path.join(os.path.dirname(__file__), "mkdocs_templates"),
    },
    "markdown_extensions": [
        "admonition",
        "codehilite",
        "extra",
        "pymdownx.details",
        "pymdownx.highlight",
    ],
}

PDOCS_DEFAULTS: Dict = {
    "overwrite": True,
    "exclude_source": False,
    "template_dir": os.path.join(os.path.dirname(__file__), "pdocs_templates"),
}


def project(directory: str, config_file: str, **overrides) -> dict:
    """Returns back the complete configuration - including all sub configuration components
       defined below that `portray` was able to determine for the project
    """
    if not (
        os.path.isfile(os.path.join(directory, config_file))
        or os.path.isfile(os.path.join(directory, "setup.py"))
        or "modules" in overrides
    ):
        raise NoProjectFound(directory)

    project_config: Dict[str, Any] = {**PORTRAY_DEFAULTS, "directory": directory}
    if os.path.isfile(os.path.join(directory, "setup.py")):
        project_config.update(setup_py(os.path.join(directory, "setup.py")))

    project_config.update(toml(os.path.join(directory, config_file)))
    project_config.update(overrides)

    project_config.setdefault("modules", [os.path.basename(os.getcwd())])
    project_config.setdefault("pdocs", {}).setdefault("modules", project_config["modules"])

    project_config["mkdocs"] = mkdocs(directory, **project_config.get("mkdocs", {}))
    if "pdoc3" in project_config:
        warnings.warn(
            "pdoc3 config usage is deprecated in favor of pdocs. "
            "pdoc3 section will be ignored. ",
            DeprecationWarning,
        )
    project_config["pdocs"] = pdocs(directory, **project_config.get("pdocs", {}))
    return project_config


def setup_py(location: str) -> dict:
    """Returns back any configuration info we are able to determine from a setup.py file"""
    setup_config = {}
    try:
        with open(location) as setup_py_file:
            for node in ast.walk(ast.parse(setup_py_file.read())):
                if (
                    type(node) == _ast.Call
                    and type(getattr(node, "func", None)) == _ast.Name
                    and node.func.id == "setup"  # type: ignore
                ):
                    for keyword in node.keywords:  # type: ignore
                        if keyword.arg == "packages":
                            setup_config["modules"] = ast.literal_eval(keyword.value)
                            break
                    break
    except Exception as error:
        warnings.warn(f"Error ({error}) occurred trying to parse setup.py file: {location}")

    return setup_config


def toml(location: str) -> dict:
    """Returns back the configuration found within the projects
       [TOML](https://github.com/toml-lang/toml#toml) config (if there is one).

       Generally this is a `pyproject.toml` file at the root of the project
       with a `[tool.portray]` section defined.
    """
    try:
        toml_config = toml_load(location)
        tools = toml_config.get("tool", {})

        config = tools.get("portray", {})
        config["file"] = location

        if "modules" not in config:
            if "poetry" in tools and "name" in tools["poetry"]:
                config["modules"] = [tools["poetry"]["name"]]
            elif (
                "flit" in tools
                and "metadata" in tools["flit"]
                and "module" in tools["flit"]["metadata"]
            ):
                config["modules"] = [tools["flit"]["metadata"]["module"]]

        return config
    except Exception:
        warnings.warn(f"No {location} config file found")

    return {}


def repository(directory: str) -> dict:
    """Returns back any information that can be determined by introspecting the projects git repo
       (if there is one).
    """
    config = {}
    try:
        repo_url = Repo(directory).remotes.origin.url
        if "http" in repo_url:
            config["repo_url"] = repo_url
            config["repo_name"] = parse.urlsplit(repo_url).path.rstrip(".git").lstrip("/")
    except Exception:
        config = {}

    if not config:
        warnings.warn("Unable to identify `repo_name` and `repo_url` automatically")

    return config


def mkdocs(directory: str, **overrides) -> dict:
    """Returns back the configuration that will be used when running mkdocs"""
    mkdocs_config: Dict[str, Any] = {**MKDOCS_DEFAULTS, **repository(directory), **overrides}
    theme = mkdocs_config["theme"]
    if theme["name"].lower() == "material" and "custom_dir" not in theme:
        theme["custom_dir"] = MKDOCS_DEFAULTS["theme"]["custom_dir"]

    return mkdocs_config


def pdocs(directory: str, **overrides) -> dict:
    """Returns back the configuration that will be used when running pdocs"""
    defaults = {**PDOCS_DEFAULTS}
    defaults.update(overrides)
    return defaults
