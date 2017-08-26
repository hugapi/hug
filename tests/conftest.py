"""Configuration for test environment"""
import sys

from .fixtures import *

collect_ignore = []

if sys.version_info < (3, 5):
    collect_ignore.append("test_async.py")
    collect_ignore.append("test_typing.py")

if sys.version_info < (3, 4):
    collect_ignore.append("test_coroutines.py")
