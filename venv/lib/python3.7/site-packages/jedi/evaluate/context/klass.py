"""
Like described in the :mod:`parso.python.tree` module,
there's a need for an ast like module to represent the states of parsed
modules.

But now there are also structures in Python that need a little bit more than
that. An ``Instance`` for example is only a ``Class`` before it is
instantiated. This class represents these cases.

So, why is there also a ``Class`` class here? Well, there are decorators and
they change classes in Python 3.

Representation modules also define "magic methods". Those methods look like
``py__foo__`` and are typically mappable to the Python equivalents ``__call__``
and others. Here's a list:

====================================== ========================================
**Method**                             **Description**
-------------------------------------- ----------------------------------------
py__call__(arguments: Array)           On callable objects, returns types.
py__bool__()                           Returns True/False/None; None means that
                                       there's no certainty.
py__bases__()                          Returns a list of base classes.
py__iter__()                           Returns a generator of a set of types.
py__class__()                          Returns the class of an instance.
py__simple_getitem__(index: int/str)   Returns a a set of types of the index.
                                       Can raise an IndexError/KeyError.
py__getitem__(indexes: ContextSet)     Returns a a set of types of the index.
py__file__()                           Only on modules. Returns None if does
                                       not exist.
py__package__() -> List[str]           Only on modules. For the import system.
py__path__()                           Only on modules. For the import system.
py__get__(call_object)                 Only on instances. Simulates
                                       descriptors.
py__doc__()                            Returns the docstring for a context.
====================================== ========================================

"""
from jedi import debug
from jedi._compatibility import use_metaclass
from jedi.parser_utils import get_cached_parent_scope
from jedi.evaluate.cache import evaluator_method_cache, CachedMetaClass, \
    evaluator_method_generator_cache
from jedi.evaluate import compiled
from jedi.evaluate.lazy_context import LazyKnownContexts
from jedi.evaluate.filters import ParserTreeFilter
from jedi.evaluate.names import TreeNameDefinition, ContextName
from jedi.evaluate.arguments import unpack_arglist, ValuesArguments
from jedi.evaluate.base_context import ContextSet, iterator_to_context_set, \
    NO_CONTEXTS
from jedi.evaluate.context.function import FunctionAndClassBase
from jedi.plugins import plugin_manager


def apply_py__get__(context, instance, class_context):
    try:
        method = context.py__get__
    except AttributeError:
        yield context
    else:
        for descriptor_context in method(instance, class_context):
            yield descriptor_context


class ClassName(TreeNameDefinition):
    def __init__(self, parent_context, tree_name, name_context, apply_decorators):
        super(ClassName, self).__init__(parent_context, tree_name)
        self._name_context = name_context
        self._apply_decorators = apply_decorators

    @iterator_to_context_set
    def infer(self):
        # We're using a different context to infer, so we cannot call super().
        from jedi.evaluate.syntax_tree import tree_name_to_contexts
        inferred = tree_name_to_contexts(
            self.parent_context.evaluator, self._name_context, self.tree_name)

        for result_context in inferred:
            if self._apply_decorators:
                for c in apply_py__get__(result_context,
                                         instance=None,
                                         class_context=self.parent_context):
                    yield c
            else:
                yield result_context


class ClassFilter(ParserTreeFilter):
    name_class = ClassName

    def __init__(self, *args, **kwargs):
        self._is_instance = kwargs.pop('is_instance')  # Python 2 :/
        super(ClassFilter, self).__init__(*args, **kwargs)

    def _convert_names(self, names):
        return [
            self.name_class(
                parent_context=self.context,
                tree_name=name,
                name_context=self._node_context,
                apply_decorators=not self._is_instance,
            ) for name in names
        ]

    def _equals_origin_scope(self):
        node = self._origin_scope
        while node is not None:
            if node == self._parser_scope or node == self.context:
                return True
            node = get_cached_parent_scope(self._used_names, node)
        return False

    def _access_possible(self, name, from_instance=False):
        # Filter for ClassVar variables
        # TODO this is not properly done, yet. It just checks for the string
        # ClassVar in the annotation, which can be quite imprecise. If we
        # wanted to do this correct, we would have to resolve the ClassVar.
        if not from_instance:
            expr_stmt = name.get_definition()
            if expr_stmt is not None and expr_stmt.type == 'expr_stmt':
                annassign = expr_stmt.children[1]
                if annassign.type == 'annassign':
                    # TODO this is not proper matching
                    if 'ClassVar' not in annassign.children[1].get_code():
                        return False

        # Filter for name mangling of private variables like __foo
        return not name.value.startswith('__') or name.value.endswith('__') \
            or self._equals_origin_scope()

    def _filter(self, names, from_instance=False):
        names = super(ClassFilter, self)._filter(names)
        return [name for name in names if self._access_possible(name, from_instance)]


