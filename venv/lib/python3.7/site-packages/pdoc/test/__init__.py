"""
Unit tests for pdoc package.
"""
import inspect
import os
import signal
import sys
import threading
import unittest
import warnings
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from functools import wraps
from glob import glob
from io import StringIO
from itertools import chain
from random import randint
from tempfile import TemporaryDirectory
from time import sleep
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import typing

import pdoc
from pdoc.cli import main, parser
from pdoc.html_helpers import (
    minify_css, minify_html, glimpse, to_html,
    ReferenceWarning, extract_toc,
)

TESTS_BASEDIR = os.path.abspath(os.path.dirname(__file__) or '.')
EXAMPLE_MODULE = 'example_pkg'

sys.path.insert(0, TESTS_BASEDIR)


@contextmanager
def temp_dir():
    with TemporaryDirectory(prefix='pdoc-test-') as path:
        yield path


@contextmanager
def chdir(path):
    old = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old)


def run(*args, _check=True, **kwargs) -> int:
    params = (('--' + key.replace('_', '-'), value)
              for key, value in kwargs.items())
    params = list(filter(None, chain.from_iterable(params)))  # type: ignore
    _args = parser.parse_args([*params, *args])               # type: ignore
    try:
        returncode = main(_args)
        return returncode or 0
    except SystemExit as e:
        return e.code


@contextmanager
def run_html(*args, **kwargs):
    with temp_dir() as path:
        run(*args, html=None, output_dir=path, **kwargs)
        with chdir(path):
            yield


@contextmanager
def redirect_streams():
    stdout, stderr = StringIO(), StringIO()
    with redirect_stderr(stderr), redirect_stdout(stdout):
        yield stdout, stderr


