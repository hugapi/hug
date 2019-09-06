"""
Tests for behaviour related to type annotations.
"""

from sys import version_info

from pyflakes import messages as m
from pyflakes.test.harness import TestCase, skipIf


class TestTypeAnnotations(TestCase):

    def test_typingOverload(self):
        """Allow intentional redefinitions via @typing.overload"""
        self.flakes("""
        import typing
        from typing import overload

        @overload
        def f(s):  # type: (None) -> None
            pass

        @overload
        def f(s):  # type: (int) -> int
            pass

        def f(s):
            return s

        @typing.overload
        def g(s):  # type: (None) -> None
            pass

        @typing.overload
        def g(s):  # type: (int) -> int
            pass

        def g(s):
            return s
        """)

    def test_not_a_typing_overload(self):
        """regression test for @typing.overload detection bug in 2.1.0"""
        self.flakes("""
            x = lambda f: f

            @x
            def t():
                pass

            y = lambda f: f

            @x
            @y
            def t():
                pass

            @x
            @y
            def t():
                pass
        """, m.RedefinedWhileUnused, m.RedefinedWhileUnused)

    @skipIf(version_info < (3, 6), 'new in Python 3.6')
    def test_variable_annotations(self):
        self.flakes('''
        name: str
        age: int
        ''')
        self.flakes('''
        name: str = 'Bob'
        age: int = 18
        ''')
        self.flakes('''
        class C:
            name: str
            age: int
        ''')
        self.flakes('''
        class C:
            name: str = 'Bob'
            age: int = 18
        ''')
        self.flakes('''
        def f():
            name: str
            age: int
        ''')
        self.flakes('''
        def f():
            name: str = 'Bob'
            age: int = 18
            foo: not_a_real_type = None
        ''', m.UnusedVariable, m.UnusedVariable, m.UnusedVariable, m.UndefinedName)
        self.flakes('''
        def f():
            name: str
            print(name)
        ''', m.UndefinedName)
        self.flakes('''
        from typing import Any
        def f():
            a: Any
        ''')
        self.flakes('''
        foo: not_a_real_type
        ''', m.UndefinedName)
        self.flakes('''
        foo: not_a_real_type = None
        ''', m.UndefinedName)
        self.flakes('''
        class C:
            foo: not_a_real_type
        ''', m.UndefinedName)
        self.flakes('''
        class C:
            foo: not_a_real_type = None
        ''', m.UndefinedName)
        self.flakes('''
        def f():
            class C:
                foo: not_a_real_type
        ''', m.UndefinedName)
        self.flakes('''
        def f():
            class C:
                foo: not_a_real_type = None
        ''', m.UndefinedName)
        self.flakes('''
        from foo import Bar
        bar: Bar
        ''')
        self.flakes('''
        from foo import Bar
        bar: 'Bar'
        ''')
        self.flakes('''
        import foo
        bar: foo.Bar
        ''')
        self.flakes('''
        import foo
        bar: 'foo.Bar'
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar: Bar): pass
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar: 'Bar'): pass
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar) -> Bar: return bar
        ''')
        self.flakes('''
        from foo import Bar
        def f(bar) -> 'Bar': return bar
        ''')
        self.flakes('''
        bar: 'Bar'
        ''', m.UndefinedName)
        self.flakes('''
        bar: 'foo.Bar'
        ''', m.UndefinedName)
        self.flakes('''
        from foo import Bar
        bar: str
        ''', m.UnusedImport)
        self.flakes('''
        from foo import Bar
        def f(bar: str): pass
        ''', m.UnusedImport)
        self.flakes('''
        def f(a: A) -> A: pass
        class A: pass
        ''', m.UndefinedName, m.UndefinedName)
        self.flakes('''
        def f(a: 'A') -> 'A': return a
        class A: pass
        ''')
        self.flakes('''
        a: A
        class A: pass
        ''', m.UndefinedName)
        self.flakes('''
        a: 'A'
        class A: pass
        ''')
        self.flakes('''
        a: 'A B'
        ''', m.ForwardAnnotationSyntaxError)
        self.flakes('''
        a: 'A; B'
        ''', m.ForwardAnnotationSyntaxError)
        self.flakes('''
        a: '1 + 2'
        ''')
        self.flakes('''
        a: 'a: "A"'
        ''', m.ForwardAnnotationSyntaxError)

    @skipIf(version_info < (3, 5), 'new in Python 3.5')
    def test_annotated_async_def(self):
        self.flakes('''
        class c: pass
        async def func(c: c) -> None: pass
        ''')

    @skipIf(version_info < (3, 7), 'new in Python 3.7')
    def test_postponed_annotations(self):
        self.flakes('''
        from __future__ import annotations
        def f(a: A) -> A: pass
        class A:
            b: B
        class B: pass
        ''')

        self.flakes('''
        from __future__ import annotations
        def f(a: A) -> A: pass
        class A:
            b: Undefined
        class B: pass
        ''', m.UndefinedName)

    def test_typeCommentsMarkImportsAsUsed(self):
        self.flakes("""
        from mod import A, B, C, D, E, F, G


        def f(
            a,  # type: A
        ):
            # type: (...) -> B
            for b in a:  # type: C
                with b as c:  # type: D
                    d = c.x  # type: E
                    return d


        def g(x):  # type: (F) -> G
            return x.y
        """)

    def test_typeCommentsFullSignature(self):
        self.flakes("""
        from mod import A, B, C, D
        def f(a, b):
            # type: (A, B[C]) -> D
            return a + b
        """)

    def test_typeCommentsStarArgs(self):
        self.flakes("""
        from mod import A, B, C, D
        def f(a, *b, **c):
            # type: (A, *B, **C) -> D
            return a + b
        """)

    def test_typeCommentsFullSignatureWithDocstring(self):
        self.flakes('''
        from mod import A, B, C, D
        def f(a, b):
            # type: (A, B[C]) -> D
            """do the thing!"""
            return a + b
        ''')

    def test_typeCommentsAdditionalComemnt(self):
        self.flakes("""
        from mod import F

        x = 1 # type: F  # noqa
        """)

    def test_typeCommentsNoWhitespaceAnnotation(self):
        self.flakes("""
        from mod import F

        x = 1  #type:F
        """)

    def test_typeCommentsInvalidDoesNotMarkAsUsed(self):
        self.flakes("""
        from mod import F

        # type: F
        """, m.UnusedImport)

    def test_typeCommentsSyntaxError(self):
        self.flakes("""
        def f(x):  # type: (F[) -> None
            pass
        """, m.CommentAnnotationSyntaxError)

    def test_typeCommentsSyntaxErrorCorrectLine(self):
        checker = self.flakes("""\
        x = 1
        # type: definitely not a PEP 484 comment
        """, m.CommentAnnotationSyntaxError)
        self.assertEqual(checker.messages[0].lineno, 2)

    def test_typeCommentsAssignedToPreviousNode(self):
        # This test demonstrates an issue in the implementation which
        # associates the type comment with a node above it, however the type
        # comment isn't valid according to mypy.  If an improved approach
        # which can detect these "invalid" type comments is implemented, this
        # test should be removed / improved to assert that new check.
        self.flakes("""
        from mod import F
        x = 1
        # type: F
        """)
