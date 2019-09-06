from __future__ import unicode_literals

from threading import Lock

import tox

from ..py_spec import CURRENT, PythonSpec
from ..via_path import check_with_path


@tox.hookimpl
def tox_get_python_executable(envconfig):
    base_python = envconfig.basepython
    spec = PythonSpec.from_name(base_python)
    # first, check current
    if spec.name is not None and CURRENT.satisfies(spec):
        return CURRENT.path

    # second check if the py.exe has it (only for non path specs)
    if spec.path is None:
        py_exe = locate_via_pep514(spec)
        if py_exe is not None:
            return py_exe

    # third check if the literal base python is on PATH
    candidates = [envconfig.basepython]
    # fourth check if the name is on PATH
    if spec.name is not None and spec.name != base_python:
        candidates.append(spec.name)
    # or check known locations
    if spec.major is not None and spec.minor is not None:
        if spec.name == "python":
            # The standard names are in predictable places.
            candidates.append(r"c:\python{}{}\python.exe".format(spec.major, spec.minor))
    return check_with_path(candidates, spec)


_PY_AVAILABLE = []
_PY_LOCK = Lock()


def locate_via_pep514(spec):
    with _PY_LOCK:
        if not _PY_AVAILABLE:
            from . import pep514

            _PY_AVAILABLE.extend(pep514.discover_pythons())
            _PY_AVAILABLE.append(CURRENT)
    for cur_spec in _PY_AVAILABLE:
        if cur_spec.satisfies(spec):
            return cur_spec.path
