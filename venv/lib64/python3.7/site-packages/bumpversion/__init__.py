# -*- coding: utf-8 -*-

from __future__ import unicode_literals

try:
    from configparser import RawConfigParser, NoOptionError
except ImportError:
    from ConfigParser import RawConfigParser, NoOptionError

try:
    from StringIO import StringIO
except:
    from io import StringIO


import argparse
import os
import re
import sre_constants
import subprocess
import warnings
import io
from string import Formatter
from datetime import datetime
from difflib import unified_diff
from tempfile import NamedTemporaryFile

import sys
import codecs

if sys.version_info[0] == 2:
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

__VERSION__ = '0.5.3'

DESCRIPTION = 'bumpversion: v{} (using Python v{})'.format(
    __VERSION__,
    sys.version.split("\n")[0].split(" ")[0],
)

import logging
logger = logging.getLogger("bumpversion.logger")
logger_list = logging.getLogger("bumpversion.list")

from argparse import _AppendAction
class DiscardDefaultIfSpecifiedAppendAction(_AppendAction):

    '''
    Fixes bug http://bugs.python.org/issue16399 for 'append' action
    '''

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(self, "_discarded_default", None) is None:
            setattr(namespace, self.dest, [])
            self._discarded_default = True

        super(DiscardDefaultIfSpecifiedAppendAction, self).__call__(
                parser, namespace, values, option_string=None)

time_context = {
    'now': datetime.now(),
    'utcnow': datetime.utcnow(),
}

class BaseVCS(object):

    @classmethod
    def commit(cls, message):
        f = NamedTemporaryFile('wb', delete=False)
        f.write(message.encode('utf-8'))
        f.close()
        subprocess.check_output(cls._COMMIT_COMMAND + [f.name], env=dict(
            list(os.environ.items()) + [(b'HGENCODING', b'utf-8')]
        ))
        os.unlink(f.name)

    @classmethod
    def is_usable(cls):
        try:
            return subprocess.call(
                cls._TEST_USABLE_COMMAND,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
            ) == 0
        except OSError as e:
            if e.errno == 2:
                # mercurial is not installed then, ok.
                return False
            raise


class Git(BaseVCS):

    _TEST_USABLE_COMMAND = ["git", "rev-parse", "--git-dir"]
    _COMMIT_COMMAND = ["git", "commit", "-F"]

    @classmethod
    def assert_nondirty(cls):
        lines = [
            line.strip() for line in
            subprocess.check_output(
                ["git", "status", "--porcelain"]).splitlines()
            if not line.strip().startswith(b"??")
        ]

        if lines:
            raise WorkingDirectoryIsDirtyException(
                "Git working directory is not clean:\n{}".format(
                    b"\n".join(lines)))

    @classmethod
    def latest_tag_info(cls):
        try:
            # git-describe doesn't update the git-index, so we do that
            subprocess.check_output(["git", "update-index", "--refresh"])

            # get info about the latest tag in git
            describe_out = subprocess.check_output([
                "git",
                "describe",
                "--dirty",
                "--tags",
                "--long",
                "--abbrev=40",
                "--match=v*",
            ], stderr=subprocess.STDOUT
            ).decode().split("-")
        except subprocess.CalledProcessError:
            # logger.warn("Error when running git describe")
            return {}

        info = {}

        if describe_out[-1].strip() == "dirty":
            info["dirty"] = True
            describe_out.pop()

        info["commit_sha"] = describe_out.pop().lstrip("g")
        info["distance_to_latest_tag"] = int(describe_out.pop())
        info["current_version"] = "-".join(describe_out).lstrip("v")

        return info

    @classmethod
    def add_path(cls, path):
        subprocess.check_output(["git", "add", "--update", path])

    @classmethod
    def tag(cls, name):
        subprocess.check_output(["git", "tag", name])