class ClassMixin(object):
    def is_class(self):
        return True

    def py__call__(self, arguments=None):
        from jedi.evaluate.context import TreeInstance
        if arguments is None:
            arguments = ValuesArguments([])
        return ContextSet([TreeInstance(self.evaluator, self.parent_context, self, arguments)])

    def py__class__(self):
        return compiled.builtin_from_name(self.evaluator, u'type')

    @property
    def name(self):
        return ContextName(self, self.tree_node.name)

    def py__name__(self):
        return self.name.string_name

    def get_param_names(self):
        for context_ in self.py__getattribute__(u'__init__'):
            if context_.is_function():
                return list(context_.get_param_names())[1:]
        return []

    @evaluator_method_generator_cache()
    def py__mro__(self):
        mro = [self]
        yield self
        # TODO Do a proper mro resolution. Currently we are just listing
        # classes. However, it's a complicated algorithm.
        for lazy_cls in self.py__bases__():
            # TODO there's multiple different mro paths possible if this yields
            # multiple possibilities. Could be changed to be more correct.
            for cls in lazy_cls.infer():
                # TODO detect for TypeError: duplicate base class str,
                # e.g.  `class X(str, str): pass`
                try:
                    mro_method = cls.py__mro__
                except AttributeError:
                    # TODO add a TypeError like:
                    """
                    >>> class Y(lambda: test): pass
                    Traceback (most recent call last):
                      File "<stdin>", line 1, in <module>
                    TypeError: function() argument 1 must be code, not str
                    >>> class Y(1): pass
                    Traceback (most recent call last):
                      File "<stdin>", line 1, in <module>
                    TypeError: int() takes at most 2 arguments (3 given)
                    """
                    debug.warning('Super class of %s is not a class: %s', self, cls)
                else:
                    for cls_new in mro_method():
                        if cls_new not in mro:
                            mro.append(cls_new)
                            yield cls_new

    def get_filters(self, search_global=False, until_position=None,
                    origin_scope=None, is_instance=False):
        metaclasses = self.get_metaclasses()
        if metaclasses:
            for f in self.get_metaclass_filters(metaclasses):
                yield f

        if search_global:
            yield self.get_global_filter(until_position, origin_scope)
        else:
            for cls in self.py__mro__():
                if isinstance(cls, compiled.CompiledObject):
                    for filter in cls.get_filters(is_instance=is_instance):
                        yield filter
                else:
                    yield ClassFilter(
                        self.evaluator, self, node_context=cls,
                        origin_scope=origin_scope,
                        is_instance=is_instance
                    )
        if not is_instance:
            from jedi.evaluate.compiled import builtin_from_name
            type_ = builtin_from_name(self.evaluator, u'type')
            assert isinstance(type_, ClassContext)
            if type_ != self:
                for instance in type_.py__call__():
                    instance_filters = instance.get_filters()
                    # Filter out self filters
                    next(instance_filters)
                    next(instance_filters)
                    yield next(instance_filters)

    def get_signatures(self):
        init_funcs = self.py__call__().py__getattribute__('__init__')
        return [sig.bind(self) for sig in init_funcs.get_signatures()]

    def get_global_filter(self, until_position=None, origin_scope=None):
        return ParserTreeFilter(
            self.evaluator,
            context=self,
            until_position=until_position,
            origin_scope=origin_scope
        )


class ClassContext(use_metaclass(CachedMetaClass, ClassMixin, FunctionAndClassBase)):
    """
    This class is not only important to extend `tree.Class`, it is also a
    important for descriptors (if the descriptor methods are evaluated or not).
    """
    api_type = u'class'

    @evaluator_method_cache()
    def list_type_vars(self):
        found = []
        arglist = self.tree_node.get_super_arglist()
        if arglist is None:
            return []

        for stars, node in unpack_arglist(arglist):
            if stars:
                continue  # These are not relevant for this search.

            from jedi.evaluate.gradual.annotation import find_unknown_type_vars
            for type_var in find_unknown_type_vars(self.parent_context, node):
                if type_var not in found:
                    # The order matters and it's therefore a list.
                    found.append(type_var)
        return found

    def _get_bases_arguments(self):
        arglist = self.tree_node.get_super_arglist()
        if arglist:
            from jedi.evaluate import arguments
            return arguments.TreeArguments(self.evaluator, self.parent_context, arglist)
        return None

    @evaluator_method_cache(default=())
    def py__bases__(self):
        args = self._get_bases_arguments()
        if args is not None:
            lst = [value for key, value in args.unpack() if key is None]
            if lst:
                return lst

        if self.py__name__() == 'object' \
                and self.parent_context == self.evaluator.builtins_module:
            return []
        return [LazyKnownContexts(
            self.evaluator.builtins_module.py__getattribute__('object')
        )]

    def py__getitem__(self, index_context_set, contextualized_node):
        from jedi.evaluate.gradual.typing import LazyGenericClass
        if not index_context_set:
            return ContextSet([self])
        return ContextSet(
            LazyGenericClass(
                self,
                index_context,
                context_of_index=contextualized_node.context,
            )
            for index_context in index_context_set
        )

    def define_generics(self, type_var_dict):
        from jedi.evaluate.gradual.typing import GenericClass

        def remap_type_vars():
            """
            The TypeVars in the resulting classes have sometimes different names
            and we need to check for that, e.g. a signature can be:

            def iter(iterable: Iterable[_T]) -> Iterator[_T]: ...

            However, the iterator is defined as Iterator[_T_co], which means it has
            a different type var name.
            """
            for type_var in self.list_type_vars():
                yield type_var_dict.get(type_var.py__name__(), NO_CONTEXTS)

        if type_var_dict:
            return ContextSet([GenericClass(
                self,
                generics=tuple(remap_type_vars())
            )])
        return ContextSet({self})

    @plugin_manager.decorate()
    def get_metaclass_filters(self, metaclass):
        debug.dbg('Unprocessed metaclass %s', metaclass)
        return []

    @evaluator_method_cache(default=NO_CONTEXTS)
    def get_metaclasses(self):
        args = self._get_bases_arguments()
        if args is not None:
            m = [value for key, value in args.unpack() if key == 'metaclass']
            metaclasses = ContextSet.from_sets(lazy_context.infer() for lazy_context in m)
            metaclasses = ContextSet(m for m in metaclasses if m.is_class())
            if metaclasses:
                return metaclasses

        for lazy_base in self.py__bases__():
            for context in lazy_base.infer():
                if context.is_class():
                    contexts = context.get_metaclasses()
                    if contexts:
                        return contexts
        return NO_CONTEXTS
