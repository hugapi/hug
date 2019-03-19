#!/usr/bin/env python
"""setup.py

Defines the setup instructions for the hug framework

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
import glob
import os
import sys
from os import path

from setuptools import Extension, setup

MYDIR = path.abspath(os.path.dirname(__file__))
CYTHON = False
JYTHON = 'java' in sys.platform

ext_modules = []
cmdclass = {}

try:
    sys.pypy_version_info
    PYPY = True
except AttributeError:
    PYPY = False

if not PYPY and not JYTHON:
    try:
        from Cython.Distutils import build_ext
        CYTHON = True
    except ImportError:
        CYTHON = False

if CYTHON:
    def list_modules(dirname):
        filenames = glob.glob(path.join(dirname, '*.py'))

        module_names = []
        for name in filenames:
            module, ext = path.splitext(path.basename(name))
            if module != '__init__':
                module_names.append(module)

        return module_names

    ext_modules = [
        Extension('hug.' + ext, [path.join('hug', ext + '.py')])
        for ext in list_modules(path.join(MYDIR, 'hug'))]
    cmdclass['build_ext'] = build_ext


with open('README.md', encoding='utf-8') as f:  # Loads in the README for PyPI
    long_description = f.read()


setup(
    name='hug',
    version='2.4.3',
    description='A Python framework that makes developing APIs '
                'as simple as possible, but no simpler.',
    long_description=long_description,
    # PEP 566, the new PyPI, and setuptools>=38.6.0 make markdown possible
    long_description_content_type='text/markdown',
    author='Timothy Crosley',
    author_email='timothy.crosley@gmail.com',
    # These appear in the left hand side bar on PyPI
    url='https://github.com/timothycrosley/hug',
    project_urls={
        'Documentation': 'http://www.hug.rest/',
        'Gitter': 'https://gitter.im/timothycrosley/hug',
    },
    license="MIT",
    entry_points={
        'console_scripts': [
            'hug = hug:development_runner.hug.interface.cli',
        ]
    },
    packages=['hug'],
    requires=['falcon', 'requests'],
    install_requires=['falcon==1.4.1', 'requests'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'mock', 'marshmallow'],
    ext_modules=ext_modules,
    cmdclass=cmdclass,
    python_requires=">=3.4",
    keywords='Web, Python, Python3, Refactoring, REST, Framework, RPC',
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities'
    ]
)
