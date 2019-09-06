"""
Python package `pdoc` provides types, functions, and a command-line
interface for accessing public documentation of Python modules, and
for presenting it in a user-friendly, industry-standard open format.
It is best suited for small- to medium-sized projects with tidy,
hierarchical APIs.

.. include:: ./documentation.md
"""
import ast
import importlib.machinery
import importlib.util
import inspect
import os
import os.path as path
import re
import sys
import typing
from contextlib import contextmanager
from copy import copy
from functools import lru_cache, reduce, partial
from itertools import tee, groupby
from types import ModuleType
from typing import Dict, Iterable, List, Set, Type, TypeVar, Union, Tuple, Generator, Callable
from warnings import warn

from mako.lookup import TemplateLookup
from mako.exceptions import TopLevelLookupException
from mako.template import Template

try:
    from pdoc._version import version as __version__  # noqa: F401
except ImportError:
    __version__ = '???'  # Package not installed


_URL_MODULE_SUFFIX = '.html'
_URL_INDEX_MODULE_SUFFIX = '.m.html'  # For modules named literal 'index'
_URL_PACKAGE_SUFFIX = '/index.html'

_SOURCE_SUFFIXES = tuple(importlib.machinery.SOURCE_SUFFIXES)

T = TypeVar('T', bound='Doc')

__pdoc__ = {}  # type: Dict[str, Union[bool, str]]

tpl_lookup = TemplateLookup(
    cache_args=dict(cached=True,
                    cache_type='memory'),
    input_encoding='utf-8',
    directories=[path.join(path.dirname(__file__), "templates")],
)
"""
A `mako.lookup.TemplateLookup` object that knows how to load templates
from the file system. You may add additional paths by modifying the
object's `directories` attribute.
"""
if os.getenv("XDG_CONFIG_HOME"):
    tpl_lookup.directories.insert(0, path.join(os.getenv("XDG_CONFIG_HOME", ''), "pdoc"))


class Context(dict):
    """
    The context object that maps all documented identifiers
    (`pdoc.Doc.refname`) to their respective `pdoc.Doc` objects.

    You can pass an instance of `pdoc.Context` to `pdoc.Module` constructor.
    All `pdoc.Module` objects that share the same `pdoc.Context` will see
    (and be able to link in HTML to) each other's identifiers.

    If you don't pass your own `Context` instance to `Module` constructor,
    a global context object will be used.
    """
    __pdoc__['Context.__init__'] = False


_global_context = Context()


def reset():
    """Resets the global `pdoc.Context` to the initial (empty) state."""
    global _global_context
    _global_context.clear()

    # Clear LRU caches
    for cls in (Doc, Module, Class, Function, Variable, External):
        for _, method in inspect.getmembers(cls):
            if isinstance(method, property):
                method = method.fget
            if hasattr(method, 'cache_clear'):
                method.cache_clear()


def _render_template(template_name, **kwargs):
    """
    Returns the Mako template with the given name.  If the template
    cannot be found, a nicer error message is displayed.
    """
    # Apply config.mako configuration
    MAKO_INTERNALS = Template('').module.__dict__.keys()
    DEFAULT_CONFIG = path.join(path.dirname(__file__), 'templates', 'config.mako')
    config = {}
    for config_module in (Template(filename=DEFAULT_CONFIG).module,
                          tpl_lookup.get_template('/config.mako').module):
        config.update((var, getattr(config_module, var, None))
                      for var in config_module.__dict__
                      if var not in MAKO_INTERNALS)
    known_keys = set(config) | {'module', 'modules', 'http_server', 'external_links'}  # deprecated
    invalid_keys = {k: v for k, v in kwargs.items() if k not in known_keys}
    if invalid_keys:
        warn('Unknown configuration variables (not in config.mako): {}'.format(invalid_keys))
    config.update(kwargs)

    try:
        t = tpl_lookup.get_template(template_name)
    except TopLevelLookupException:
        raise OSError(
            "No template found at any of: {}".format(
                ', '.join(path.join(p, template_name.lstrip("/"))
                          for p in tpl_lookup.directories)))
    try:
        return t.render(**config).strip()
    except Exception:
        from mako import exceptions
        print(exceptions.text_error_template().render(),
              file=sys.stderr)
        raise


def html(module_name, docfilter=None, reload=False, **kwargs) -> str:
    """
    Returns the documentation for the module `module_name` in HTML
    format. The module must be a module or an importable string.

    `docfilter` is an optional predicate that controls which
    documentation objects are shown in the output. It is a function
    that takes a single argument (a documentation object) and returns
    `True` or `False`. If `False`, that object will not be documented.
    """
    mod = Module(import_module(module_name, reload=reload), docfilter=docfilter)
    link_inheritance()
    return mod.html(**kwargs)