class Mercurial(BaseVCS):

    _TEST_USABLE_COMMAND = ["hg", "root"]
    _COMMIT_COMMAND = ["hg", "commit", "--logfile"]

    @classmethod
    def latest_tag_info(cls):
        return {}

    @classmethod
    def assert_nondirty(cls):
        lines = [
            line.strip() for line in
            subprocess.check_output(
                ["hg", "status", "-mard"]).splitlines()
            if not line.strip().startswith(b"??")
        ]

        if lines:
            raise WorkingDirectoryIsDirtyException(
                "Mercurial working directory is not clean:\n{}".format(
                    b"\n".join(lines)))

    @classmethod
    def add_path(cls, path):
        pass

    @classmethod
    def tag(cls, name):
        subprocess.check_output(["hg", "tag", name])

VCS = [Git, Mercurial]


def prefixed_environ():
    return dict((("${}".format(key), value) for key, value in os.environ.items()))

class ConfiguredFile(object):

    def __init__(self, path, versionconfig):
        self.path = path
        self._versionconfig = versionconfig

    def should_contain_version(self, version, context):

        context['current_version'] = self._versionconfig.serialize(version, context)

        serialized_version = self._versionconfig.search.format(**context)

        if self.contains(serialized_version):
            return

        msg = "Did not find '{}' or '{}' in file {}".format(version.original, serialized_version, self.path)

        if version.original:
            assert self.contains(version.original), msg
            return

        assert False, msg

    def contains(self, search):
        with io.open(self.path, 'rb') as f:
            search_lines = search.splitlines()
            lookbehind = []

            for lineno, line in enumerate(f.readlines()):
                lookbehind.append(line.decode('utf-8').rstrip("\n"))

                if len(lookbehind) > len(search_lines):
                    lookbehind = lookbehind[1:]

                if (search_lines[0] in lookbehind[0] and
                   search_lines[-1] in lookbehind[-1] and
                   search_lines[1:-1] == lookbehind[1:-1]):
                    logger.info("Found '{}' in {} at line {}: {}".format(
                        search, self.path, lineno - (len(lookbehind) - 1), line.decode('utf-8').rstrip()))
                    return True
        return False

    def replace(self, current_version, new_version, context, dry_run):

        with io.open(self.path, 'rb') as f:
            file_content_before = f.read().decode('utf-8')

        context['current_version'] = self._versionconfig.serialize(current_version, context)
        context['new_version'] = self._versionconfig.serialize(new_version, context)

        search_for = self._versionconfig.search.format(**context)
        replace_with = self._versionconfig.replace.format(**context)

        file_content_after = file_content_before.replace(
            search_for, replace_with
        )

        if file_content_before == file_content_after:
            # TODO expose this to be configurable
            file_content_after = file_content_before.replace(
                current_version.original,
                replace_with,
            )

        if file_content_before != file_content_after:
            logger.info("{} file {}:".format(
                "Would change" if dry_run else "Changing",
                self.path,
            ))
            logger.info("\n".join(list(unified_diff(
                file_content_before.splitlines(),
                file_content_after.splitlines(),
                lineterm="",
                fromfile="a/"+self.path,
                tofile="b/"+self.path
            ))))
        else:
            logger.info("{} file {}".format(
                "Would not change" if dry_run else "Not changing",
                self.path,
            ))

        if not dry_run:
            with io.open(self.path, 'wb') as f:
                f.write(file_content_after.encode('utf-8'))

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<bumpversion.ConfiguredFile:{}>'.format(self.path)

class VersionPartConfiguration(object):
    pass

class ConfiguredVersionPartConfiguration(object):

    def __init__(self, values, optional_value=None, first_value=None):

        assert len(values) > 0

        self._values = values

        if optional_value is None:
            optional_value = values[0]

        assert optional_value in values

        self.optional_value = optional_value

        if first_value is None:
            first_value = values[0]

        assert first_value in values

        self.first_value = first_value

    def bump(self, value):
        return self._values[self._values.index(value)+1]

