"""tests/test_full_request.py.

Test cases that rely on a command being ran against a running hug server

Copyright (C) 2016 Timothy Edmund Crosley

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
import platform
import time
from subprocess import Popen

import pytest
import requests

import hug

TEST_HUG_API = """
import hug


@hug.post("/test", output=hug.output_format.json)
def post(body, response):
    print(body)
    return {'message': 'ok'}
"""


@pytest.mark.skipif(
    platform.python_implementation() == "PyPy", reason="Can't run hug CLI from travis PyPy"
)
def test_hug_post(tmp_path):
    hug_test_file = tmp_path / "hug_postable.py"
    hug_test_file.write_text(TEST_HUG_API)
    hug_server = Popen(["hug", "-f", str(hug_test_file), "-p", "3000"])
    time.sleep(5)
    requests.post("http://127.0.0.1:3000/test", {"data": "here"})
    hug_server.kill()
