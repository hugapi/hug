"""tests/test_redirect.py.

Tests to ensure Hug's redirect methods work as expected

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
import falcon
import pytest
import hug.redirect


def test_to():
    '''Test that the base redirect to function works as expected'''
    with pytest.raises(falcon.http_status.HTTPStatus) as redirect:
        hug.redirect.to('/')
    assert '302' in redirect.value.status


def test_permanent():
    '''Test to ensure function causes a redirect with HTTP 301 status code'''
    with pytest.raises(falcon.http_status.HTTPStatus) as redirect:
        hug.redirect.permanent('/')
    assert '301' in redirect.value.status


def test_found():
    '''Test to ensure function causes a redirect with HTTP 302 status code'''
    with pytest.raises(falcon.http_status.HTTPStatus) as redirect:
        hug.redirect.found('/')
    assert '302' in redirect.value.status


def test_see_other():
    '''Test to ensure function causes a redirect with HTTP 303 status code'''
    with pytest.raises(falcon.http_status.HTTPStatus) as redirect:
        hug.redirect.see_other('/')
    assert '303' in redirect.value.status


def test_temporary():
    '''Test to ensure function causes a redirect with HTTP 307 status code'''
    with pytest.raises(falcon.http_status.HTTPStatus) as redirect:
        hug.redirect.temporary('/')
    assert '307' in redirect.value.status


def test_not_found():
    with pytest.raises(falcon.HTTPNotFound) as redirect:
        hug.redirect.not_found()
    assert '404' in redirect.value.status