def text(module_name, docfilter=None, reload=False, **kwargs) -> str:
    """
    Returns the documentation for the module `module_name` in plain
    text format suitable for viewing on a terminal.
    The module must be a module or an importable string.

    `docfilter` is an optional predicate that controls which
    documentation objects are shown in the output. It is a function
    that takes a single argument (a documentation object) and returns
    `True` or `False`. If `False`, that object will not be documented.
    """
    mod = Module(import_module(module_name, reload=reload), docfilter=docfilter)
    link_inheritance()
    return mod.text(**kwargs)


def import_module(module, *, reload: bool = False) -> ModuleType:
    """
    Return module object matching `module` specification (either a python
    module path or a filesystem path to file/directory).
    """
    @contextmanager
    def _module_path(module):
        from os.path import isfile, isdir, split, abspath, splitext
        path, module = '_pdoc_dummy_nonexistent', module
        if isdir(module) or isfile(module) and module.endswith(_SOURCE_SUFFIXES):
            path, module = split(splitext(abspath(module))[0])
        try:
            sys.path.insert(0, path)
            yield module
        finally:
            sys.path.remove(path)

    if isinstance(module, Module):
        module = module.obj
    if isinstance(module, str):
        with _module_path(module) as module_path:
            try:
                module = importlib.import_module(module_path)
            except Exception as e:
                raise ImportError('Error importing {!r}: {}'.format(module, e))

    assert inspect.ismodule(module)
    # If this is pdoc itself, return without reloading. Otherwise later
    # `isinstance(..., pdoc.Doc)` calls won't work correctly.
    if reload and not module.__name__.startswith(__name__):
        module = importlib.reload(module)
    return module


def _pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def _var_docstrings(doc_obj: Union['Module', 'Class'], *,
                    _init_tree: ast.FunctionDef = None) -> Dict[str, 'Variable']:
    """
    Extracts docstrings for variables of `doc_obj`
    (either a `pdoc.Module` or `pdoc.Class`).

    Returns a dict mapping variable names to `pdoc.Variable` objects.

    For `pdoc.Class` objects, the dict contains class' instance
    variables (defined as `self.something` in class' `__init__`),
    recognized by `Variable.instance_var == True`.
    """
    if _init_tree:
        tree = _init_tree  # type: Union[ast.Module, ast.FunctionDef]
    else:
        # No variables in namespace packages
        if isinstance(doc_obj, Module) and doc_obj.is_namespace:
            return {}
        try:
            tree = ast.parse(inspect.getsource(doc_obj.obj))
        except (OSError, TypeError, SyntaxError):
            warn("Couldn't get/parse source of '{!r}'".format(doc_obj))
            return {}
        if isinstance(doc_obj, Class):
            tree = tree.body[0]  # type: ignore  # ast.parse creates a dummy ast.Module wrapper

    vs = {}  # type: Dict[str, Variable]

    cls = None
    module = doc_obj
    module_all = getattr(module.obj, '__all__', None)

    if isinstance(doc_obj, Class):
        cls = doc_obj
        module = doc_obj.module
        module_all = None  # If documenting a class, we needn't look into __all__

        # For classes, first add instance variables defined in __init__
        if not _init_tree:
            try:
                # Recursive call with just the __init__ tree
                vs = _var_docstrings(
                    doc_obj, _init_tree=next(
                        node for node in tree.body
                        if (isinstance(node, ast.FunctionDef) and
                            node.name == '__init__')))
            except StopIteration:
                pass

    if module_all is not None:
        module_all = set(module_all)

    try:
        ast_AnnAssign = ast.AnnAssign   # type: Type
    except AttributeError:  # Python < 3.6
        ast_AnnAssign = type(None)

    ast_Assignments = (ast.Assign, ast_AnnAssign)

    for assign_node, str_node in _pairwise(ast.iter_child_nodes(tree)):
        if not (isinstance(assign_node, ast_Assignments) and
                isinstance(str_node, ast.Expr) and
                isinstance(str_node.value, ast.Str)):
            continue

        if isinstance(assign_node, ast.Assign) and len(assign_node.targets) == 1:
            target = assign_node.targets[0]
        elif isinstance(assign_node, ast_AnnAssign):
            target = assign_node.target
            # TODO: use annotation
        else:
            continue

        if not _init_tree and isinstance(target, ast.Name):
            name = target.id
        elif (_init_tree and
              isinstance(target, ast.Attribute) and
              isinstance(target.value, ast.Name) and
              target.value.id == 'self'):
            name = target.attr
        else:
            continue

        if not _is_public(name):
            continue

        if module_all is not None and name not in module_all:
            continue

        docstring = inspect.cleandoc(str_node.value.s).strip()
        if not docstring:
            continue

        vs[name] = Variable(name, module, docstring,
                            cls=cls, instance_var=bool(_init_tree))
    return vs


