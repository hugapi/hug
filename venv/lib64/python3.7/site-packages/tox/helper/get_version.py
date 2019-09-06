from __future__ import unicode_literals

import json
import sys

info = {
    "executable": sys.executable,
    "name": "pypy" if hasattr(sys, "pypy_version_info") else "python",
    "version_info": list(sys.version_info),
    "version": sys.version,
    "is_64": sys.maxsize > 2 ** 32,
    "sysplatform": sys.platform,
}
info_as_dump = json.dumps(info)
print(info_as_dump)
