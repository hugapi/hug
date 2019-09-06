# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://bitbucket.org/ned/coveragepy/src/default/NOTICE.txt

"""Determine facts about the environment."""

import os
import platform
import sys

# Operating systems.
WINDOWS = sys.platform == "win32"
LINUX = sys.platform == "linux2"

# Python implementations.
PYPY = (platform.python_implementation() == 'PyPy')
if PYPY:
    PYPYVERSION = sys.pypy_version_info

JYTHON = (platform.python_implementation() == 'Jython')
IRONPYTHON = (platform.python_implementation() == 'IronPython')

# Python versions.
PYVERSION = sys.version_info
PY2 = PYVERSION < (3, 0)
PY3 = PYVERSION >= (3, 0)

# Python behavior
class PYBEHAVIOR(object):
    """Flags indicating this Python's behavior."""

    # Is "if not __debug__" optimized away even better?
    optimize_if_not_debug2 = (not PYPY) and (PYVERSION >= (3, 8, 0, 'beta', 1))

    # When a break/continue/return statement in a try block jumps to a finally
    # block, does the finally block do the break/continue/return (pre-3.8), or
    # does the finally jump back to the break/continue/return (3.8) to do the
    # work?
    finally_jumps_back = (PYVERSION >= (3, 8))

    # When a function is decorated, does the trace function get called for the
    # @-line and also the def-line (new behavior in 3.8)? Or just the @-line
    # (old behavior)?
    trace_decorated_def = (PYVERSION >= (3, 8))

    # Are while-true loops optimized into absolute jumps with no loop setup?
    nix_while_true = (PYVERSION >= (3, 8))

# Coverage.py specifics.

# Are we using the C-implemented trace function?
C_TRACER = os.getenv('COVERAGE_TEST_TRACER', 'c') == 'c'

# Are we coverage-measuring ourselves?
METACOV = os.getenv('COVERAGE_COVERAGE', '') != ''

# Are we running our test suite?
# Even when running tests, you can use COVERAGE_TESTING=0 to disable the
# test-specific behavior like contracts.
TESTING = os.getenv('COVERAGE_TESTING', '') == 'True'