def _is_public(ident_name):
    """
    Returns `True` if `ident_name` matches the export criteria for an
    identifier name.
    """
    return not ident_name.startswith("_")


def _filter_type(type: Type[T],
                 values: Union[Iterable['Doc'], Dict[str, 'Doc']]) -> List[T]:
    """
    Return a list of values from `values` of type `type`.
    """
    if isinstance(values, dict):
        values = values.values()
    return [i for i in values if isinstance(i, type)]


def _toposort(graph: Dict[T, Set[T]]) -> Generator[T, None, None]:
    """
    Return items of `graph` sorted in topological order.
    Source: https://rosettacode.org/wiki/Topological_sort#Python
    """
    items_without_deps = reduce(set.union, graph.values(), set()) - set(graph.keys())  # type: ignore  # noqa: E501
    yield from items_without_deps
    ordered = items_without_deps
    while True:
        graph = {item: (deps - ordered)
                 for item, deps in graph.items()
                 if item not in ordered}
        ordered = {item
                   for item, deps in graph.items()
                   if not deps}
        yield from ordered
        if not ordered:
            break
    assert not graph, "A cyclic dependency exists amongst %r" % graph


def link_inheritance(context: Context = None):
    """
    Link inheritance relationsships between `pdoc.Class` objects
    (and between their members) of all `pdoc.Module` objects that
    share the provided `context` (`pdoc.Context`).

    You need to call this if you expect `pdoc.Doc.inherits` and
    inherited `pdoc.Doc.docstring` to be set correctly.
    """
    if context is None:
        context = _global_context

    graph = {cls: set(cls.mro(only_documented=True))
             for cls in _filter_type(Class, context)}

    for cls in _toposort(graph):
        cls._fill_inheritance()

    for module in _filter_type(Module, context):
        module._link_inheritance()


class Doc:
    """
    A base class for all documentation objects.

    A documentation object corresponds to *something* in a Python module
    that has a docstring associated with it. Typically, this includes
    modules, classes, functions, and methods. However, `pdoc` adds support
    for extracting some docstrings from abstract syntax trees, making
    (module, class or instance) variables supported too.

    A special type of documentation object `pdoc.External` is used to
    represent identifiers that are not part of the public interface of
    a module. (The name "External" is a bit of a misnomer, since it can
    also correspond to unexported members of the module, particularly in
    a class's ancestor list.)
    """
    __slots__ = ('module', 'name', 'obj', 'docstring', 'inherits')

    def __init__(self, name, module, obj, docstring=None):
        """
        Initializes a documentation object, where `name` is the public
        identifier name, `module` is a `pdoc.Module` object where raw
        Python object `obj` is defined, and `docstring` is its
        documentation string. If `docstring` is left empty, it will be
        read with `inspect.getdoc()`.
        """
        self.module = module
        """
        The module documentation object that this object is defined in.
        """

        self.name = name
        """
        The identifier name for this object.
        """

        self.obj = obj
        """
        The raw python object.
        """

        docstring = (docstring or inspect.getdoc(obj) or '').strip()
        if '.. include::' in docstring:
            from pdoc.html_helpers import _ToMarkdown
            docstring = _ToMarkdown.admonitions(docstring, self.module, ('include',))
        self.docstring = docstring
        """
        The cleaned docstring for this object with any `.. include::`
        directives resolved (i.e. content included).
        """

        self.inherits = None  # type: Union[Class, Function, Variable]
        """
        The Doc object (Class, Function, or Variable) this object inherits from,
        if any.
        """

    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.refname)

    @property  # type: ignore
    @lru_cache()
    def source(self) -> str:
        """
        Cleaned (dedented) source code of the Python object. If not
        available, an empty string.
        """
        try:
            lines, _ = inspect.getsourcelines(self.obj)
        except (ValueError, TypeError, OSError):
            return ''
        return inspect.cleandoc(''.join(['\n'] + lines))

    @property
    def refname(self):
        """
        Reference name of this documentation
        object, usually its fully qualified path
        (e.g. <code>pdoc.Doc.refname</code>). Every
        documentation object provides this property.
        """
        # Ok for Module and External, the rest need it overriden
        return self.name

    @property
    def qualname(self):
        """
        Module-relative "qualified" name of this documentation
        object, used for show (e.g. <code>Doc.qualname</code>).
        """
        return getattr(self.obj, '__qualname__', self.name)

    @lru_cache()
    def url(self, relative_to: 'Module' = None, *, link_prefix: str = '',
            top_ancestor: bool = False):
        """
        Canonical relative URL (including page fragment) for this
        documentation object.

        Specify `relative_to` (a `pdoc.Module` object) to obtain a
        relative URL.

        For usage of `link_prefix` see `pdoc.html()`.

        If `top_ancestor` is `True`, the returned URL instead points to
        the top ancestor in the object's `pdoc.Doc.inherits` chain.
        """
        if top_ancestor:
            self = self._inherits_top()

        if relative_to is None or link_prefix:
            return link_prefix + self._url()

        if self.module.name == relative_to.name:
            return '#' + self.refname

        # Otherwise, compute relative path from current module to link target
        url = os.path.relpath(self._url(), relative_to.url()).replace(path.sep, '/')
        # We have one set of '..' too many
        if url.startswith('../'):
            url = url[3:]
        return url

    def _url(self):
        return self.module._url() + '#' + self.refname

    def _inherits_top(self):
        """
        Follow the `pdoc.Doc.inherits` chain and return the top object.
        """
        top = self
        while top.inherits:
            top = top.inherits
        return top

    def __lt__(self, other):
        return self.name < other.name