class NumericVersionPartConfiguration(VersionPartConfiguration):

    optional_value = "0"

    FIRST_NUMERIC = re.compile('([^\d]*)(\d+)(.*)')

    def __init__(self, first_value=None):

        if first_value is None:
            first_value = "0"

        int(first_value) # make sure that it's numeric

        self.first_value = first_value

    @classmethod
    def bump(cls, value):
        part_prefix, numeric_version, part_suffix = cls.FIRST_NUMERIC.search(value).groups()
        bumped_numeric = str(int(numeric_version) + 1)
        return "".join([part_prefix, bumped_numeric, part_suffix])

class VersionPart(object):

    def __init__(self, value, config=None):
        self._value = value

        if config is None:
            config = NumericVersionPartConfiguration()

        self.config = config

    @property
    def value(self):
        return self._value or self.config.optional_value

    def copy(self):
        return VersionPart(self._value)

    def bump(self):
        return VersionPart(self.config.bump(self.value), self.config)

    def is_optional(self):
        return self.value == self.config.optional_value

    def __format__(self, format_spec):
        return self.value

    def __repr__(self):
        return '<bumpversion.VersionPart:{}:{}>'.format(
            self.config.__class__.__name__,
            self.value
        )

    def null(self):
        return VersionPart(self.config.first_value, self.config)

class IncompleteVersionRepresenationException(Exception):
    def __init__(self, message):
        self.message = message

class MissingValueForSerializationException(Exception):
    def __init__(self, message):
        self.message = message

class WorkingDirectoryIsDirtyException(Exception):
    def __init__(self, message):
        self.message = message

def keyvaluestring(d):
    return ", ".join("{}={}".format(k, v) for k, v in sorted(d.items()))

class Version(object):

    def __init__(self, values, original=None):
        self._values = dict(values)
        self.original = original

    def __getitem__(self, key):
        return self._values[key]

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return '<bumpversion.Version:{}>'.format(keyvaluestring(self._values))

    def bump(self, part_name, order):
        bumped = False

        new_values = {}

        for label in order:
            if not label in self._values:
                continue
            elif label == part_name:
                new_values[label] = self._values[label].bump()
                bumped = True
            elif bumped:
                new_values[label] = self._values[label].null()
            else:
                new_values[label] = self._values[label].copy()

        new_version = Version(new_values)

        return new_version

