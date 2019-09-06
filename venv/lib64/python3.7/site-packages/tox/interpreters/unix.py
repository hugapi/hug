from __future__ import unicode_literals

import tox

from .py_spec import CURRENT, PythonSpec
from .via_path import check_with_path


@tox.hookimpl
def tox_get_python_executable(envconfig):
    base_python = envconfig.basepython
    spec = PythonSpec.from_name(base_python)
    # first, check current
    if spec.name is not None and CURRENT.satisfies(spec):
        return CURRENT.path
    # second check if the literal base python
    candidates = [base_python]
    # third check if the un-versioned name is good
    if spec.name is not None and spec.name != base_python:
        candidates.append(spec.name)
    return check_with_path(candidates, spec)