class Module(Doc):
    """
    Representation of a module's documentation.
    """
    __pdoc__["Module.name"] = """
        The name of this module with respect to the context/path in which
        it was imported from. It is always an absolute import path.
        """

    __slots__ = ('supermodule', 'doc', '_context', '_is_inheritance_linked')

    def __init__(self, module: ModuleType, *, docfilter: Callable[[Doc], bool] = None,
                 supermodule: 'Module' = None, context: Context = None):
        """
        Creates a `Module` documentation object given the actual
        module Python object.

        `docfilter` is an optional predicate that controls which
        sub-objects are documentated (see also: `pdoc.html()`).

        `supermodule` is the parent `pdoc.Module` this module is
        a submodule of.

        `context` is an instance of `pdoc.Context`. If `None` a
        global context object will be used.
        """
        super().__init__(module.__name__, self, module)
        if self.name.endswith('.__init__') and not self.is_package:
            self.name = self.name[:-len('.__init__')]

        self._context = _global_context if context is None else context
        """
        A lookup table for ALL doc objects of all modules that share this context,
        mainly used in `Module.find_ident()`.
        """

        self.supermodule = supermodule
        """
        The parent `pdoc.Module` this module is a submodule of, or `None`.
        """

        self.doc = {}  # type: Dict[str, Doc]
        """A mapping from identifier name to a documentation object."""

        self._is_inheritance_linked = False
        """Re-entry guard for `pdoc.Module._link_inheritance()`."""

        # Populate self.doc with this module's public members
        if hasattr(self.obj, '__all__'):
            public_objs = []
            for name in self.obj.__all__:
                try:
                    public_objs.append((name, getattr(self.obj, name)))
                except AttributeError:
                    warn("Module {!r} doesn't contain identifier `{}` "
                         "exported in `__all__`".format(self.module, name))
        else:
            def is_from_this_module(obj):
                mod = inspect.getmodule(obj)
                return mod is None or mod.__name__ == self.obj.__name__

            public_objs = [(name, inspect.unwrap(obj))
                           for name, obj in inspect.getmembers(self.obj)
                           if (_is_public(name) and
                               is_from_this_module(obj))]
            index = list(self.obj.__dict__).index
            public_objs.sort(key=lambda i: index(i[0]))
        for name, obj in public_objs:
            if inspect.isroutine(obj):
                self.doc[name] = Function(name, self, obj)
            elif inspect.isclass(obj):
                self.doc[name] = Class(name, self, obj)

        self.doc.update(_var_docstrings(self))

        # If the module is a package, scan the directory for submodules
        if self.is_package:

            def iter_modules(paths):
                """
                Custom implementation of `pkgutil.iter_modules()`
                because that one doesn't play well with namespace packages.
                See: https://github.com/pypa/setuptools/issues/83
                """
                from os.path import isdir, join, splitext
                for pth in paths:
                    for file in os.listdir(pth):
                        if file.startswith(('.', '__pycache__', '__init__.py')):
                            continue
                        if file.endswith(_SOURCE_SUFFIXES) or isdir(join(pth, file)):
                            yield splitext(file)[0]

            for root in iter_modules(self.obj.__path__):
                # Ignore if this module was already doc'd.
                if root in self.doc:
                    continue

                # Ignore if it isn't exported
                if not _is_public(root):
                    continue

                assert self.refname == self.name
                fullname = "%s.%s" % (self.name, root)
                self.doc[root] = m = Module(import_module(fullname),
                                            docfilter=docfilter, supermodule=self,
                                            context=self._context)
                # Skip empty namespace packages because they may
                # as well be other auxiliary directories
                if m.is_namespace and not m.doc:
                    del self.doc[root]

        # Apply docfilter
        if docfilter:
            for name, dobj in self.doc.copy().items():
                if not docfilter(dobj):
                    self.doc.pop(name)

        # Build the reference name dictionary of the module
        self._context[self.refname] = self
        for docobj in self.doc.values():
            self._context[docobj.refname] = docobj
            if isinstance(docobj, Class):
                self._context.update((obj.refname, obj)
                                     for obj in docobj.doc.values())

    def _link_inheritance(self):
        # Inherited members are already in place since
        # `Class._fill_inheritance()` has been called from
        # `pdoc.fill_inheritance()`.
        # Now look for docstrings in the module's __pdoc__ override.

        if self._is_inheritance_linked:
            # Prevent re-linking inheritance for modules which have already
            # had done so. Otherwise, this would raise "does not exist"
            # errors if `pdoc.link_inheritance()` is called multiple times.
            return

        for name, docstring in getattr(self.obj, "__pdoc__", {}).items():
            refname = "%s.%s" % (self.refname, name)
            if docstring in (False, None):
                if docstring is None:
                    warn('Setting `__pdoc__[key] = None` is deprecated; '
                         'use `__pdoc__[key] = False` '
                         '(key: {!r}, module: {!r}).'.format(name, self.name))

                if (not name.endswith('.__init__') and
                        name not in self.doc and refname not in self._context):
                    warn('__pdoc__-overriden key {!r} does not exist '
                         'in module {!r}'.format(name, self.name))

                obj = self.find_ident(name)
                cls = getattr(obj, 'cls', None)
                if cls:
                    del cls.doc[obj.name]
                self.doc.pop(name, None)
                self._context.pop(refname, None)

                # Pop also all that startwith refname
                for key in list(self._context.keys()):
                    if key.startswith(refname + '.'):
                        del self._context[key]

                continue

            dobj = self.find_ident(refname)
            if isinstance(dobj, External):
                continue
            if not isinstance(docstring, str):
                raise ValueError('__pdoc__ dict values must be strings;'
                                 '__pdoc__[{!r}] is of type {}'.format(name, type(docstring)))
            dobj.docstring = inspect.cleandoc(docstring)

        # Now after docstrings are set correctly, continue the
        # inheritance routine, marking members inherited or not
        for c in _filter_type(Class, self.doc):
            c._link_inheritance()

        self._is_inheritance_linked = True

    def text(self, **kwargs) -> str:
        """
        Returns the documentation for this module as plain text.
        """
        txt = _render_template('/text.mako', module=self, **kwargs)
        return re.sub("\n\n\n+", "\n\n", txt)

    def html(self, minify=True, **kwargs) -> str:
        """
        Returns the documentation for this module as
        self-contained HTML.

        If `minify` is `True`, the resulting HTML is minified.

        For explanation of other arguments, see `pdoc.html()`.

        `kwargs` is passed to the `mako` render function.
        """
        html = _render_template('/html.mako', module=self, **kwargs)
        if minify:
            from pdoc.html_helpers import minify_html
            html = minify_html(html)
        return html

    @property
    def is_package(self):
        """
        `True` if this module is a package.

        Works by checking whether the module has a `__path__` attribute.
        """
        return hasattr(self.obj, "__path__")

    @property
    def is_namespace(self):
        """
        `True` if this module is a namespace package.
        """
        return self.obj.__spec__.origin in (None, 'namespace')  # None in Py3.7+

    def find_class(self, cls: type):
        """
        Given a Python `cls` object, try to find it in this module
        or in any of the exported identifiers of the submodules.
        """
        # XXX: Is this corrent? Does it always match
        # `Class.module.name + Class.qualname`?. Especially now?
        # If not, see what was here before.
        return self.find_ident(cls.__module__ + '.' + cls.__qualname__)

    def find_ident(self, name: str) -> Doc:
        """
        Searches this module and **all** other public modules
        for an identifier with name `name` in its list of
        exported identifiers.

        The documentation object corresponding to the identifier is
        returned. If one cannot be found, then an instance of
        `External` is returned populated with the given identifier.
        """
        _name = name.rstrip('()')  # Function specified with parentheses

        if _name.endswith('.__init__'):  # Ref to class' init is ref to class itself
            _name = _name[:-len('.__init__')]

        return (self.doc.get(_name) or
                self._context.get(_name) or
                self._context.get(self.name + '.' + _name) or
                External(name))

    def _filter_doc_objs(self, type: Type[T], sort=True) -> List[T]:
        result = _filter_type(type, self.doc)
        return sorted(result) if sort else result

    def variables(self, sort=True):
        """
        Returns all documented module-level variables in the module,
        optionally sorted alphabetically, as a list of `pdoc.Variable`.
        """
        return self._filter_doc_objs(Variable, sort)

    def classes(self, sort=True):
        """
        Returns all documented module-level classes in the module,
        optionally sorted alphabetically, as a list of `pdoc.Class`.
        """
        return self._filter_doc_objs(Class, sort)

    def functions(self, sort=True):
        """
        Returns all documented module-level functions in the module,
        optionally sorted alphabetically, as a list of `pdoc.Function`.
        """
        return self._filter_doc_objs(Function, sort)

    def submodules(self):
        """
        Returns all documented sub-modules of the module sorted
        alphabetically as a list of `pdoc.Module`.
        """
        return self._filter_doc_objs(Module)

    def _url(self):
        url = self.module.name.replace('.', '/')
        if self.is_package:
            return url + _URL_PACKAGE_SUFFIX
        elif url.endswith('/index'):
            return url + _URL_INDEX_MODULE_SUFFIX
        return url + _URL_MODULE_SUFFIX


