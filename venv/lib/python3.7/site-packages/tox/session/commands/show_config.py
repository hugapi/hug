import sys
from collections import OrderedDict

from six import StringIO
from six.moves import configparser

from tox import reporter

DO_NOT_SHOW_CONFIG_ATTRIBUTES = (
    "interpreters",
    "envconfigs",
    "envlist",
    "pluginmanager",
    "envlist_explicit",
)


def show_config(config):
    parser = configparser.ConfigParser()

    if not config.envlist_explicit or reporter.verbosity() >= reporter.Verbosity.INFO:
        tox_info(config, parser)
        version_info(parser)
    tox_envs_info(config, parser)

    content = StringIO()
    parser.write(content)
    value = content.getvalue().rstrip()
    reporter.verbosity0(value)


def tox_envs_info(config, parser):
    if config.envlist_explicit:
        env_list = config.envlist
    elif config.option.listenvs:
        env_list = config.envlist_default
    else:
        env_list = list(config.envconfigs.keys())
    for name in env_list:
        env_config = config.envconfigs[name]
        values = OrderedDict(
            (attr.name, str(getattr(env_config, attr.name)))
            for attr in config._parser._testenv_attr
        )
        section = "testenv:{}".format(name)
        set_section(parser, section, values)


def tox_info(config, parser):
    info = OrderedDict(
        (i, str(getattr(config, i)))
        for i in sorted(dir(config))
        if not i.startswith("_") and i not in DO_NOT_SHOW_CONFIG_ATTRIBUTES
    )
    info["host_python"] = sys.executable
    set_section(parser, "tox", info)


def version_info(parser):
    import pkg_resources

    versions = OrderedDict()
    visited = set()
    to_visit = {"tox"}
    while to_visit:
        current = to_visit.pop()
        visited.add(current)
        current_dist = pkg_resources.get_distribution(current)
        to_visit.update(i.name for i in current_dist.requires() if i.name not in visited)
        versions[current] = current_dist.version
    set_section(parser, "tox:versions", versions)


def set_section(parser, section, values):
    parser.add_section(section)
    for key, value in values.items():
        parser.set(section, key, value)