def ignore_warnings(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            func(*args, **kwargs)
    return wrapper


class CliTest(unittest.TestCase):
    """
    Command-line interface unit tests.
    """
    ALL_FILES = [
        'example_pkg',
        'example_pkg/index.html',
        'example_pkg/index.m.html',
        'example_pkg/module.html',
        'example_pkg/_private',
        'example_pkg/_private/index.html',
        'example_pkg/_private/module.html',
        'example_pkg/subpkg',
        'example_pkg/subpkg/_private.html',
        'example_pkg/subpkg/index.html',
        'example_pkg/subpkg2',
        'example_pkg/subpkg2/_private.html',
        'example_pkg/subpkg2/module.html',
        'example_pkg/subpkg2/index.html',
    ]
    PUBLIC_FILES = [f for f in ALL_FILES if '/_' not in f]

    def setUp(self):
        pdoc.reset()

    def _basic_html_assertions(self, expected_files=PUBLIC_FILES):
        # Output directory tree layout is as expected
        files = glob('**', recursive=True)
        self.assertEqual(sorted(files), sorted(expected_files))

    def _check_files(self, include_patterns=(), exclude_patterns=(), file_pattern='**/*.html'):
        files = glob(file_pattern, recursive=True)
        assert files
        for file in files:
            with open(file) as f:
                contents = f.read()
                for pattern in include_patterns:
                    self.assertIn(pattern, contents)
                for pattern in exclude_patterns:
                    self.assertNotIn(pattern, contents)

    def test_html(self):
        include_patterns = [
            'CONST docstring',
            'var docstring',
            'foreign_var',
            'foreign var docstring',
            'A',
            'A.overridden docstring',
            'A.overridden_same_docstring docstring',
            'A.inherited',
            'B docstring',
            'B.overridden docstring',
            'builtins.int',
            'External refs: ',
            '>sys.version<',
            'B.CONST docstring',
            'B.var docstring',
            'b=1',
            '*args',
            '**kwargs',
            'x, y, z, w',
            '__init__ docstring',
            'instance_var',
            'instance var docstring',
            'B.f docstring',
            'B.static docstring',
            'B.cls docstring',
            'B.p docstring',
            'B.C docstring',
            'B.overridden docstring',

            ' class="ident">static',
        ]
        exclude_patterns = [
            ' class="ident">_private',
            ' class="ident">_Private',
        ]
        package_files = {
            '': self.PUBLIC_FILES,
            '.subpkg2': [f for f in self.PUBLIC_FILES
                         if 'subpkg2' in f or f == EXAMPLE_MODULE],
            '._private': [f for f in self.ALL_FILES
                          if EXAMPLE_MODULE + '/_private' in f or f == EXAMPLE_MODULE],
        }
        for package, expected_files in package_files.items():
            with self.subTest(package=package):
                with run_html(EXAMPLE_MODULE + package):
                    self._basic_html_assertions(expected_files)
                    self._check_files(include_patterns, exclude_patterns)

        filenames_files = {
            ('module.py',): ['module.html'],
            ('module.py', 'subpkg2'): ['module.html', 'subpkg2',
                                       'subpkg2/index.html', 'subpkg2/module.html'],
        }
        with chdir(TESTS_BASEDIR):
            for filenames, expected_files in filenames_files.items():
                with self.subTest(filename=','.join(filenames)):
                    with run_html(*(os.path.join(EXAMPLE_MODULE, f) for f in filenames)):
                        self._basic_html_assertions(expected_files)
                        self._check_files(include_patterns, exclude_patterns)

    def test_html_multiple_files(self):
        with chdir(TESTS_BASEDIR):
            with run_html(EXAMPLE_MODULE + '/module.py', EXAMPLE_MODULE + '/subpkg2'):
                self._basic_html_assertions(
                    ['module.html', 'subpkg2', 'subpkg2/index.html', 'subpkg2/module.html'])

    def test_html_identifier(self):
        for package in ('', '._private'):
            with self.subTest(package=package), \
                 self.assertWarns(UserWarning) as cm:
                with run_html(EXAMPLE_MODULE + package, filter='A',
                              config='show_source_code=False'):
                    self._check_files(['A'], ['CONST', 'B docstring'])
        self.assertIn('__pdoc__', cm.warning.args[0])

    def test_html_ref_links(self):
        with run_html(EXAMPLE_MODULE, config='show_source_code=False'):
            self._check_files(
                file_pattern=EXAMPLE_MODULE + '/index.html',
                include_patterns=[
                    'href="#example_pkg.B">',
                    'href="#example_pkg.A">',
                ],
            )

    def test_html_no_source(self):
        with self.assertWarns(DeprecationWarning),\
                run_html(EXAMPLE_MODULE, html_no_source=None):
            self._basic_html_assertions()
            self._check_files(exclude_patterns=['class="source"', 'Hidden'])

    def test_force(self):
        with run_html(EXAMPLE_MODULE):
            with redirect_streams() as (stdout, stderr):
                returncode = run(EXAMPLE_MODULE, _check=False, html=None, output_dir=os.getcwd())
                self.assertNotEqual(returncode, 0)
                self.assertNotEqual(stderr.getvalue(), '')

            with redirect_streams() as (stdout, stderr):
                returncode = run(EXAMPLE_MODULE, html=None, force=None, output_dir=os.getcwd())
                self.assertEqual(returncode, 0)
                self.assertEqual(stderr.getvalue(), '')

    def test_external_links(self):
        with run_html(EXAMPLE_MODULE):
            self._basic_html_assertions()
            self._check_files(exclude_patterns=['<a href="/sys.version.ext"'])

        with self.assertWarns(DeprecationWarning),\
                run_html(EXAMPLE_MODULE, external_links=None):
            self._basic_html_assertions()
            self._check_files(['<a title="sys.version" href="/sys.version.ext"'])

    def test_template_dir(self):
        old_tpl_dirs = pdoc.tpl_lookup.directories.copy()
        # Prevent loading incorrect template cached from prev runs
        pdoc.tpl_lookup._collection.clear()
        try:
            with run_html(EXAMPLE_MODULE, template_dir=TESTS_BASEDIR):
                self._basic_html_assertions()
                self._check_files(['FOOBAR', '/* Empty CSS */'], ['coding: utf-8'])
        finally:
            pdoc.tpl_lookup.directories = old_tpl_dirs
            pdoc.tpl_lookup._collection.clear()

    def test_link_prefix(self):
        with self.assertWarns(DeprecationWarning),\
                run_html(EXAMPLE_MODULE, link_prefix='/foobar/'):
            self._basic_html_assertions()
            self._check_files(['/foobar/' + EXAMPLE_MODULE])

    def test_text(self):
        include_patterns = [
            'CONST docstring',
            'var docstring',
            'foreign_var',
            'foreign var docstring',
            'A',
            'A.overridden docstring',
            'A.overridden_same_docstring docstring',
            'A.inherited',
            'B docstring',
            'B.overridden docstring',
            'builtins.int',
            'External refs: ',
            'sys.version',
            'B.CONST docstring',
            'B.var docstring',
            'x, y, z, w',
            '__init__ docstring',
            'instance_var',
            'instance var docstring',
            'b=1',
            '*args',
            '**kwargs',
            'B.f docstring',
            'B.static docstring',
            'B.cls docstring',
            'B.p docstring',
            'C',
            'B.overridden docstring',
        ]
        exclude_patterns = [
            '_private',
            '_Private',
            'subprocess',
            'Hidden',
        ]

        with self.subTest(package=EXAMPLE_MODULE):
            with redirect_streams() as (stdout, _):
                run(EXAMPLE_MODULE)
                out = stdout.getvalue()

            header = 'Module {}\n{:=<{}}'.format(EXAMPLE_MODULE, '',
                                                 len('Module ') + len(EXAMPLE_MODULE))
            self.assertIn(header, out)
            for pattern in include_patterns:
                self.assertIn(pattern, out)
            for pattern in exclude_patterns:
                self.assertNotIn(pattern, out)

        with chdir(TESTS_BASEDIR):
            for files in (('module.py',),
                          ('module.py', 'subpkg2')):
                with self.subTest(filename=','.join(files)):
                    with redirect_streams() as (stdout, _):
                        run(*(os.path.join(EXAMPLE_MODULE, f) for f in files))
                        out = stdout.getvalue()
                    for f in files:
                        header = 'Module {}\n'.format(os.path.splitext(f)[0])
                        self.assertIn(header, out)

    def test_text_identifier(self):
        with redirect_streams() as (stdout, _):
            run(EXAMPLE_MODULE, filter='A')
            out = stdout.getvalue()
        self.assertIn('A', out)
        self.assertIn('### Descendants\n\n    * example_pkg.B', out)
        self.assertNotIn('CONST', out)
        self.assertNotIn('B docstring', out)

    def test_pdf(self):
        with redirect_streams() as (stdout, stderr):
            run('pdoc', pdf=None)
            out = stdout.getvalue()
            err = stderr.getvalue()
        self.assertIn('pdoc3.github.io', out)
        self.assertIn('pandoc', err)

        self.assertIn(str(inspect.signature(pdoc.Doc.__init__)).replace('self, ', ''),
                      out)

    def test_config(self):
        with run_html(EXAMPLE_MODULE, config='link_prefix="/foobar/"'):
            self._basic_html_assertions()
            self._check_files(['/foobar/' + EXAMPLE_MODULE])

    def test_output_text(self):
        with temp_dir() as path:
            run(EXAMPLE_MODULE, output_dir=path)
            with chdir(path):
                self._basic_html_assertions([file.replace('.html', '.md')
                                             for file in self.PUBLIC_FILES])

    def test_google_analytics(self):
        expected = ['google-analytics.com']
        with run_html(EXAMPLE_MODULE):
            self._check_files((), exclude_patterns=expected)
        with run_html(EXAMPLE_MODULE, config='google_analytics="UA-xxxxxx-y"'):
            self._check_files(expected)


class ApiTest(unittest.TestCase):
    """
    Programmatic/API unit tests.
    """
    def setUp(self):
        pdoc.reset()

    def test_module(self):
        modules = {
            EXAMPLE_MODULE: ('', ('index', 'module', 'subpkg', 'subpkg2')),
            EXAMPLE_MODULE + '.subpkg2': ('.subpkg2', ('subpkg2.module',)),
        }
        with chdir(TESTS_BASEDIR):
            for module, (name_suffix, submodules) in modules.items():
                with self.subTest(module=module):
                    m = pdoc.Module(pdoc.import_module(module))
                    self.assertEqual(repr(m), "<Module '{}'>".format(m.obj.__name__))
                    self.assertEqual(m.name, EXAMPLE_MODULE + name_suffix)
                    self.assertEqual(sorted(m.name for m in m.submodules()),
                                     [EXAMPLE_MODULE + '.' + m for m in submodules])

    def test_import_filename(self):
        with patch.object(sys, 'path', ['']), \
             chdir(os.path.join(TESTS_BASEDIR, EXAMPLE_MODULE)):
            pdoc.import_module('index')

    def test_imported_once(self):
        with chdir(os.path.join(TESTS_BASEDIR, EXAMPLE_MODULE)):
            pdoc.import_module('_imported_once.py')

    def test_namespace(self):
        # Test the three namespace types
        # https://packaging.python.org/guides/packaging-namespace-packages/#creating-a-namespace-package
        for i in range(1, 4):
            path = os.path.join(TESTS_BASEDIR, EXAMPLE_MODULE, '_namespace', str(i))
            with patch.object(sys, 'path', [os.path.join(path, 'a'),
                                            os.path.join(path, 'b')]):
                mod = pdoc.Module(pdoc.import_module('a.main'))
                self.assertIn('D', mod.doc)

    def test_module_allsubmodules(self):
        m = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE + '._private'))
        self.assertEqual(sorted(m.name for m in m.submodules()),
                         [EXAMPLE_MODULE + '._private.module'])

    def test_instance_var(self):
        pdoc.reset()
        mod = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))
        var = mod.doc['B'].doc['instance_var']
        self.assertTrue(var.instance_var)

    def test_builtin_methoddescriptors(self):
        import parser
        with self.assertWarns(UserWarning):
            c = pdoc.Class('STType', pdoc.Module(parser), parser.STType)
        self.assertIsInstance(c.doc['compile'], pdoc.Function)

    def test_refname(self):
        mod = EXAMPLE_MODULE + '.' + 'subpkg'
        module = pdoc.Module(pdoc.import_module(mod))
        var = module.doc['var']
        cls = module.doc['B']
        nested_cls = cls.doc['C']
        cls_var = cls.doc['var']
        method = cls.doc['f']

        self.assertEqual(pdoc.External('foo').refname, 'foo')
        self.assertEqual(module.refname, mod)
        self.assertEqual(var.refname, mod + '.var')
        self.assertEqual(cls.refname, mod + '.B')
        self.assertEqual(nested_cls.refname, mod + '.B.C')
        self.assertEqual(cls_var.refname, mod + '.B.var')
        self.assertEqual(method.refname, mod + '.B.f')

        # Inherited method's refname points to class' implicit copy
        pdoc.link_inheritance()
        self.assertEqual(cls.doc['inherited'].refname, mod + '.B.inherited')

    def test_qualname(self):
        module = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))
        var = module.doc['var']
        cls = module.doc['B']
        nested_cls = cls.doc['C']
        cls_var = cls.doc['var']
        method = cls.doc['f']

        self.assertEqual(pdoc.External('foo').qualname, 'foo')
        self.assertEqual(module.qualname, EXAMPLE_MODULE)
        self.assertEqual(var.qualname, 'var')
        self.assertEqual(cls.qualname, 'B')
        self.assertEqual(nested_cls.qualname, 'B.C')
        self.assertEqual(cls_var.qualname, 'B.var')
        self.assertEqual(method.qualname, 'B.f')

    def test__pdoc__dict(self):
        module = pdoc.import_module(EXAMPLE_MODULE)
        with patch.object(module, '__pdoc__', {'B': False}):
            mod = pdoc.Module(module)
            pdoc.link_inheritance()
            self.assertIn('A', mod.doc)
            self.assertNotIn('B', mod.doc)

        with patch.object(module, '__pdoc__', {'B.f': False}):
            mod = pdoc.Module(module)
            pdoc.link_inheritance()
            self.assertIn('B', mod.doc)
            self.assertNotIn('f', mod.doc['B'].doc)
            self.assertIsInstance(mod.find_ident('B.f'), pdoc.External)

    def test__pdoc__invalid_value(self):
        module = pdoc.import_module(EXAMPLE_MODULE)
        with patch.object(module, '__pdoc__', {'B': 1}), \
                self.assertRaises(ValueError):
            pdoc.Module(module)
            pdoc.link_inheritance()

    def test__all__(self):
        module = pdoc.import_module(EXAMPLE_MODULE + '.index')
        with patch.object(module, '__all__', ['B'], create=True):
            mod = pdoc.Module(module)
            with self.assertWarns(UserWarning):  # Only B is used but __pdoc__ contains others
                pdoc.link_inheritance()
            self.assertEqual(list(mod.doc.keys()), ['B'])

    def test_find_ident(self):
        mod = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))
        self.assertIsInstance(mod.find_ident('subpkg'), pdoc.Module)
        mod = pdoc.Module(pdoc)
        self.assertIsInstance(mod.find_ident('subpkg'), pdoc.External)

        self.assertIsInstance(mod.find_ident(EXAMPLE_MODULE + '.subpkg'), pdoc.Module)

        nonexistent = 'foo()'
        result = mod.find_ident(nonexistent)
        self.assertIsInstance(result, pdoc.External)
        self.assertEqual(result.name, nonexistent)

        # Ref by class __init__
        mod = pdoc.Module(pdoc)
        self.assertIs(mod.find_ident('pdoc.Doc.__init__').obj, pdoc.Doc)

    def test_inherits(self):
        module = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))
        pdoc.link_inheritance()

        a = module.doc['A']
        b = module.doc['B']
        self.assertEqual(b.doc['inherited'].inherits,
                         a.doc['inherited'])
        self.assertEqual(b.doc['overridden_same_docstring'].inherits,
                         a.doc['overridden_same_docstring'])
        self.assertEqual(b.doc['overridden'].inherits,
                         None)

        c = module.doc['C']
        d = module.doc['D']
        self.assertEqual(d.doc['overridden'].inherits, c.doc['overridden'])
        self.assertEqual(c.doc['overridden'].inherits, b.doc['overridden'])

    def test_inherited_members(self):
        mod = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))
        pdoc.link_inheritance()
        a = mod.doc['A']
        b = mod.doc['B']
        self.assertEqual(b.inherited_members(), [(a, [a.doc['inherited'],
                                                      a.doc['overridden_same_docstring']])])
        self.assertEqual(a.inherited_members(), [])

    @ignore_warnings
    def test_subclasses(self):
        class A:
            pass

        class B(type):
            pass

        class C(A):
            pass

        class D(B):
            pass

        mod = pdoc.Module(pdoc)
        self.assertEqual([x.refname for x in pdoc.Class('A', mod, A).subclasses()],
                         [mod.find_class(C).refname])
        self.assertEqual([x.refname for x in pdoc.Class('B', mod, B).subclasses()],
                         [mod.find_class(D).refname])

    def test_link_inheritance(self):
        mod = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))
        with warnings.catch_warnings(record=True) as w:
            pdoc.link_inheritance()
            pdoc.link_inheritance()
        self.assertFalse(w)

        mod._is_inheritance_linked = False
        with self.assertWarns(UserWarning):
            pdoc.link_inheritance()

        # Test inheritance across modules
        pdoc.reset()
        mod = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE + '._test_linking'))
        pdoc.link_inheritance()
        a = mod.doc['a'].doc['A']
        b = mod.doc['b'].doc['B']
        c = mod.doc['b'].doc['c'].doc['C']
        self.assertEqual(b.doc['a'].inherits, a.doc['a'])
        self.assertEqual(b.doc['c'].inherits, c.doc['c'])
        # While classes do inherit from superclasses, they just shouldn't always
        # say so, because public classes do want to be exposed and linked to
        self.assertNotEqual(b.inherits, a)

    def test_context(self):
        context = {}
        pdoc.Module(pdoc, context=context)
        self.assertIn('pdoc', context)
        self.assertIn('pdoc.cli', context)
        self.assertIn('pdoc.cli.main', context)
        self.assertIn('pdoc.Module', context)
        self.assertIsInstance(context['pdoc'], pdoc.Module)
        self.assertIsInstance(context['pdoc.cli'], pdoc.Module)
        self.assertIsInstance(context['pdoc.cli.main'], pdoc.Function)
        self.assertIsInstance(context['pdoc.Module'], pdoc.Class)

        module = pdoc.Module(pdoc)
        self.assertIsInstance(module.find_ident('pdoc.Module'), pdoc.Class)
        pdoc.reset()
        self.assertIsInstance(module.find_ident('pdoc.Module'), pdoc.External)

    def test_Function_params(self):
        mod = pdoc.Module(pdoc)
        func = pdoc.Function('f', mod,
                             lambda a, _a, _b=None: None)
        self.assertEqual(func.params(), ['a', '_a'])

        func = pdoc.Function('f', mod,
                             lambda _ok, a, _a, *args, _b=None, c=None, _d=None: None)
        self.assertEqual(func.params(), ['_ok', 'a', '_a', '*args', 'c=None'])

        func = pdoc.Function('f', mod,
                             lambda a, b, *, _c=1: None)
        self.assertEqual(func.params(), ['a', 'b'])

        func = pdoc.Function('f', mod,
                             lambda a, *, b, c: None)
        self.assertEqual(func.params(), ['a', '*', 'b', 'c'])

        func = pdoc.Function('f', mod,
                             lambda a=os.environ: None)
        self.assertEqual(func.params(), ['a=os.environ'])

        # typed
        def f(a: int, *b, c: typing.List[pdoc.Doc] = []): pass
        func = pdoc.Function('f', mod, f)
        self.assertEqual(func.params(), ['a', '*b', "c=[]"])
        self.assertEqual(func.params(annotate=True),
                         ['a:\N{NBSP}int', '*b', "c:\N{NBSP}List[pdoc.Doc]\N{NBSP}=\N{NBSP}[]"])

        # typed, linked
        def link(dobj):
            return '<a href="{}">{}</a>'.format(dobj.url(relative_to=mod), dobj.qualname)

        self.assertEqual(func.params(annotate=True, link=link),
                         ['a:\N{NBSP}int', '*b',
                          "c:\N{NBSP}List[<a href=\"#pdoc.Doc\">Doc</a>]\N{NBSP}=\N{NBSP}[]"])

    def test_Function_return_annotation(self):
        import typing

        def f() -> typing.List[typing.Union[str, pdoc.Doc]]: pass
        func = pdoc.Function('f', pdoc.Module(pdoc), f)
        self.assertEqual(func.return_annotation(), 'List[Union[str,\N{NBSP}pdoc.Doc]]')

    @ignore_warnings
    def test_Class_docstring(self):
        class A:
            """foo"""

        class B:
            def __init__(self):
                """foo"""

        class C:
            """foo"""
            def __init__(self):
                """bar"""

        class D(C):
            """baz"""

        class E(C):
            def __init__(self):
                """baz"""

        self.assertEqual(pdoc.Class('A', pdoc.Module(pdoc), A).docstring, """foo""")
        self.assertEqual(pdoc.Class('B', pdoc.Module(pdoc), B).docstring, """foo""")
        self.assertEqual(pdoc.Class('C', pdoc.Module(pdoc), C).docstring, """foo\n\nbar""")
        self.assertEqual(pdoc.Class('D', pdoc.Module(pdoc), D).docstring, """baz\n\nbar""")
        self.assertEqual(pdoc.Class('E', pdoc.Module(pdoc), E).docstring, """foo\n\nbaz""")

    @ignore_warnings
    def test_Class_params(self):
        class C:
            def __init__(self, x):
                pass

        mod = pdoc.Module(pdoc)
        self.assertEqual(pdoc.Class('C', mod, C).params(), ['x'])
        with patch.dict(mod.obj.__pdoc__, {'C.__init__': False}):
            self.assertEqual(pdoc.Class('C', mod, C).params(), [])

    def test_url(self):
        mod = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))
        pdoc.link_inheritance()

        c = mod.doc['D']
        self.assertEqual(c.url(), 'example_pkg/index.html#example_pkg.D')
        self.assertEqual(c.url(link_prefix='/'), '/example_pkg/index.html#example_pkg.D')
        self.assertEqual(c.url(relative_to=c.module), '#example_pkg.D')
        self.assertEqual(c.url(top_ancestor=True), c.url())  # Public classes do link to themselves

        f = c.doc['overridden']
        self.assertEqual(f.url(), 'example_pkg/index.html#example_pkg.D.overridden')
        self.assertEqual(f.url(link_prefix='/'), '/example_pkg/index.html#example_pkg.D.overridden')
        self.assertEqual(f.url(relative_to=c.module), '#example_pkg.D.overridden')
        self.assertEqual(f.url(top_ancestor=1), 'example_pkg/index.html#example_pkg.B.overridden')

    @unittest.skipIf(sys.version_info < (3, 6), reason="only deterministic on CPython 3.6+")
    def test_sorting(self):
        module = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))

        sorted_variables = module.variables()
        unsorted_variables = module.variables(sort=False)
        self.assertNotEqual(sorted_variables, unsorted_variables)
        self.assertEqual(sorted_variables, sorted(unsorted_variables))

        sorted_functions = module.functions()
        unsorted_functions = module.functions(sort=False)
        self.assertNotEqual(sorted_functions, unsorted_functions)
        self.assertEqual(sorted_functions, sorted(unsorted_functions))

        sorted_classes = module.classes()
        unsorted_classes = module.classes(sort=False)
        self.assertNotEqual(sorted_classes, unsorted_classes)
        self.assertEqual(sorted_classes, sorted(unsorted_classes))

        cls = module.doc["Docformats"]

        sorted_methods = cls.methods()
        unsorted_methods = cls.methods(sort=False)
        self.assertNotEqual(sorted_methods, unsorted_methods)
        self.assertEqual(sorted_methods, sorted(unsorted_methods))

    def test_module_init(self):
        mod = pdoc.Module(pdoc.import_module('pdoc.__init__'))
        self.assertEqual(mod.name, 'pdoc')
        self.assertIn('Module', mod.doc)


