"""hug/development_runner.py

Contains logic to enable execution of hug APIS locally from the command line for development use

Copyright (C) 2015  Timothy Edmund Crosley

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
import hug


@hug.cli(version=hug.__version__)
def hug(file:'A Python file that contains a Hug API', module:'A Python module that contains a Hug API',
        port:hug.types.int=8000, no_404_documentation:hug.types.boolean=False):
    """Hug API Development Server"""
    api_module = None
    server_arguments = {}
    if file and module:
        print("Error: can not define both a file and module source for Hug API.")
        sys.exit(1)
    if file:
        sys.path.append(os.path.dirname(os.path.abspath(file)))
        api_module = importlib.machinery.SourceFileLoader(file.split(".")[0], file).load_module()
    elif module:
        api_module = importlib.import_module(module)
    if not api_module or not hasattr(api_module, '__hug__'):
        print("Error: must define a file name or module that contains a Hug API.")
        sys.exit(1)

    hug.API(api_module).http.serve(port, no_404_documentation)