class VersionConfig(object):

    """
    Holds a complete representation of a version string
    """

    def __init__(self, parse, serialize, search, replace, part_configs=None):

        try:
            self.parse_regex = re.compile(parse, re.VERBOSE)
        except sre_constants.error as e:
            logger.error("--parse '{}' is not a valid regex".format(parse))
            raise e

        self.serialize_formats = serialize

        if not part_configs:
            part_configs = {}

        self.part_configs = part_configs
        self.search = search
        self.replace = replace

    def _labels_for_format(self, serialize_format):
        return (
            label
            for _, label, _, _ in Formatter().parse(serialize_format)
            if label
        )

    def order(self):
        # currently, order depends on the first given serialization format
        # this seems like a good idea because this should be the most complete format
        return self._labels_for_format(self.serialize_formats[0])

    def parse(self, version_string):

        regexp_one_line = "".join([l.split("#")[0].strip() for l in self.parse_regex.pattern.splitlines()])

        logger.info("Parsing version '{}' using regexp '{}'".format(version_string, regexp_one_line))

        match = self.parse_regex.search(version_string)

        _parsed = {}
        if not match:
            logger.warn("Evaluating 'parse' option: '{}' does not parse current version '{}'".format(
                self.parse_regex.pattern, version_string))
            return

        for key, value in match.groupdict().items():
            _parsed[key] = VersionPart(value, self.part_configs.get(key))


        v = Version(_parsed, version_string)

        logger.info("Parsed the following values: %s" % keyvaluestring(v._values))

        return v

    def _serialize(self, version, serialize_format, context, raise_if_incomplete=False):
        """
        Attempts to serialize a version with the given serialization format.

        Raises MissingValueForSerializationException if not serializable
        """
        values = context.copy()
        for k in version:
            values[k] = version[k]

        # TODO dump complete context on debug level

        try:
            # test whether all parts required in the format have values
            serialized = serialize_format.format(**values)

        except KeyError as e:
            missing_key = getattr(e,
                'message', # Python 2
                e.args[0] # Python 3
            )
            raise MissingValueForSerializationException(
                "Did not find key {} in {} when serializing version number".format(
                    repr(missing_key), repr(version)))

        keys_needing_representation = set()
        found_required = False

        for k in self.order():
            v = values[k]

            if not isinstance(v, VersionPart):
                # values coming from environment variables don't need
                # representation
                continue

            if not v.is_optional():
                found_required = True
                keys_needing_representation.add(k)
            elif not found_required:
                keys_needing_representation.add(k)

        required_by_format = set(self._labels_for_format(serialize_format))

        # try whether all parsed keys are represented
        if raise_if_incomplete:
            if not (keys_needing_representation <= required_by_format):
                raise IncompleteVersionRepresenationException(
                    "Could not represent '{}' in format '{}'".format(
                        "', '".join(keys_needing_representation ^ required_by_format),
                        serialize_format,
                    ))

        return serialized


    def _choose_serialize_format(self, version, context):

        chosen = None

        # logger.info("Available serialization formats: '{}'".format("', '".join(self.serialize_formats)))

        for serialize_format in self.serialize_formats:
            try:
                self._serialize(version, serialize_format, context, raise_if_incomplete=True)
                chosen = serialize_format
                # logger.info("Found '{}' to be a usable serialization format".format(chosen))
            except IncompleteVersionRepresenationException as e:
                # logger.info(e.message)
                if not chosen:
                    chosen = serialize_format
            except MissingValueForSerializationException as e:
                logger.info(e.message)
                raise e

        if not chosen:
            raise KeyError("Did not find suitable serialization format")

        # logger.info("Selected serialization format '{}'".format(chosen))

        return chosen

    def serialize(self, version, context):
        serialized = self._serialize(version, self._choose_serialize_format(version, context), context)
        # logger.info("Serialized to '{}'".format(serialized))
        return serialized

OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES = [
    '--config-file',
    '--current-version',
    '--message',
    '--new-version',
    '--parse',
    '--serialize',
    '--search',
    '--replace',
    '--tag-name',
]


def split_args_in_optional_and_positional(args):
    # manually parsing positional arguments because stupid argparse can't mix
    # positional and optional arguments

    positions = []
    for i, arg in enumerate(args):

        previous = None

        if i > 0:
            previous = args[i-1]

        if ((not arg.startswith('--'))  and
            (previous not in OPTIONAL_ARGUMENTS_THAT_TAKE_VALUES)):
            positions.append(i)

    positionals = [arg for i, arg in enumerate(args) if i in positions]
    args = [arg for i, arg in enumerate(args) if i not in positions]

    return (positionals, args)

