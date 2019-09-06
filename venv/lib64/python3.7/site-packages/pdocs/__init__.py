"""
Module pdoc provides types and functions for accessing the public
documentation of a Python module. This includes modules (and
sub-modules), functions, classes and module, class and instance
variables.  Docstrings are taken from modules, functions and classes
using the special `__doc__` attribute. Docstrings for variables are
extracted by examining the module's abstract syntax tree.

The public interface of a module is determined through one of two
ways. If `__all__` is defined in the module, then all identifiers in
that list will be considered public. No other identifiers will be
considered as public. Conversely, if `__all__` is not defined, then
`pdoc` will heuristically determine the public interface. There are
three rules that are applied to each identifier in the module:

1. If the name starts with an underscore, it is **not** public.

2. If the name is defined in a different module, it is **not** public.

3. If the name refers to an immediate sub-module, then it is public.

Once documentation for a module is created with `pdoc.Module`, it
can be output as either HTML or plain text using the covenience
functions `pdoc.html` and `pdoc.text`, or the corresponding methods
`pdoc.Module.html` and `pdoc.Module.text`.

Alternatively, you may run an HTTP server with the `pdoc` script
included with this module.


Compatibility
-------------
`pdoc` requires Python 3.6 or later.


Contributing
------------
`pdoc` [is on GitHub](https://github.com/mitmproxy/pdoc). Pull
requests and bug reports are welcome.


Linking to other identifiers
----------------------------
In your documentation, you may link to other identifiers in
your module or submodules. Linking is automatically done for
you whenever you surround an identifier with a back quote
(grave). The identifier name must be fully qualified. For
example, <code>`pdoc.Doc.docstring`</code> is correct while
<code>`Doc.docstring`</code> is incorrect.

If the `pdoc` script is used to run an HTTP server, then external
linking to other packages installed is possible. No extra work is
necessary; simply use the fully qualified path. For example,
<code>`nflvid.slice`</code> will create a link to the `nflvid.slice`
function, which is **not** a part of `pdoc` at all.


Where does pdoc get documentation from?
---------------------------------------
Broadly speaking, `pdoc` gets everything you see from introspecting the
module. This includes words describing a particular module, class,
function or variable. While `pdoc` does some analysis on the source
code of a module, importing the module itself is necessary to use
Python's introspection features.

In Python, objects like modules, functions, classes and methods have
a special attribute named `__doc__` which contains that object's
*docstring*.  The docstring comes from a special placement of a string
in your source code.  For example, the following code shows how to
define a function with a docstring and access the contents of that
docstring:

    #!python
    >>> def test():
    ...     '''This is a docstring.'''
    ...     pass
    ...
    >>> test.__doc__
    'This is a docstring.'

Something similar can be done for classes and modules too. For classes,
the docstring should come on the line immediately following `class
...`. For modules, the docstring should start on the first line of
the file. These docstrings are what you see for each module, class,
function and method listed in the documentation produced by `pdoc`.

The above just about covers *standard* uses of docstrings in Python.
`pdoc` extends the above in a few important ways.


### Special docstring conventions used by `pdoc`

**Firstly**, docstrings can be inherited. Consider the following code
sample:

    #!python
    >>> class A (object):
    ...     def test():
    ...         '''Docstring for A.'''
    ...
    >>> class B (A):
    ...     def test():
    ...         pass
    ...
    >>> print(A.test.__doc__)
    Docstring for A.
    >>> print(B.test.__doc__)
    None

In Python, the docstring for `B.test` is empty, even though one was
defined in `A.test`. If `pdoc` generates documentation for the above
code, then it will automatically attach the docstring for `A.test` to
`B.test` only if `B.test` does not have a docstring. In the default
HTML output, an inherited docstring is grey.

**Secondly**, docstrings can be attached to variables, which includes
module (or global) variables, class variables and instance variables.
Python by itself [does not allow docstrings to be attached to
variables](http://www.python.org/dev/peps/pep-0224). For example:

    #!python
    variable = "SomeValue"
    '''Docstring for variable.'''

The resulting `variable` will have no `__doc__` attribute. To
compensate, `pdoc` will read the source code when it's available to
infer a connection between a variable and a docstring. The connection
is only made when an assignment statement is followed by a docstring.

Something similar is done for instance variables as well. By
convention, instance variables are initialized in a class's `__init__`
method.  Therefore, `pdoc` adheres to that convention and looks for
docstrings of variables like so:

    #!python
    def __init__(self):
        self.variable = "SomeValue"
        '''Docstring for instance variable.'''

Note that `pdoc` only considers attributes defined on `self` as
instance variables.

Class and instance variables can also have inherited docstrings.

**Thirdly and finally**, docstrings can be overridden with a special
`__pdoc__` dictionary that `pdoc` inspects if it exists. The keys of
`__pdoc__` should be identifiers within the scope of the module. (In
the case of an instance variable `self.variable` for class `A`, its
module identifier would be `A.variable`.) The values of `__pdoc__`
should be docstrings.

This particular feature is useful when there's no feasible way of
attaching a docstring to something. A good example of this is a
[namedtuple](http://goo.gl/akfXJ9):

    #!python
    __pdoc__ = {}

    Table = namedtuple('Table', ['types', 'names', 'rows'])
    __pdoc__['Table.types'] = 'Types for each column in the table.'
    __pdoc__['Table.names'] = 'The names of each column in the table.'
    __pdoc__['Table.rows'] = 'Lists corresponding to each row in the table.'

`pdoc` will then show `Table` as a class with documentation for the
`types`, `names` and `rows` members.

Note that assignments to `__pdoc__` need to placed where they'll be
executed when the module is imported. For example, at the top level
of a module or in the definition of a class.

If `__pdoc__[key] = None`, then `key` will not be included in the
public interface of the module.
"""

from pdocs._version import __version__
from pdocs.api import as_html, as_markdown, server
