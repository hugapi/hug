# HUG
Everyone needs a hug. Even API developers. Hug aims to make developing Python driven APIs as simple as possible, but no simpler. This one is for you :).
===================

[![PyPI version](https://badge.fury.io/py/hug.png)](http://badge.fury.io/py/hug)
[![PyPi downloads](https://pypip.in/d/hug/badge.png)](https://crate.io/packages/hug/)
[![Build Status](https://travis-ci.org/timothycrosley/hug.png?branch=master)](https://travis-ci.org/timothycrosley/hug)
[![License](https://img.shields.io/github/license/mashape/apistatus.svg)](https://pypi.python.org/pypi/hug/)

Hug drastically simplifies Python API development.

Hug's Design Objectives:

- Make developing a Python driven API as succint as a written definition.
- The framework should encourage code that self-documents.
- It should be fast. Never should a developer feel the need to look somewhere else for performance reasons.
- Writing tests for APIs written on-top of Hug should be easy and intuitive.
- Magic done once, in an API, is better then pushing the problem set to the user of the API.

Basic Example API
===================

happy_birthday.py

    """A basic (single function) API written using Hug"""
    import hug


    @hug.get('/happy_birthday')
    def happy_birthday(name, age:int, **kwargs):
        """Says happy birthday to a user"""
        return "Happy {age} Birthday {name}!".format(**locals())

To run the example:

    hug happy_birthday.py

Then you can access the example from localhost:8080/happy_birthday?name=Hug&age=1
Or access the documentation for your API from localhost:8080/documentation

Why Hug?
===================
HUG simply stands for Hopefully Useful Guide. This represents the projects goal to help guide developers into creating
well written and intuitive APIs.

--------------------------------------------

Thanks and I hope you find *this* hug helpful as you develop your next Python API!

~Timothy Crosley
