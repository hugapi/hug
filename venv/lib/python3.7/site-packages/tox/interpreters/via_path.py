from __future__ import unicode_literals

import json
import os
import subprocess
from collections import defaultdict
from threading import Lock

import py

from tox import reporter
from tox.constants import VERSION_QUERY_SCRIPT

from .py_spec import PythonSpec


def check_with_path(candidates, spec):
    for path in candidates:
        base = path
        if not os.path.isabs(path):
            path = py.path.local.sysfind(path)
        if path is not None:
            if os.path.exists(str(path)):
                cur_spec = exe_spec(path, base)
                if cur_spec is not None and cur_spec.satisfies(spec):
                    return cur_spec.path


_SPECS = {}
_SPECK_LOCK = defaultdict(Lock)


def exe_spec(python_exe, base):
    if not isinstance(python_exe, str):
        python_exe = str(python_exe)
    with _SPECK_LOCK[python_exe]:
        if python_exe not in _SPECS:
            info = get_python_info([python_exe])
            if info is not None:
                found = PythonSpec(
                    info["name"],
                    info["version_info"][0],
                    info["version_info"][1],
                    64 if info["is_64"] else 32,
                    info["executable"],
                )
                reporter.verbosity2("{} ({}) is {}".format(base, python_exe, info))
            else:
                found = None
            _SPECS[python_exe] = found
    return _SPECS[python_exe]


def get_python_info(cmd):
    proc = subprocess.Popen(
        cmd + [VERSION_QUERY_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    out, err = proc.communicate()
    if not proc.returncode:
        try:
            result = json.loads(out)
        except ValueError as exception:
            failure = exception
        else:
            return result
    else:
        failure = "exit code {}".format(proc.returncode)
    reporter.verbosity1("{!r} cmd {!r} out {!r} err {!r} ".format(failure, cmd, out, err))