class Class(Doc):
    """
    Representation of a class' documentation.
    """
    __slots__ = ('doc', '_super_members')

    def __init__(self, name, module, obj, *, docstring=None):
        assert isinstance(obj, type)
        if docstring is None:
            init_doc = inspect.getdoc(obj.__init__) or ''
            if init_doc == object.__init__.__doc__:
                init_doc = ''
            docstring = ((inspect.getdoc(obj) or '') + '\n\n' + init_doc).strip()
        super().__init__(name, module, obj, docstring=docstring)

        self.doc = {}
        """A mapping from identifier name to a `pdoc.Doc` objects."""

        self.doc.update(_var_docstrings(self))

        public_objs = [(name, inspect.unwrap(obj))
                       for name, obj in inspect.getmembers(self.obj)
                       # Filter only *own* members. The rest are inherited
                       # in Class._fill_inheritance()
                       if name in self.obj.__dict__ and _is_public(name)]
        index = list(self.obj.__dict__).index
        public_objs.sort(key=lambda i: index(i[0]))

        # Convert the public Python objects to documentation objects.
        for name, obj in public_objs:
            if name in self.doc and self.doc[name].docstring:
                continue
            if inspect.isroutine(obj):
                self.doc[name] = Function(
                    name, self.module, obj, cls=self,
                    method=not self._method_type(self.obj, name))
            elif (inspect.isdatadescriptor(obj) or
                  inspect.isgetsetdescriptor(obj) or
                  inspect.ismemberdescriptor(obj)):
                self.doc[name] = Variable(
                    name, self.module, inspect.getdoc(obj),
                    obj=getattr(obj, 'fget', obj),
                    cls=self, instance_var=True)
            else:
                self.doc[name] = Variable(
                    name, self.module,
                    docstring=isinstance(obj, type) and inspect.getdoc(obj) or "",
                    cls=self,
                    instance_var=name in getattr(self.obj, "__slots__", ()))

    @staticmethod
    def _method_type(cls: type, name: str):
        """
        Returns `None` if the method `name` of class `cls`
        is a regular method. Otherwise, it returns
        `classmethod` or `staticmethod`, as appropriate.
        """
        func = getattr(cls, name, None)
        if inspect.ismethod(func):
            # If the function is already bound, it's a classmethod.
            # Regular methods are not bound before initialization.
            return classmethod
        for c in inspect.getmro(cls):
            if name in c.__dict__:
                if isinstance(c.__dict__[name], staticmethod):
                    return staticmethod
                return None
        raise RuntimeError("{}.{} not found".format(cls, name))

    @property
    def refname(self):
        return self.module.name + '.' + self.qualname

    def mro(self, only_documented=False) -> List['Class']:
        """
        Returns a list of ancestor (superclass) documentation objects
        in method resolution order.

        The list will contain objects of type `pdoc.Class`
        if the types are documented, and `pdoc.External` otherwise.
        """
        classes = [self.module.find_class(c)
                   for c in inspect.getmro(self.obj)
                   if c not in (self.obj, object)]
        if only_documented:
            classes = _filter_type(Class, classes)
        return classes

    def subclasses(self) -> List['Class']:
        """
        Returns a list of subclasses of this class that are visible to the
        Python interpreter (obtained from `type.__subclasses__()`).

        The objects in the list are of type `pdoc.Class` if available,
        and `pdoc.External` otherwise.
        """
        return [self.module.find_class(c)
                for c in type.__subclasses__(self.obj)]

    def params(self, *, annotate=False, link=None) -> List['str']:
        """
        Return a list of formatted parameters accepted by the
        class constructor (method `__init__`). See `pdoc.Function.params`.
        """
        name = self.name + '.__init__'
        qualname = self.qualname + '.__init__'
        refname = self.refname + '.__init__'
        exclusions = getattr(self.module.obj, "__pdoc__", {})
        if name in exclusions or qualname in exclusions or refname in exclusions:
            return []

        params = Function._params(self.obj.__init__,
                                  annotate=annotate, link=link, module=self.module)
        params = params[1:] if params[0] == 'self' else params
        return params

    def _filter_doc_objs(self, type: Type[T], include_inherited=True,
                         filter_func: Callable[[T], bool] = lambda x: True,
                         sort=True) -> List[T]:
        result = [obj for obj in _filter_type(type, self.doc)
                  if (include_inherited or not obj.inherits) and filter_func(obj)]
        return sorted(result) if sort else result

    def class_variables(self, include_inherited=True, sort=True):
        """
        Returns an optionally-sorted list of `pdoc.Variable` objects that
        represent this class' class variables.
        """
        return self._filter_doc_objs(
            Variable, include_inherited, lambda dobj: not dobj.instance_var,
            sort)

    def instance_variables(self, include_inherited=True, sort=True):
        """
        Returns an optionally-sorted list of `pdoc.Variable` objects that
        represent this class' instance variables. Instance variables
        are those defined in a class's `__init__` as `self.variable = ...`.
        """
        return self._filter_doc_objs(
            Variable, include_inherited, lambda dobj: dobj.instance_var,
            sort)

    def methods(self, include_inherited=True, sort=True):
        """
        Returns an optionally-sorted list of `pdoc.Function` objects that
        represent this class' methods.
        """
        return self._filter_doc_objs(
            Function, include_inherited, lambda dobj: dobj.method,
            sort)

    def functions(self, include_inherited=True, sort=True) -> List['Function']:
        """
        Returns an optionally-sorted list of `pdoc.Function` objects that
        represent this class' static functions.
        """
        return self._filter_doc_objs(
            Function, include_inherited, lambda dobj: not dobj.method,
            sort)

    def inherited_members(self) -> List[Tuple['Class', List[Doc]]]:
        """
        Returns all inherited members as a list of tuples
        (ancestor class, list of ancestor class' members sorted by name),
        sorted by MRO.
        """
        return sorted(((k, sorted(g))
                       for k, g in groupby((i.inherits
                                            for i in self.doc.values() if i.inherits),
                                           key=lambda i: i.cls)),
                      key=lambda x, _mro_index=self.mro().index: _mro_index(x[0]))  # type: ignore

    def _fill_inheritance(self):
        """
        Traverses this class's ancestor list and attempts to fill in
        missing documentation objects from its ancestors.

        Afterwards, call to `pdoc.Class._link_inheritance()` to also
        set `pdoc.Doc.inherits` pointers.
        """
        super_members = self._super_members = {}
        for cls in self.mro(only_documented=True):
            for name, dobj in cls.doc.items():
                if name not in super_members and dobj.docstring:
                    super_members[name] = dobj
                    if name not in self.doc:
                        dobj = copy(dobj)
                        dobj.cls = self

                        self.doc[name] = dobj
                        self.module._context[dobj.refname] = dobj

    def _link_inheritance(self):
        """
        Set `pdoc.Doc.inherits` pointers to inherited ancestors' members,
        as appropriate. This must be called after
        `pdoc.Class._fill_inheritance()`.

        The reason this is split in two parts is that in-between
        the `__pdoc__` overrides are applied.
        """
        if not hasattr(self, '_super_members'):
            return

        for name, parent_dobj in self._super_members.items():
            dobj = self.doc[name]
            if (dobj.obj is parent_dobj.obj or
                    (dobj.docstring or parent_dobj.docstring) == parent_dobj.docstring):
                dobj.inherits = parent_dobj
                dobj.docstring = parent_dobj.docstring
        del self._super_members