def main(original_args=None):

    positionals, args = split_args_in_optional_and_positional(
      sys.argv[1:] if original_args is None else original_args
    )

    if len(positionals[1:]) > 2:
        warnings.warn("Giving multiple files on the command line will be deprecated, please use [bumpversion:file:...] in a config file.", PendingDeprecationWarning)

    parser1 = argparse.ArgumentParser(add_help=False)

    parser1.add_argument(
        '--config-file', metavar='FILE',
        default=argparse.SUPPRESS, required=False,
        help='Config file to read most of the variables from (default: .bumpversion.cfg)')

    parser1.add_argument(
        '--verbose', action='count', default=0,
        help='Print verbose logging to stderr', required=False)

    parser1.add_argument(
        '--list', action='store_true', default=False,
        help='List machine readable information', required=False)

    parser1.add_argument(
        '--allow-dirty', action='store_true', default=False,
        help="Don't abort if working directory is dirty", required=False)

    known_args, remaining_argv = parser1.parse_known_args(args)

    logformatter = logging.Formatter('%(message)s')

    if len(logger.handlers) == 0:
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(logformatter)
        logger.addHandler(ch)

    if len(logger_list.handlers) == 0:
       ch2 = logging.StreamHandler(sys.stdout)
       ch2.setFormatter(logformatter)
       logger_list.addHandler(ch2)

    if known_args.list:
          logger_list.setLevel(1)

    log_level = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }.get(known_args.verbose, logging.DEBUG)

    logger.setLevel(log_level)

    logger.debug("Starting {}".format(DESCRIPTION))

    defaults = {}
    vcs_info = {}

    for vcs in VCS:
        if vcs.is_usable():
            vcs_info.update(vcs.latest_tag_info())

    if 'current_version' in vcs_info:
        defaults['current_version'] = vcs_info['current_version']

    config = RawConfigParser('')

    # don't transform keys to lowercase (which would be the default)
    config.optionxform = lambda option: option

    config.add_section('bumpversion')

    explicit_config = hasattr(known_args, 'config_file')

    if explicit_config:
        config_file = known_args.config_file
    elif not os.path.exists('.bumpversion.cfg') and \
            os.path.exists('setup.cfg'):
        config_file = 'setup.cfg'
    else:
        config_file = '.bumpversion.cfg'

    config_file_exists = os.path.exists(config_file)

    part_configs = {}

    files = []

    if config_file_exists:

        logger.info("Reading config file {}:".format(config_file))
        logger.info(io.open(config_file, 'rt', encoding='utf-8').read())

        config.readfp(io.open(config_file, 'rt', encoding='utf-8'))

        log_config = StringIO()
        config.write(log_config)

        if 'files' in dict(config.items("bumpversion")):
            warnings.warn(
                "'files =' configuration is will be deprecated, please use [bumpversion:file:...]",
                PendingDeprecationWarning
            )

        defaults.update(dict(config.items("bumpversion")))

        for listvaluename in ("serialize",):
            try:
                value = config.get("bumpversion", listvaluename)
                defaults[listvaluename] = list(filter(None, (x.strip() for x in value.splitlines())))
            except NoOptionError:
                pass  # no default value then ;)

        for boolvaluename in ("commit", "tag", "dry_run"):
            try:
                defaults[boolvaluename] = config.getboolean(
                    "bumpversion", boolvaluename)
            except NoOptionError:
                pass  # no default value then ;)

        for section_name in config.sections():

            section_name_match = re.compile("^bumpversion:(file|part):(.+)").match(section_name)

            if not section_name_match:
                continue

            section_prefix, section_value = section_name_match.groups()

            section_config = dict(config.items(section_name))

            if section_prefix == "part":

                ThisVersionPartConfiguration = NumericVersionPartConfiguration

                if 'values' in section_config:
                    section_config['values'] = list(filter(None, (x.strip() for x in section_config['values'].splitlines())))
                    ThisVersionPartConfiguration = ConfiguredVersionPartConfiguration

                part_configs[section_value] = ThisVersionPartConfiguration(**section_config)

            elif section_prefix == "file":

                filename = section_value

                if 'serialize' in section_config:
                    section_config['serialize'] = list(filter(None, (x.strip() for x in section_config['serialize'].splitlines())))

                section_config['part_configs'] = part_configs

                if not 'parse' in section_config:
                    section_config['parse'] = defaults.get("parse", '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)')

                if not 'serialize' in section_config:
                    section_config['serialize'] = defaults.get('serialize', [str('{major}.{minor}.{patch}')])

                if not 'search' in section_config:
                    section_config['search'] = defaults.get("search", '{current_version}')

                if not 'replace' in section_config:
                    section_config['replace'] = defaults.get("replace", '{new_version}')

                files.append(ConfiguredFile(filename, VersionConfig(**section_config)))

    else:
        message = "Could not read config file at {}".format(config_file)
        if explicit_config:
            raise argparse.ArgumentTypeError(message)
        else:
            logger.info(message)

    parser2 = argparse.ArgumentParser(prog='bumpversion', add_help=False, parents=[parser1])
    parser2.set_defaults(**defaults)

    parser2.add_argument('--current-version', metavar='VERSION',
                         help='Version that needs to be updated', required=False)
    parser2.add_argument('--parse', metavar='REGEX',
                         help='Regex parsing the version string',
                         default=defaults.get("parse", '(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)'))
    parser2.add_argument('--serialize', metavar='FORMAT',
                         action=DiscardDefaultIfSpecifiedAppendAction,
                         help='How to format what is parsed back to a version',
                         default=defaults.get("serialize", [str('{major}.{minor}.{patch}')]))
    parser2.add_argument('--search', metavar='SEARCH',
                         help='Template for complete string to search',
                         default=defaults.get("search", '{current_version}'))
    parser2.add_argument('--replace', metavar='REPLACE',
                         help='Template for complete string to replace',
                         default=defaults.get("replace", '{new_version}'))

    known_args, remaining_argv = parser2.parse_known_args(args)

    defaults.update(vars(known_args))

    assert type(known_args.serialize) == list

    context = dict(list(time_context.items()) + list(prefixed_environ().items()) + list(vcs_info.items()))

    try:
        vc = VersionConfig(
            parse=known_args.parse,
            serialize=known_args.serialize,
            search=known_args.search,
            replace=known_args.replace,
            part_configs=part_configs,
        )
    except sre_constants.error as e:
        sys.exit(1)

    current_version = vc.parse(known_args.current_version) if known_args.current_version else None

    new_version = None

    if not 'new_version' in defaults and known_args.current_version:
        try:
            if current_version and len(positionals) > 0:
                logger.info("Attempting to increment part '{}'".format(positionals[0]))
                new_version = current_version.bump(positionals[0], vc.order())
                logger.info("Values are now: " + keyvaluestring(new_version._values))
                defaults['new_version'] = vc.serialize(new_version, context)
        except MissingValueForSerializationException as e:
            logger.info("Opportunistic finding of new_version failed: " + e.message)
        except IncompleteVersionRepresenationException as e:
            logger.info("Opportunistic finding of new_version failed: " + e.message)
        except KeyError as e:
            logger.info("Opportunistic finding of new_version failed")

    parser3 = argparse.ArgumentParser(
        prog='bumpversion',
        description=DESCRIPTION,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        conflict_handler='resolve',
        parents=[parser2],
    )

    parser3.set_defaults(**defaults)

    parser3.add_argument('--current-version', metavar='VERSION',
                         help='Version that needs to be updated',
                         required=not 'current_version' in defaults)
    parser3.add_argument('--dry-run', '-n', action='store_true',
                         default=False, help="Don't write any files, just pretend.")
    parser3.add_argument('--new-version', metavar='VERSION',
                         help='New version that should be in the files',
                         required=not 'new_version' in defaults)

    commitgroup = parser3.add_mutually_exclusive_group()

    commitgroup.add_argument('--commit', action='store_true', dest="commit",
                             help='Commit to version control', default=defaults.get("commit", False))
    commitgroup.add_argument('--no-commit', action='store_false', dest="commit",
                             help='Do not commit to version control', default=argparse.SUPPRESS)

    taggroup = parser3.add_mutually_exclusive_group()

    taggroup.add_argument('--tag', action='store_true', dest="tag", default=defaults.get("tag", False),
                          help='Create a tag in version control')
    taggroup.add_argument('--no-tag', action='store_false', dest="tag",
                          help='Do not create a tag in version control', default=argparse.SUPPRESS)

    parser3.add_argument('--tag-name', metavar='TAG_NAME',
                         help='Tag name (only works with --tag)',
                         default=defaults.get('tag_name', 'v{new_version}'))

    parser3.add_argument('--message', '-m', metavar='COMMIT_MSG',
                         help='Commit message',
                         default=defaults.get('message', 'Bump version: {current_version} → {new_version}'))


    file_names = []
    if 'files' in defaults:
        assert defaults['files'] != None
        file_names = defaults['files'].split(' ')

    parser3.add_argument('part',
                         help='Part of the version to be bumped.')
    parser3.add_argument('files', metavar='file',
                         nargs='*',
                         help='Files to change', default=file_names)

    args = parser3.parse_args(remaining_argv + positionals)

    if args.dry_run:
        logger.info("Dry run active, won't touch any files.")
    
    if args.new_version:
        new_version = vc.parse(args.new_version)

    logger.info("New version will be '{}'".format(args.new_version))

    file_names = file_names or positionals[1:]

    for file_name in file_names:
        files.append(ConfiguredFile(file_name, vc))

    for vcs in VCS:
        if vcs.is_usable():
            try:
                vcs.assert_nondirty()
            except WorkingDirectoryIsDirtyException as e:
                if not defaults['allow_dirty']:
                    logger.warn(
                        "{}\n\nUse --allow-dirty to override this if you know what you're doing.".format(e.message))
                    raise
            break
        else:
            vcs = None

    # make sure files exist and contain version string

    logger.info("Asserting files {} contain the version string:".format(", ".join([str(f) for f in files])))

    for f in files:
        f.should_contain_version(current_version, context)

    # change version string in files
    for f in files:
        f.replace(current_version, new_version, context, args.dry_run)

    commit_files = [f.path for f in files]

    config.set('bumpversion', 'new_version', args.new_version)

    for key, value in config.items('bumpversion'):
        logger_list.info("{}={}".format(key, value))

    config.remove_option('bumpversion', 'new_version')

    config.set('bumpversion', 'current_version', args.new_version)

    new_config = StringIO()

    try:
        write_to_config_file = (not args.dry_run) and config_file_exists

        logger.info("{} to config file {}:".format(
            "Would write" if not write_to_config_file else "Writing",
            config_file,
        ))

        config.write(new_config)
        logger.info(new_config.getvalue())

        if write_to_config_file:
            with io.open(config_file, 'wb') as f:
                f.write(new_config.getvalue().encode('utf-8'))

    except UnicodeEncodeError:
        warnings.warn(
            "Unable to write UTF-8 to config file, because of an old configparser version. "
            "Update with `pip install --upgrade configparser`."
        )

    if config_file_exists:
        commit_files.append(config_file)

    if not vcs:
        return

    assert vcs.is_usable(), "Did find '{}' unusable, unable to commit.".format(vcs.__name__)

    do_commit = (not args.dry_run) and args.commit
    do_tag = (not args.dry_run) and args.tag

    logger.info("{} {} commit".format(
        "Would prepare" if not do_commit else "Preparing",
        vcs.__name__,
    ))

    for path in commit_files:
        logger.info("{} changes in file '{}' to {}".format(
            "Would add" if not do_commit else "Adding",
            path,
            vcs.__name__,
        ))

        if do_commit:
            vcs.add_path(path)

    vcs_context = {
        "current_version": args.current_version,
        "new_version": args.new_version,
    }
    vcs_context.update(time_context)
    vcs_context.update(prefixed_environ())

    commit_message = args.message.format(**vcs_context)

    logger.info("{} to {} with message '{}'".format(
        "Would commit" if not do_commit else "Committing",
        vcs.__name__,
        commit_message,
    ))

    if do_commit:
        vcs.commit(message=commit_message)

    tag_name = args.tag_name.format(**vcs_context)
    logger.info("{} '{}' in {}".format(
        "Would tag" if not do_tag else "Tagging",
        tag_name,
        vcs.__name__
    ))

    if do_tag:
        vcs.tag(tag_name)

