"""tests/test_test.py.

Test to ensure basic test functionality works as expected.

Copyright (C) 2019 Timothy Edmund Crosley

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
import pytest

import hug

api = hug.API(__name__)


def test_cli():
    """Test to ensure the CLI tester works as intended to allow testing CLI endpoints"""

    @hug.cli()
    def my_cli_function():
        return "Hello"

    assert hug.test.cli(my_cli_function) == "Hello"
    assert hug.test.cli("my_cli_function", api=api) == "Hello"

    # Shouldn't be able to specify both api and module.
    with pytest.raises(ValueError):
        assert hug.test.cli("my_method", api=api, module=hug)
