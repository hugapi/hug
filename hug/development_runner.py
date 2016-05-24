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
import inspect
import os
import sys
from wsgiref.simple_server import make_server

try:
    from watchdog.observers import Observer
    from watchdog.events import RegexMatchingEventHandler
except ImportError:
    Observer = None
    RegexMatchingEventHandler = None

from hug._version import current
from hug.api import API
from hug.route import cli
from hug.types import boolean, number


INTRO = """
/########################################################################\\
          `.----``..-------..``.----.
         :/:::::--:---------:--::::://.
        .+::::----##/-/oo+:-##----:::://
        `//::-------/oosoo-------::://.       ##    ##  ##    ##    #####
          .-:------./++o/o-.------::-`   ```  ##    ##  ##    ##  ##
             `----.-./+o+:..----.     `.:///. ########  ##    ## ##
   ```        `----.-::::::------  `.-:::://. ##    ##  ##    ## ##   ####
  ://::--.``` -:``...-----...` `:--::::::-.`  ##    ##  ##   ##   ##    ##
  :/:::::::::-:-     `````      .:::::-.`     ##    ##    ####     ######
   ``.--:::::::.                .:::.`
         ``..::.                .::         EMBRACE THE APIs OF THE FUTURE
             ::-                .:-
             -::`               ::-                   VERSION {0}
             `::-              -::`
              -::-`           -::-
\########################################################################/

 Copyright (C) 2016 Timothy Edmund Crosley
 Under the MIT License

""".format(current)


@cli(version=current)
def hug(file: 'A Python file that contains a Hug API'=None, module: 'A Python module that contains a Hug API'=None,
        port: number=8000, no_404_documentation: boolean=False,
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

    print(INTRO)
    httpd = None

    def start_httpd_service():
        nonlocal httpd
        api = API(api_module)
        if no_404_documentation:
            server = api.http.server(None)
        else:
            server = api.http.server()

        httpd = make_server('', port, server)
        print("Starting server on port {0}...".format(port))
        httpd.serve_forever()

    if Observer and RegexMatchingEventHandler:
        class APIReloadingEventHandler(RegexMatchingEventHandler):
            nonlocal httpd

            def on_any_event(self, event):
                nonlocal httpd
                importlib.reload(api_module)
                print()
                print('*** Module {} reloaded ***'.format(api_module.__name__))
                if httpd:
                    httpd.shutdown()

        src_file = os.path.abspath(inspect.getsourcefile(api_module))
        # TODO: make this observer more accurate
        observer = Observer()
        event_handler = APIReloadingEventHandler(regexes=[r'.*\.py$'])
        path = os.path.dirname(src_file)
        observer.schedule(event_handler, path, recursive=True)
        observer.start()

    try:
        while True:
            start_httpd_service()
    except KeyboardInterrupt:
        print()
        print('Goodbye')
