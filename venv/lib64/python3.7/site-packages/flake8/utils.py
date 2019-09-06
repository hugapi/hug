"""Utility methods for flake8."""
import collections
import fnmatch as _fnmatch
import inspect
import io
import os
import platform
import re
import sys
import tokenize
from typing import Callable, Dict, Generator, List, Pattern, Sequence, Set
from typing import Tuple, Union

from flake8 import exceptions

if False:  # `typing.TYPE_CHECKING` was introduced in 3.5.2
    from flake8.plugins.manager import Plugin

DIFF_HUNK_REGEXP = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@.*$")
COMMA_SEPARATED_LIST_RE = re.compile(r"[,\s]")
LOCAL_PLUGIN_LIST_RE = re.compile(r"[,\t\n\r\f\v]")


def parse_comma_separated_list(value, regexp=COMMA_SEPARATED_LIST_RE):
    # type: (Union[Sequence[str], str], Pattern[str]) -> List[str]
    """Parse a comma-separated list.

    :param value:
        String or list of strings to be parsed and normalized.
    :param regexp:
        Compiled regular expression used to split the value when it is a
        string.
    :type regexp:
        _sre.SRE_Pattern
    :returns:
        List of values with whitespace stripped.
    :rtype:
        list
    """
    if not value:
        return []

    if not isinstance(value, (list, tuple)):
        value = regexp.split(value)

    item_gen = (item.strip() for item in value)
    return [item for item in item_gen if item]


_Token = collections.namedtuple("Token", ("tp", "src"))
_CODE, _FILE, _COLON, _COMMA, _WS = "code", "file", "colon", "comma", "ws"
_EOF = "eof"
_FILE_LIST_TOKEN_TYPES = [
    (re.compile(r"[A-Z]+[0-9]*(?=$|\s|,)"), _CODE),
    (re.compile(r"[^\s:,]+"), _FILE),
    (re.compile(r"\s*:\s*"), _COLON),
    (re.compile(r"\s*,\s*"), _COMMA),
    (re.compile(r"\s+"), _WS),
]


def _tokenize_files_to_codes_mapping(value):
    # type: (str) -> List[_Token]
    tokens = []
    i = 0
    while i < len(value):
        for token_re, token_name in _FILE_LIST_TOKEN_TYPES:
            match = token_re.match(value, i)
            if match:
                tokens.append(_Token(token_name, match.group().strip()))
                i = match.end()
                break
        else:
            raise AssertionError("unreachable", value, i)
    tokens.append(_Token(_EOF, ""))

    return tokens


def parse_files_to_codes_mapping(value):  # noqa: C901
    # type: (Union[Sequence[str], str]) -> List[Tuple[List[str], List[str]]]
    """Parse a files-to-codes maping.

    A files-to-codes mapping a sequence of values specified as
    `filenames list:codes list ...`.  Each of the lists may be separated by
    either comma or whitespace tokens.

    :param value: String to be parsed and normalized.
    :type value: str
    """
    if isinstance(value, (list, tuple)):
        value = "\n".join(value)

    ret = []
    if not value.strip():
        return ret

    class State:
        seen_sep = True
        seen_colon = False
        filenames = []
        codes = []

    def _reset():
        if State.codes:
            for filename in State.filenames:
                ret.append((filename, State.codes))
        State.seen_sep = True
        State.seen_colon = False
        State.filenames = []
        State.codes = []

    def _unexpected_token():
        # type: () -> exceptions.ExecutionError

        def _indent(s):
            # type: (str) -> str
            return "    " + s.strip().replace("\n", "\n    ")

        return exceptions.ExecutionError(
            "Expected `per-file-ignores` to be a mapping from file exclude "
            "patterns to ignore codes.\n\n"
            "Configured `per-file-ignores` setting:\n\n{}".format(
                _indent(value)
            )
        )

    for token in _tokenize_files_to_codes_mapping(value):
        # legal in any state: separator sets the sep bit
        if token.tp in {_COMMA, _WS}:
            State.seen_sep = True
        # looking for filenames
        elif not State.seen_colon:
            if token.tp == _COLON:
                State.seen_colon = True
                State.seen_sep = True
            elif State.seen_sep and token.tp == _FILE:
                State.filenames.append(token.src)
                State.seen_sep = False
            else:
                raise _unexpected_token()
        # looking for codes
        else:
            if token.tp == _EOF:
                _reset()
            elif State.seen_sep and token.tp == _CODE:
                State.codes.append(token.src)
                State.seen_sep = False
            elif State.seen_sep and token.tp == _FILE:
                _reset()
                State.filenames.append(token.src)
                State.seen_sep = False
            else:
                raise _unexpected_token()

    return ret