class HtmlHelpersTest(unittest.TestCase):
    """
    Unit tests for helper functions for producing HTML.
    """
    def test_minify_css(self):
        css = 'a { color: white; } /*comment*/ b {;}'
        minified = minify_css(css)
        self.assertNotIn(' ', minified)
        self.assertNotIn(';}', minified)
        self.assertNotIn('*', minified)

    def test_minify_html(self):
        html = '  <p>   a   </p>    <pre>    a\n    b</pre>    c   \n    d   '
        expected = '\n<p>\na\n</p>\n<pre>    a\n    b</pre>\nc\nd\n'
        minified = minify_html(html)
        self.assertEqual(minified, expected)

    def test_glimpse(self):
        text = 'foo bar\n\nbaz'
        self.assertEqual(glimpse(text), 'foo bar …')
        self.assertEqual(glimpse(text, max_length=8, paragraph=False), 'foo …')
        self.assertEqual(glimpse('Foo bar\n-------'), 'Foo bar')

    def test_to_html(self):
        text = '# Title\n\n`pdoc.Module` is a `Doc`, not `dict`.'
        expected = ('<h1 id="title">Title</h1>\n'
                    '<p><a href="#pdoc.Module">Module</a> is a <a href="#pdoc.Doc">Doc</a>, '
                    'not <code>dict</code>.</p>')

        module = pdoc.Module(pdoc)

        def link(dobj, *args, **kwargs):
            return '<a href="{}">{}</a>'.format(dobj.url(relative_to=module), dobj.qualname)

        html = to_html(text, module=module, link=link)
        self.assertEqual(html, expected)

        self.assertIn('<a href=', to_html('`pdoc.Doc.url()`', module=module, link=link))

        self.assertIn('<code>foo.f()</code>', to_html('`foo.f()`', module=module, link=link))

    def test_to_html_refname_warning(self):
        mod = pdoc.Module(pdoc.import_module(EXAMPLE_MODULE))

        def f():
            """Reference to some `example_pkg.nonexisting` object"""

        mod.doc['__f'] = pdoc.Function('__f', mod, f)
        with self.assertWarns(ReferenceWarning) as cm:
            mod.html()
        del mod.doc['__f']
        self.assertIn('example_pkg.nonexisting', cm.warning.args[0])

    def test_extract_toc(self):
        text = 'xxx\n\n# Title\n\nfoo\n\n## Subtitle\n\nbar'
        expected = '''<div class="toc">
<ul>
<li><a href="#title">Title</a><ul>
<li><a href="#subtitle">Subtitle</a></li>
</ul>
</li>
</ul>
</div>'''
        toc = extract_toc(text)
        self.assertEqual(toc, expected)


