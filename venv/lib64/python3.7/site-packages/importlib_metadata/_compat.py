from __future__ import absolute_import

import io
import abc
import sys
import email


if sys.version_info > (3,):  # pragma: nocover
    import builtins
    from configparser import ConfigParser
    from contextlib import suppress
    FileNotFoundError = builtins.FileNotFoundError
    IsADirectoryError = builtins.IsADirectoryError
    NotADirectoryError = builtins.NotADirectoryError
    PermissionError = builtins.PermissionError
    map = builtins.map
else:  # pragma: nocover
    from backports.configparser import ConfigParser
    from itertools import imap as map  # type: ignore
    from contextlib2 import suppress  # noqa
    FileNotFoundError = IOError, OSError
    IsADirectoryError = IOError, OSError
    NotADirectoryError = IOError, OSError
    PermissionError = IOError, OSError

if sys.version_info > (3, 5):  # pragma: nocover
    import pathlib
else:  # pragma: nocover
    import pathlib2 as pathlib

try:
    ModuleNotFoundError = builtins.FileNotFoundError
except (NameError, AttributeError):  # pragma: nocover
    ModuleNotFoundError = ImportError  # type: ignore


if sys.version_info >= (3,):  # pragma: nocover
    from importlib.abc import MetaPathFinder
else:  # pragma: nocover
    class MetaPathFinder(object):
        __metaclass__ = abc.ABCMeta


__metaclass__ = type
__all__ = [
    'install', 'NullFinder', 'MetaPathFinder', 'ModuleNotFoundError',
    'pathlib', 'ConfigParser', 'map', 'suppress', 'FileNotFoundError',
    'NotADirectoryError', 'email_message_from_string',
    ]


def install(cls):
    """Class decorator for installation on sys.meta_path."""
    sys.meta_path.append(cls())
    return cls


class NullFinder:
    """
    A "Finder" (aka "MetaClassFinder") that never finds any modules,
    but may find distributions.
    """
    @staticmethod
    def find_spec(*args, **kwargs):
        return None

    # In Python 2, the import system requires finders
    # to have a find_module() method, but this usage
    # is deprecated in Python 3 in favor of find_spec().
    # For the purposes of this finder (i.e. being present
    # on sys.meta_path but having no other import
    # system functionality), the two methods are identical.
    find_module = find_spec


def py2_message_from_string(text):  # nocoverpy3
    # Work around https://bugs.python.org/issue25545 where
    # email.message_from_string cannot handle Unicode on Python 2.
    io_buffer = io.StringIO(text)
    return email.message_from_file(io_buffer)


email_message_from_string = (
    py2_message_from_string
    if sys.version_info < (3,) else
    email.message_from_string
    )

# https://bitbucket.org/pypy/pypy/issues/3021/ioopen-directory-leaks-a-file-descriptor
PYPY_OPEN_BUG = getattr(sys, 'pypy_version_info', (9, 9, 9))[:3] <= (7, 1, 1)