def normalize_paths(paths, parent=os.curdir):
    # type: (Union[Sequence[str], str], str) -> List[str]
    """Parse a comma-separated list of paths.

    :returns:
        The normalized paths.
    :rtype:
        [str]
    """
    return [
        normalize_path(p, parent) for p in parse_comma_separated_list(paths)
    ]


def normalize_path(path, parent=os.curdir):
    # type: (str, str) -> str
    """Normalize a single-path.

    :returns:
        The normalized path.
    :rtype:
        str
    """
    # NOTE(sigmavirus24): Using os.path.sep and os.path.altsep allow for
    # Windows compatibility with both Windows-style paths (c:\\foo\bar) and
    # Unix style paths (/foo/bar).
    separator = os.path.sep
    # NOTE(sigmavirus24): os.path.altsep may be None
    alternate_separator = os.path.altsep or ""
    if separator in path or (
        alternate_separator and alternate_separator in path
    ):
        path = os.path.abspath(os.path.join(parent, path))
    return path.rstrip(separator + alternate_separator)


def _stdin_get_value_py3():
    stdin_value = sys.stdin.buffer.read()
    fd = io.BytesIO(stdin_value)
    try:
        (coding, lines) = tokenize.detect_encoding(fd.readline)
        return io.StringIO(stdin_value.decode(coding))
    except (LookupError, SyntaxError, UnicodeError):
        return io.StringIO(stdin_value.decode("utf-8"))


def stdin_get_value():
    # type: () -> str
    """Get and cache it so plugins can use it."""
    cached_value = getattr(stdin_get_value, "cached_stdin", None)
    if cached_value is None:
        if sys.version_info < (3, 0):
            stdin_value = io.BytesIO(sys.stdin.read())
        else:
            stdin_value = _stdin_get_value_py3()
        stdin_get_value.cached_stdin = stdin_value
        cached_value = stdin_get_value.cached_stdin
    return cached_value.getvalue()


def parse_unified_diff(diff=None):
    # type: (str) -> Dict[str, Set[int]]
    """Parse the unified diff passed on stdin.

    :returns:
        dictionary mapping file names to sets of line numbers
    :rtype:
        dict
    """
    # Allow us to not have to patch out stdin_get_value
    if diff is None:
        diff = stdin_get_value()

    number_of_rows = None
    current_path = None
    parsed_paths = collections.defaultdict(set)
    for line in diff.splitlines():
        if number_of_rows:
            # NOTE(sigmavirus24): Below we use a slice because stdin may be
            # bytes instead of text on Python 3.
            if line[:1] != "-":
                number_of_rows -= 1
            # We're in the part of the diff that has lines starting with +, -,
            # and ' ' to show context and the changes made. We skip these
            # because the information we care about is the filename and the
            # range within it.
            # When number_of_rows reaches 0, we will once again start
            # searching for filenames and ranges.
            continue

        # NOTE(sigmavirus24): Diffs that we support look roughly like:
        #    diff a/file.py b/file.py
        #    ...
        #    --- a/file.py
        #    +++ b/file.py
        # Below we're looking for that last line. Every diff tool that
        # gives us this output may have additional information after
        # ``b/file.py`` which it will separate with a \t, e.g.,
        #    +++ b/file.py\t100644
        # Which is an example that has the new file permissions/mode.
        # In this case we only care about the file name.
        if line[:3] == "+++":
            current_path = line[4:].split("\t", 1)[0]
            # NOTE(sigmavirus24): This check is for diff output from git.
            if current_path[:2] == "b/":
                current_path = current_path[2:]
            # We don't need to do anything else. We have set up our local
            # ``current_path`` variable. We can skip the rest of this loop.
            # The next line we will see will give us the hung information
            # which is in the next section of logic.
            continue

        hunk_match = DIFF_HUNK_REGEXP.match(line)
        # NOTE(sigmavirus24): pep8/pycodestyle check for:
        #    line[:3] == '@@ '
        # But the DIFF_HUNK_REGEXP enforces that the line start with that
        # So we can more simply check for a match instead of slicing and
        # comparing.
        if hunk_match:
            (row, number_of_rows) = [
                1 if not group else int(group)
                for group in hunk_match.groups()
            ]
            parsed_paths[current_path].update(
                range(row, row + number_of_rows)
            )

    # We have now parsed our diff into a dictionary that looks like:
    #    {'file.py': set(range(10, 16), range(18, 20)), ...}
    return parsed_paths


def is_windows():
    # type: () -> bool
    """Determine if we're running on Windows.

    :returns:
        True if running on Windows, otherwise False
    :rtype:
        bool
    """
    return os.name == "nt"