class Docformats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._module = pdoc.Module(pdoc)
        cls._docmodule = pdoc.import_module(EXAMPLE_MODULE)

    @staticmethod
    def _link(dobj, *args, **kwargs):
        return '<a>`{}`</a>'.format(dobj.refname)

    def test_numpy(self):
        expected = '''<p>Summary line.</p>
<p><strong>Documentation</strong>: <a href="https://pdoc3.github.io/pdoc/doc/pdoc/">https://pdoc3.github.io/pdoc/doc/pdoc/</a>
<strong>Source Code</strong>: <a href="https://github.com/pdoc3/">https://github.com/pdoc3/</a></p>
<h2 id="parameters">Parameters</h2>
<dl>
<dt><strong><code>x1</code></strong>, <strong><code>x2</code></strong> :&ensp;<code>array_like</code></dt>
<dd>
<p>Input arrays,
description of <code>x1</code>, <code>x2</code>.</p>
<div class="admonition versionadded">
<p class="admonition-title">Added in version:&ensp;1.5.0</p>
</div>
</dd>
<dt><strong><code>x</code></strong> :&ensp;{ <code>NoneType</code>, <code>'B'</code>, <code>'C'</code> }, optional</dt>
<dd>&nbsp;</dd>
<dt><strong><code>n</code></strong> :&ensp;<code>int</code> or <code>list</code> of <code>int</code></dt>
<dd>Description of num</dd>
<dt><strong><code>*args</code></strong>, <strong><code>**kwargs</code></strong></dt>
<dd>Passed on.</dd>
</dl>
<h2 id="returns">Returns</h2>
<dl>
<dt><strong><code>output</code></strong> :&ensp;<a><code>pdoc.Doc</code></a></dt>
<dd>The output array</dd>
<dt><code>foo</code></dt>
<dd>&nbsp;</dd>
</dl>
<h2 id="returns_1">Returns</h2>
<dl>
<dt><a><code>pdoc.Doc</code></a></dt>
<dd>The output array</dd>
</dl>
<h2 id="raises">Raises</h2>
<dl>
<dt><code>TypeError</code></dt>
<dd>When something.</dd>
</dl>
<h2 id="raises_1">Raises</h2>
<dl>
<dt><code>TypeError</code></dt>
<dd>&nbsp;</dd>
</dl>
<h2 id="returns_2">Returns</h2>
<p>None.</p>
<h2 id="invalid">Invalid</h2>
<p>no match</p>
<h2 id="see-also">See Also</h2>
<p><code>fromstring</code>, <code>loadtxt</code></p>
<h2 id="see-also_1">See Also</h2>
<dl>
<dt><a><code>pdoc.text</code></a></dt>
<dd>Function a with its description.</dd>
<dt><a><code>scipy.random.norm</code></a></dt>
<dd>Random variates, PDFs, etc.</dd>
</dl>
<h2 id="notes">Notes</h2>
<p>Foo bar.</p>
<h3 id="h3-title">H3 Title</h3>
<p>Foo bar.</p>'''  # noqa: E501
        text = inspect.getdoc(self._docmodule.numpy)
        html = to_html(text, module=self._module, link=self._link)
        self.assertEqual(html, expected)

    def test_google(self):
        expected = '''<p>Summary line.
Nomatch:</p>
<h2 id="args">Args</h2>
<dl>
<dt><strong><code>arg1</code></strong> :&ensp;<code>str</code>, optional</dt>
<dd>Text1</dd>
<dt><strong><code>arg2</code></strong> :&ensp;<code>List</code>[<code>str</code>], optional,\
 default=<code>10</code></dt>
<dd>Text2</dd>
</dl>
<h2 id="args_1">Args</h2>
<dl>
<dt><strong><code>arg1</code></strong> :&ensp;<code>int</code></dt>
<dd>Description of arg1</dd>
<dt><strong><code>arg2</code></strong> :&ensp;<code>str</code> or <code>int</code></dt>
<dd>Description of arg2</dd>
<dt><strong><code>test_sequence</code></strong></dt>
<dd>
<p>2-dim numpy array of real numbers, size: N * D
- the test observation sequence.</p>
<pre><code>test_sequence =
code
</code></pre>
<p>Continue.</p>
</dd>
<dt><strong><code>*args</code></strong></dt>
<dd>passed around</dd>
</dl>
<h2 id="returns">Returns</h2>
<dl>
<dt><strong><code>issue_10</code></strong></dt>
<dd>description didn't work across multiple lines
if only a single item was listed. <code>inspect.cleandoc()</code>
somehow stripped the required extra indentation.</dd>
</dl>
<h2 id="raises">Raises</h2>
<dl>
<dt><strong><code>AttributeError</code></strong></dt>
<dd>
<p>The <code>Raises</code> section is a list of all exceptions
that are relevant to the interface.</p>
<p>and a third line.</p>
</dd>
<dt><strong><code>ValueError</code></strong></dt>
<dd>If <code>arg2</code> is equal to <code>arg1</code>.</dd>
</dl>
<p>Test a title without a blank line before it.</p>
<h2 id="args_2">Args</h2>
<dl>
<dt><strong><code>A</code></strong></dt>
<dd>a</dd>
</dl>
<h2 id="examples">Examples</h2>
<p>Examples in doctest format.</p>
<pre><code>&gt;&gt;&gt; a = [1,2,3]
</code></pre>
<h2 id="todos">Todos</h2>
<ul>
<li>For module TODOs</li>
</ul>'''
        text = inspect.getdoc(self._docmodule.google)
        html = to_html(text, module=self._module, link=self._link)
        self.assertEqual(html, expected)

    def test_doctests(self):
        expected = '''<p>Need an intro paragrapgh.</p>
<pre><code>&gt;&gt;&gt; Then code is indented one level
</code></pre>
<p>Alternatively</p>
<pre><code>fenced code works
</code></pre>

<h2 id="examples">Examples</h2>
<pre><code>&gt;&gt;&gt; nbytes(100)
'100.0 bytes'

&gt;&gt;&gt; asdf
</code></pre>'''
        text = inspect.getdoc(self._docmodule.doctests)
        html = to_html(text, module=self._module, link=self._link)
        self.assertEqual(html, expected)

    def test_reST_directives(self):
        expected = '''<div class="admonition todo">
<p class="admonition-title">TODO</p>
<p>Create something.</p>
</div>
<div class="admonition admonition">
<p class="admonition-title">Example</p>
<p>Image shows something.</p>
<p><img alt="" src="https://www.debian.org/logos/openlogo-nd-100.png"></p>
<div class="admonition note">
<p class="admonition-title">Note</p>
<p>Can only nest admonitions two levels.</p>
</div>
</div>
<p><img alt="" src="https://www.debian.org/logos/openlogo-nd-100.png"></p>
<p>Now you know.</p>
<div class="admonition warning">
<p class="admonition-title">Warning</p>
<p>Some warning
lines.</p>
</div>
<ul>
<li>
<p>Describe some func in a list
  across multiple lines:</p>
<div class="admonition deprecated">
<p class="admonition-title">Deprecated since version:&ensp;3.1</p>
<p>Use <code>spam</code> instead.</p>
</div>
<div class="admonition versionadded">
<p class="admonition-title">Added in version:&ensp;2.5</p>
<p>The <em>spam</em> parameter.</p>
</div>
</li>
</ul>
<div class="admonition caution">
<p class="admonition-title">Caution</p>
<p>Don't touch this!</p>
</div>'''
        text = inspect.getdoc(self._docmodule.reST_directives)
        html = to_html(text, module=self._module, link=self._link)
        self.assertEqual(html, expected)

    def test_reST_include(self):
        expected = '''<pre><code class="python">    x = 2
</code></pre>

<p>1
x = 2
x = 3
x =</p>'''
        mod = pdoc.Module(pdoc.import_module(
            os.path.join(TESTS_BASEDIR, EXAMPLE_MODULE, '_reST_include', 'test.py')))
        text = inspect.getdoc(mod.obj)
        html = to_html(text, module=mod)
        self.assertEqual(html, expected)

        # Ensure includes are resolved within docstrings already,
        # e.g. for `pdoc.html_helpers.extract_toc()` to work
        self.assertIn('Command-line interface',
                      pdoc.Module(pdoc.import_module(pdoc)).docstring)

    def test_urls(self):
        text = """Beautiful Soup
http://www.foo.bar
http://www.foo.bar?q="foo"
<a href="https://travis-ci.org/cs01/pygdbmi"><img src="https://foo" /></a>
<https://foo.bar>

Work [like this](http://foo/) and [like that].

[like that]: ftp://bar

data:text/plain;base64,SGVsbG8sIFdvcmxkIQ%3D%3D"""
        expected = """<p>Beautiful Soup
<a href="http://www.foo.bar">http://www.foo.bar</a>
<a href="http://www.foo.bar?q=&quot;foo&quot;">http://www.foo.bar?q="foo"</a>
<a href="https://travis-ci.org/cs01/pygdbmi"><img src="https://foo" /></a>
<a href="https://foo.bar">https://foo.bar</a></p>
<p>Work <a href="http://foo/">like this</a> and <a href="ftp://bar">like that</a>.</p>
<p>data:text/plain;base64,SGVsbG8sIFdvcmxkIQ%3D%3D</p>"""
        html = to_html(text)
        self.assertEqual(html, expected)

    def test_latex_math(self):
        expected = r'''<p>Inline equation: <span><span class="MathJax_Preview"> v_t *\frac{1}{2}* j_i + [a] &lt; 3 </span><script type="math/tex"> v_t *\frac{1}{2}* j_i + [a] < 3 </script></span>.</p>
<p>Block equation: <span><span class="MathJax_Preview"> v_t *\frac{1}{2}* j_i + [a] &lt; 3 </span><script type="math/tex; mode=display"> v_t *\frac{1}{2}* j_i + [a] < 3 </script></span></p>
<p>Block equation: <span><span class="MathJax_Preview"> v_t *\frac{1}{2}* j_i + [a] &lt; 3 </span><script type="math/tex; mode=display"> v_t *\frac{1}{2}* j_i + [a] < 3 </script></span></p>
<p><span><span class="MathJax_Preview"> v_t *\frac{1}{2}* j_i + [a] &lt; 3 </span><script type="math/tex; mode=display"> v_t *\frac{1}{2}* j_i + [a] < 3 </script></span></p>'''  # noqa: E501
        text = inspect.getdoc(self._docmodule.latex_math)
        html = to_html(text, module=self._module, link=self._link, latex_math=True)
        self.assertEqual(html, expected)


