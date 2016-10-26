"""hug/development_runner.py

Contains logic to enable execution of hug APIS locally from the command line for development use

Copyright (C) 2016  Timothy Edmund Crosley

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
from __future__ import absolute_import

import importlib
import os
import sys

from hug._version import current
from hug.api import API
from hug.route import cli
from hug.types import boolean, number


@cli(version=current)
def hug(file: 'A Python file that contains a Hug API'=None, module: 'A Python module that contains a Hug API'=None,
        port: number=8000, no_404_documentation: boolean=False,
        no_reloader: boolean=False, interval: number=1,
        command: 'Run a command defined in the given module'=None):
    """Hug API Development Server"""
    api_module = None
    if file and module:
        print("Error: can not define both a file and module source for Hug API.")
        sys.exit(1)
    if file:
        sys.path.append(os.path.dirname(os.path.abspath(file)))
        sys.path.append(os.getcwd())
        api_module = importlib.machinery.SourceFileLoader(file.split(".")[0], file).load_module()
    elif module:
        api_module = importlib.import_module(module)
    if not api_module or not hasattr(api_module, '__hug__'):
        print("Error: must define a file name or module that contains a Hug API.")
        sys.exit(1)

    api = API(api_module)
    if command:
        if command not in api.cli.commands:
            print(str(api.cli))
            sys.exit(1)

        sys.argv[1:] = sys.argv[(sys.argv.index('-c') if '-c' in sys.argv else sys.argv.index('--command')) + 2:]
        api.cli.commands[command]()
        return
    reloader = not no_reloader
    if reloader and not os.environ.get('HUG_CHILD'):
        try:
            import tempfile
            import subprocess
            import time
            lockfile = None
            fd, lockfile = tempfile.mkstemp(prefix='hug.', suffix='.lock')
            os.close(fd) # We only need this file to exist. We never write to it
            while os.path.exists(lockfile):
                args = [sys.executable] + sys.argv
                environ = os.environ.copy()
                environ['HUG_CHILD'] = 'true'
                environ['HUG_CHILD'] = lockfile
                p = subprocess.Popen(args, env=environ)
                while p.poll() is None: # Busy wait...
                    os.utime(lockfile, None) # I am alive!
                    time.sleep(interval)
                if p.poll() != 3:
                    if os.path.exists(lockfile):
                        os.unlink(lockfile)
                    sys.exit(p.poll())
        except KeyboardInterrupt:
            pass
        finally:
            if os.path.exists(lockfile):
                os.unlink(lockfile)
    if reloader:
        from . _reloader import FileCheckerThread
        lockfile = os.environ.get('HUG_CHILD')
        bgcheck = FileCheckerThread(lockfile, interval)
        with bgcheck:
            API(api_module).http.serve(port, no_404_documentation)
        if bgcheck.status == 'reload':
            sys.exit(3)
    else:
        API(api_module).http.serve(port, no_404_documentation)