# NOTE(sigmavirus24): If and when https://bugs.python.org/issue27649 is fixed,
# re-enable multiprocessing support on Windows.
def can_run_multiprocessing_on_windows():
    # type: () -> bool
    """Determine if we can use multiprocessing on Windows.

    This presently will **always** return False due to a `bug`_ in the
    :mod:`multiprocessing` module on Windows. Once fixed, we will check
    to ensure that the version of Python contains that fix (via version
    inspection) and *conditionally* re-enable support on Windows.

    .. _bug:
        https://bugs.python.org/issue27649

    :returns:
        True if the version of Python is modern enough, otherwise False
    :rtype:
        bool
    """
    is_new_enough_python27 = (2, 7, 11) <= sys.version_info < (3, 0)
    is_new_enough_python3 = sys.version_info > (3, 2)
    return False and (is_new_enough_python27 or is_new_enough_python3)


def is_using_stdin(paths):
    # type: (List[str]) -> bool
    """Determine if we're going to read from stdin.

    :param list paths:
        The paths that we're going to check.
    :returns:
        True if stdin (-) is in the path, otherwise False
    :rtype:
        bool
    """
    return "-" in paths


def _default_predicate(*args):
    return False


def filenames_from(arg, predicate=None):
    # type: (str, Callable[[str], bool]) -> Generator
    """Generate filenames from an argument.

    :param str arg:
        Parameter from the command-line.
    :param callable predicate:
        Predicate to use to filter out filenames. If the predicate
        returns ``True`` we will exclude the filename, otherwise we
        will yield it. By default, we include every filename
        generated.
    :returns:
        Generator of paths
    """
    if predicate is None:
        predicate = _default_predicate

    if predicate(arg):
        return

    if os.path.isdir(arg):
        for root, sub_directories, files in os.walk(arg):
            if predicate(root):
                sub_directories[:] = []
                continue

            # NOTE(sigmavirus24): os.walk() will skip a directory if you
            # remove it from the list of sub-directories.
            for directory in sub_directories:
                joined = os.path.join(root, directory)
                if predicate(joined):
                    sub_directories.remove(directory)

            for filename in files:
                joined = os.path.join(root, filename)
                if predicate(joined) or predicate(filename):
                    continue
                yield joined
    else:
        yield arg


def fnmatch(filename, patterns, default=True):
    # type: (str, List[str], bool) -> bool
    """Wrap :func:`fnmatch.fnmatch` to add some functionality.

    :param str filename:
        Name of the file we're trying to match.
    :param list patterns:
        Patterns we're using to try to match the filename.
    :param bool default:
        The default value if patterns is empty
    :returns:
        True if a pattern matches the filename, False if it doesn't.
        ``default`` if patterns is empty.
    """
    if not patterns:
        return default
    return any(_fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def parameters_for(plugin):
    # type: (Plugin) -> Dict[str, bool]
    """Return the parameters for the plugin.

    This will inspect the plugin and return either the function parameters
    if the plugin is a function or the parameters for ``__init__`` after
    ``self`` if the plugin is a class.

    :param plugin:
        The internal plugin object.
    :type plugin:
        flake8.plugins.manager.Plugin
    :returns:
        A dictionary mapping the parameter name to whether or not it is
        required (a.k.a., is positional only/does not have a default).
    :rtype:
        dict([(str, bool)])
    """
    func = plugin.plugin
    is_class = not inspect.isfunction(func)
    if is_class:  # The plugin is a class
        func = plugin.plugin.__init__

    if sys.version_info < (3, 3):
        argspec = inspect.getargspec(func)
        start_of_optional_args = len(argspec[0]) - len(argspec[-1] or [])
        parameter_names = argspec[0]
        parameters = collections.OrderedDict(
            [
                (name, position < start_of_optional_args)
                for position, name in enumerate(parameter_names)
            ]
        )
    else:
        parameters = collections.OrderedDict(
            [
                (parameter.name, parameter.default is parameter.empty)
                for parameter in inspect.signature(func).parameters.values()
                if parameter.kind == parameter.POSITIONAL_OR_KEYWORD
            ]
        )

    if is_class:
        parameters.pop("self", None)

    return parameters


def matches_filename(path, patterns, log_message, logger):
    """Use fnmatch to discern if a path exists in patterns.

    :param str path:
        The path to the file under question
    :param patterns:
        The patterns to match the path against.
    :type patterns:
        list[str]
    :param str log_message:
        The message used for logging purposes.
    :returns:
        True if path matches patterns, False otherwise
    :rtype:
        bool
    """
    if not patterns:
        return False
    basename = os.path.basename(path)
    if fnmatch(basename, patterns):
        logger.debug(log_message, {"path": basename, "whether": ""})
        return True

    absolute_path = os.path.abspath(path)
    match = fnmatch(absolute_path, patterns)
    logger.debug(
        log_message,
        {"path": absolute_path, "whether": "" if match else "not "},
    )
    return match


def get_python_version():
    """Find and format the python implementation and version.

    :returns:
        Implementation name, version, and platform as a string.
    :rtype:
        str
    """
    return "%s %s on %s" % (
        platform.python_implementation(),
        platform.python_version(),
        platform.system(),
    )