class Function(Doc):
    """
    Representation of documentation for a function or method.
    """
    __slots__ = ('cls', 'method')

    def __init__(self, name, module, obj, *, cls: Class = None, method=False):
        """
        Same as `pdoc.Doc`, except `obj` must be a
        Python function object. The docstring is gathered automatically.

        `cls` should be set when this is a method or a static function
        beloing to a class. `cls` should be a `pdoc.Class` object.

        `method` should be `True` when the function is a method. In
        all other cases, it should be `False`.
        """
        assert callable(obj)
        super().__init__(name, module, obj)

        self.cls = cls
        """
        The `pdoc.Class` documentation object if the function is a method.
        If not, this is None.
        """

        self.method = method
        """
        Whether this function is a normal bound method.

        In particular, static and class methods have this set to False.
        """

    def funcdef(self):
        """
        Generates the string of keywords used to define the function,
        for example `def` or `async def`.
        """
        return 'async def' if self._is_async else 'def'

    @property
    def _is_async(self):
        """
        Returns whether is function is asynchronous, either as a coroutine or an async
        generator.
        """
        try:
            # Both of these are required because coroutines aren't classified as async
            # generators and vice versa.
            obj = inspect.unwrap(self.obj)
            return (inspect.iscoroutinefunction(obj) or
                    inspect.isasyncgenfunction(obj))
        except AttributeError:
            return False

    def return_annotation(self, *, link=None):
        """Formatted function return type annotation or empty string if none."""
        try:
            annot = typing.get_type_hints(self.obj).get('return', '')
        except NameError as e:
            warn("Error handling return annotation for {}: {}".format(self.name, e.args[0]))
            annot = inspect.signature(inspect.unwrap(self.obj)).return_annotation
            if annot == inspect.Parameter.empty:
                annot = ''
        if not annot:
            return ''
        s = inspect.formatannotation(annot).replace(' ', '\N{NBSP}')  # Better line breaks
        if link:
            from pdoc.html_helpers import _linkify
            s = re.sub(r'[\w\.]+', partial(_linkify, link=link, module=self.module), s)
        return s

    def params(self, *, annotate: bool = False, link: Callable[[Doc], str] = None) -> List[str]:
        """
        Returns a list where each element is a nicely formatted
        parameter of this function. This includes argument lists,
        keyword arguments and default values, and it doesn't include any
        optional arguments whose names begin with an underscore.

        If `annotate` is True, the parameter strings include [PEP 484]
        type hint annotations.

        [PEP 484]: https://www.python.org/dev/peps/pep-0484/
        """
        return self._params(self.obj, annotate=annotate, link=link, module=self.module)

    @staticmethod
    def _params(func_obj, annotate=False, link=None, module=None):
        try:
            signature = inspect.signature(inspect.unwrap(func_obj))
        except ValueError:
            # I guess this is for C builtin functions?
            return ["..."]

        def safe_default_value(p: inspect.Parameter):
            if p.default is os.environ:
                class mock:
                    def __repr__(self):
                        return 'os.environ'
                return p.replace(default=mock())
            return p

        params = []
        kw_only = False
        EMPTY = inspect.Parameter.empty

        if link:
            from pdoc.html_helpers import _linkify
            _linkify = partial(_linkify, link=link, module=module)

        for p in signature.parameters.values():  # type: inspect.Parameter
            if not _is_public(p.name) and p.default is not EMPTY:
                continue

            if p.kind == p.VAR_POSITIONAL:
                kw_only = True
            if p.kind == p.KEYWORD_ONLY and not kw_only:
                kw_only = True
                params.append('*')

            p = safe_default_value(p)

            if not annotate:
                p = p.replace(annotation=EMPTY)

            s = str(p)
            if p.annotation is not EMPTY:
                if sys.version_info < (3, 7):
                    # PEP8-normalize whitespace
                    s = re.sub(r'(?<!\s)=(?!\s)', ' = ', re.sub(r':(?!\s)', ': ', s, 1), 1)
                # "Eval" forward-declarations (typing string literals)
                s = re.sub(r'(?<=: )[\'"]|[\'"](?= = )', '', s, 2)
                s = s.replace(' ', '\N{NBSP}')  # prevent improper line breaking

                if link:
                    s = re.sub(r'[\w\.]+', _linkify, s)

            params.append(s)

        return params

    @property
    def refname(self):
        return (self.cls.refname if self.cls else self.module.refname) + '.' + self.name


