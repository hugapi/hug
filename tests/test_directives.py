"""tests/test_directives.py.

Tests to ensure that directives interact in the etimerpected mannor

Copyright (C) 2015 Timothy Edmund Crosley

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
import sys
import hug

api = sys.modules[__name__]


def test_timer():
    timer = hug.directives.timer()
    assert isinstance(timer.taken(), float)
    assert isinstance(timer.start, float)

    timer = hug.directives.timer('Time: {0}')
    assert isinstance(timer.taken(), str)
    assert isinstance(timer.start, float)

    @hug.get()
    def timer_tester(hug_timer):
        return hug_timer.taken()

    assert isinstance(hug.test.get(api, 'timer_tester').data, float)
    assert isinstance(timer_tester(), float)