class HttpTest(unittest.TestCase):
    """
    Unit tests for the HTTP server functionality.
    """
    @contextmanager
    def _timeout(self, secs):
        def _raise(*_):
            raise TimeoutError

        signal.signal(signal.SIGALRM, _raise)
        signal.alarm(secs)
        yield
        signal.alarm(0)

    @contextmanager
    def _http(self, modules: list):
        port = randint(9000, 12000)

        with self._timeout(1000):
            with redirect_streams() as (stdout, stderr):
                t = threading.Thread(
                    target=main, args=(parser.parse_args(['--http', ':%d' % port] + modules),))
                t.start()
                sleep(.1)

                if not t.is_alive():
                    sys.__stderr__.write(stderr.getvalue())
                    raise AssertionError

                try:
                    yield 'http://localhost:{}/'.format(port)
                except Exception:
                    sys.__stderr__.write(stderr.getvalue())
                    sys.__stdout__.write(stdout.getvalue())
                    raise
                finally:
                    pdoc.cli._httpd.shutdown()  # type: ignore
                    t.join()

    def test_http(self):
        with self._http(['pdoc', os.path.join(TESTS_BASEDIR, EXAMPLE_MODULE)]) as url:
            with self.subTest(url='/'):
                with urlopen(url, timeout=3) as resp:
                    html = resp.read()
                    self.assertIn(b'Python package <code>pdoc</code>', html)
                    self.assertNotIn(b'gzip', html)
            with self.subTest(url='/' + EXAMPLE_MODULE):
                with urlopen(url + 'pdoc', timeout=3) as resp:
                    html = resp.read()
                    self.assertIn(b'__pdoc__', html)
            with self.subTest(url='/csv.ext'):
                with urlopen(url + 'csv.ext', timeout=3) as resp:
                    html = resp.read()
                    self.assertIn(b'DictReader', html)

    def test_file(self):
        with chdir(os.path.join(TESTS_BASEDIR, EXAMPLE_MODULE)):
            with self._http(['_relative_import']) as url:
                with urlopen(url, timeout=3) as resp:
                    html = resp.read()
                    self.assertIn(b'<a href="/_relative_import">', html)

    def test_head(self):
        with self._http(['pdoc']) as url:
            with urlopen(Request(url + 'pdoc/',
                                 method='HEAD',
                                 headers={'If-None-Match': 'xxx'})) as resp:
                self.assertEqual(resp.status, 205)
            with self.assertRaises(HTTPError) as cm:
                urlopen(Request(url + 'pdoc/',
                                method='HEAD',
                                headers={'If-None-Match': str(os.stat(pdoc.__file__).st_mtime)}))
            self.assertEqual(cm.exception.code, 304)


if __name__ == '__main__':
    unittest.main()