class Variable(Doc):
    """
    Representation of a variable's documentation. This includes
    module, class, and instance variables.
    """
    __slots__ = ('cls', 'instance_var')

    def __init__(self, name, module, docstring, *,
                 obj=None, cls: Class = None, instance_var=False):
        """
        Same as `pdoc.Doc`, except `cls` should be provided
        as a `pdoc.Class` object when this is a class or instance
        variable.
        """
        super().__init__(name, module, obj, docstring)

        self.cls = cls
        """
        The `pdoc.Class` object if this is a class or instance
        variable. If not, this is None.
        """

        self.instance_var = instance_var
        """
        True if variable is some class' instance variable (as
        opposed to class variable).
        """

    @property
    def qualname(self):
        if self.cls:
            return self.cls.qualname + '.' + self.name
        return self.name

    @property
    def refname(self):
        return (self.cls.refname if self.cls else self.module.refname) + '.' + self.name


class External(Doc):
    """
    A representation of an external identifier. The textual
    representation is the same as an internal identifier.

    External identifiers are also used to represent something that is
    not documented but appears somewhere in the public interface (like
    the ancestor list of a class).
    """

    __pdoc__["External.docstring"] = """
        An empty string. External identifiers do not have
        docstrings.
        """
    __pdoc__["External.module"] = """
        Always `None`. External identifiers have no associated
        `pdoc.Module`.
        """
    __pdoc__["External.name"] = """
        Always equivalent to `pdoc.External.refname` since external
        identifiers are always expressed in their fully qualified
        form.
        """

    def __init__(self, name):
        """
        Initializes an external identifier with `name`, where `name`
        should be a fully qualified name.
        """
        super().__init__(name, None, None)

    def url(self, *args, **kwargs):
        """
        `External` objects return absolute urls matching `/{name}.ext`.
        """
        return '/%s.ext' % self.name
