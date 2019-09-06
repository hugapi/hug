"""
We need to somehow work with the typing objects. Since the typing objects are
pretty bare we need to add all the Jedi customizations to make them work as
contexts.

This file deals with all the typing.py cases.
"""
from jedi._compatibility import unicode, force_unicode
from jedi import debug
from jedi.evaluate.cache import evaluator_method_cache
from jedi.evaluate.compiled import builtin_from_name
from jedi.evaluate.base_context import ContextSet, NO_CONTEXTS, Context, \
    iterator_to_context_set, ContextWrapper, LazyContextWrapper
from jedi.evaluate.lazy_context import LazyKnownContexts
from jedi.evaluate.context.iterable import SequenceLiteralContext
from jedi.evaluate.arguments import repack_with_argument_clinic
from jedi.evaluate.utils import to_list
from jedi.evaluate.filters import FilterWrapper
from jedi.evaluate.names import NameWrapper, AbstractTreeName, \
    AbstractNameDefinition, ContextName
from jedi.evaluate.helpers import is_string
from jedi.evaluate.context.klass import ClassMixin, ClassFilter

_PROXY_CLASS_TYPES = 'Tuple Generic Protocol Callable Type'.split()
_TYPE_ALIAS_TYPES = {
    'List': 'builtins.list',
    'Dict': 'builtins.dict',
    'Set': 'builtins.set',
    'FrozenSet': 'builtins.frozenset',
    'ChainMap': 'collections.ChainMap',
    'Counter': 'collections.Counter',
    'DefaultDict': 'collections.defaultdict',
    'Deque': 'collections.deque',
}
_PROXY_TYPES = 'Optional Union ClassVar'.split()


class TypingName(AbstractTreeName):
    def __init__(self, context, other_name):
        super(TypingName, self).__init__(context.parent_context, other_name.tree_name)
        self._context = context

    def infer(self):
        return ContextSet([self._context])


class _BaseTypingContext(Context):
    def __init__(self, evaluator, parent_context, tree_name):
        super(_BaseTypingContext, self).__init__(evaluator, parent_context)
        self._tree_name = tree_name

    @property
    def tree_node(self):
        return self._tree_name

    def get_filters(self, *args, **kwargs):
        # TODO this is obviously wrong. Is it though?
        class EmptyFilter(ClassFilter):
            def __init__(self):
                pass

            def get(self, name, **kwargs):
                return []

            def values(self, **kwargs):
                return []

        yield EmptyFilter()

    def py__class__(self):
        # TODO this is obviously not correct, but at least gives us a class if
        # we have none. Some of these objects don't really have a base class in
        # typeshed.
        return builtin_from_name(self.evaluator, u'object')

    @property
    def name(self):
        return ContextName(self, self._tree_name)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._tree_name.value)


class TypingModuleName(NameWrapper):
    def infer(self):
        return ContextSet(self._remap())

    def _remap(self):
        name = self.string_name
        evaluator = self.parent_context.evaluator
        try:
            actual = _TYPE_ALIAS_TYPES[name]
        except KeyError:
            pass
        else:
            yield TypeAlias.create_cached(evaluator, self.parent_context, self.tree_name, actual)
            return

        if name in _PROXY_CLASS_TYPES:
            yield TypingClassContext.create_cached(evaluator, self.parent_context, self.tree_name)
        elif name in _PROXY_TYPES:
            yield TypingContext.create_cached(evaluator, self.parent_context, self.tree_name)
        elif name == 'runtime':
            # We don't want anything here, not sure what this function is
            # supposed to do, since it just appears in the stubs and shouldn't
            # have any effects there (because it's never executed).
            return
        elif name == 'TypeVar':
            yield TypeVarClass.create_cached(evaluator, self.parent_context, self.tree_name)
        elif name == 'Any':
            yield Any.create_cached(evaluator, self.parent_context, self.tree_name)
        elif name == 'TYPE_CHECKING':
            # This is needed for e.g. imports that are only available for type
            # checking or are in cycles. The user can then check this variable.
            yield builtin_from_name(evaluator, u'True')
        elif name == 'overload':
            yield OverloadFunction.create_cached(evaluator, self.parent_context, self.tree_name)
        elif name == 'NewType':
            yield NewTypeFunction.create_cached(evaluator, self.parent_context, self.tree_name)
        elif name == 'cast':
            # TODO implement cast
            yield CastFunction.create_cached(evaluator, self.parent_context, self.tree_name)
        elif name == 'TypedDict':
            # TODO doesn't even exist in typeshed/typing.py, yet. But will be
            # added soon.
            pass
        elif name in ('no_type_check', 'no_type_check_decorator'):
            # This is not necessary, as long as we are not doing type checking.
            for c in self._wrapped_name.infer():  # Fuck my life Python 2
                yield c
        else:
            # Everything else shouldn't be relevant for type checking.
            for c in self._wrapped_name.infer():  # Fuck my life Python 2
                yield c


class TypingModuleFilterWrapper(FilterWrapper):
    name_wrapper_class = TypingModuleName


class _WithIndexBase(_BaseTypingContext):
    def __init__(self, evaluator, parent_context, name, index_context, context_of_index):
        super(_WithIndexBase, self).__init__(evaluator, parent_context, name)
        self._index_context = index_context
        self._context_of_index = context_of_index

    def __repr__(self):
        return '<%s: %s[%s]>' % (
            self.__class__.__name__,
            self._tree_name.value,
            self._index_context,
        )


class TypingContextWithIndex(_WithIndexBase):
    def execute_annotation(self):
        string_name = self._tree_name.value

        if string_name == 'Union':
            # This is kind of a special case, because we have Unions (in Jedi
            # ContextSets).
            return self.gather_annotation_classes().execute_annotation()
        elif string_name == 'Optional':
            # Optional is basically just saying it's either None or the actual
            # type.
            return self.gather_annotation_classes().execute_annotation() \
                | ContextSet([builtin_from_name(self.evaluator, u'None')])
        elif string_name == 'Type':
            # The type is actually already given in the index_context
            return ContextSet([self._index_context])
        elif string_name == 'ClassVar':
            # For now don't do anything here, ClassVars are always used.
            return self._index_context.execute_annotation()

        cls = globals()[string_name]
        return ContextSet([cls(
            self.evaluator,
            self.parent_context,
            self._tree_name,
            self._index_context,
            self._context_of_index
        )])

    def gather_annotation_classes(self):
        return ContextSet.from_sets(
            _iter_over_arguments(self._index_context, self._context_of_index)
        )


class TypingContext(_BaseTypingContext):
    index_class = TypingContextWithIndex
    py__simple_getitem__ = None

    def py__getitem__(self, index_context_set, contextualized_node):
        return ContextSet(
            self.index_class.create_cached(
                self.evaluator,
                self.parent_context,
                self._tree_name,
                index_context,
                context_of_index=contextualized_node.context)
            for index_context in index_context_set
        )


class _TypingClassMixin(object):
    def py__bases__(self):
        return [LazyKnownContexts(
            self.evaluator.builtins_module.py__getattribute__('object')
        )]

    def get_metaclasses(self):
        return []


class TypingClassContextWithIndex(_TypingClassMixin, TypingContextWithIndex, ClassMixin):
    pass


class TypingClassContext(_TypingClassMixin, TypingContext, ClassMixin):
    index_class = TypingClassContextWithIndex


def _iter_over_arguments(maybe_tuple_context, defining_context):
    def iterate():
        if isinstance(maybe_tuple_context, SequenceLiteralContext):
            for lazy_context in maybe_tuple_context.py__iter__(contextualized_node=None):
                yield lazy_context.infer()
        else:
            yield ContextSet([maybe_tuple_context])

    def resolve_forward_references(context_set):
        for context in context_set:
            if is_string(context):
                from jedi.evaluate.gradual.annotation import _get_forward_reference_node
                node = _get_forward_reference_node(defining_context, context.get_safe_value())
                if node is not None:
                    for c in defining_context.eval_node(node):
                        yield c
            else:
                yield context

    for context_set in iterate():
        yield ContextSet(resolve_forward_references(context_set))


class TypeAlias(LazyContextWrapper):
    def __init__(self, parent_context, origin_tree_name, actual):
        self.evaluator = parent_context.evaluator
        self.parent_context = parent_context
        self._origin_tree_name = origin_tree_name
        self._actual = actual  # e.g. builtins.list

    @property
    def name(self):
        return ContextName(self, self._origin_tree_name)

    def py__name__(self):
        return self.name.string_name

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._actual)

    def _get_wrapped_context(self):
        module_name, class_name = self._actual.split('.')
        if self.evaluator.environment.version_info.major == 2 and module_name == 'builtins':
            module_name = '__builtin__'

        # TODO use evaluator.import_module?
        from jedi.evaluate.imports import Importer
        module, = Importer(
            self.evaluator, [module_name], self.evaluator.builtins_module
        ).follow()
        classes = module.py__getattribute__(class_name)
        # There should only be one, because it's code that we control.
        assert len(classes) == 1, classes
        cls = next(iter(classes))
        return cls


class _ContainerBase(_WithIndexBase):
    def _get_getitem_contexts(self, index):
        args = _iter_over_arguments(self._index_context, self._context_of_index)
        for i, contexts in enumerate(args):
            if i == index:
                return contexts

        debug.warning('No param #%s found for annotation %s', index, self._index_context)
        return NO_CONTEXTS


class Callable(_ContainerBase):
    def py__call__(self, arguments):
        # The 0th index are the arguments.
        return self._get_getitem_contexts(1).execute_annotation()


class Tuple(_ContainerBase):
    def _is_homogenous(self):
        # To specify a variable-length tuple of homogeneous type, Tuple[T, ...]
        # is used.
        if isinstance(self._index_context, SequenceLiteralContext):
            entries = self._index_context.get_tree_entries()
            if len(entries) == 2 and entries[1] == '...':
                return True
        return False

    def py__simple_getitem__(self, index):
        if self._is_homogenous():
            return self._get_getitem_contexts(0).execute_annotation()
        else:
            if isinstance(index, int):
                return self._get_getitem_contexts(index).execute_annotation()

            debug.dbg('The getitem type on Tuple was %s' % index)
            return NO_CONTEXTS

    def py__iter__(self, contextualized_node=None):
        if self._is_homogenous():
            yield LazyKnownContexts(self._get_getitem_contexts(0).execute_annotation())
        else:
            if isinstance(self._index_context, SequenceLiteralContext):
                for i in range(self._index_context.py__len__()):
                    yield LazyKnownContexts(self._get_getitem_contexts(i).execute_annotation())

    def py__getitem__(self, index_context_set, contextualized_node):
        if self._is_homogenous():
            return self._get_getitem_contexts(0).execute_annotation()

        return ContextSet.from_sets(
            _iter_over_arguments(self._index_context, self._context_of_index)
        ).execute_annotation()


class Generic(_ContainerBase):
    pass


class Protocol(_ContainerBase):
    pass


class Any(_BaseTypingContext):
    def execute_annotation(self):
        debug.warning('Used Any - returned no results')
        return NO_CONTEXTS


class TypeVarClass(_BaseTypingContext):
    def py__call__(self, arguments):
        unpacked = arguments.unpack()

        key, lazy_context = next(unpacked, (None, None))
        var_name = self._find_string_name(lazy_context)
        # The name must be given, otherwise it's useless.
        if var_name is None or key is not None:
            debug.warning('Found a variable without a name %s', arguments)
            return NO_CONTEXTS

        return ContextSet([TypeVar.create_cached(
            self.evaluator,
            self.parent_context,
            self._tree_name,
            var_name,
            unpacked
        )])

    def _find_string_name(self, lazy_context):
        if lazy_context is None:
            return None

        context_set = lazy_context.infer()
        if not context_set:
            return None
        if len(context_set) > 1:
            debug.warning('Found multiple contexts for a type variable: %s', context_set)

        name_context = next(iter(context_set))
        try:
            method = name_context.get_safe_value
        except AttributeError:
            return None
        else:
            safe_value = method(default=None)
            if self.evaluator.environment.version_info.major == 2:
                if isinstance(safe_value, bytes):
                    return force_unicode(safe_value)
            if isinstance(safe_value, (str, unicode)):
                return safe_value
            return None


class TypeVar(_BaseTypingContext):
    def __init__(self, evaluator, parent_context, tree_name, var_name, unpacked_args):
        super(TypeVar, self).__init__(evaluator, parent_context, tree_name)
        self._var_name = var_name

        self._constraints_lazy_contexts = []
        self._bound_lazy_context = None
        self._covariant_lazy_context = None
        self._contravariant_lazy_context = None
        for key, lazy_context in unpacked_args:
            if key is None:
                self._constraints_lazy_contexts.append(lazy_context)
            else:
                if key == 'bound':
                    self._bound_lazy_context = lazy_context
                elif key == 'covariant':
                    self._covariant_lazy_context = lazy_context
                elif key == 'contravariant':
                    self._contra_variant_lazy_context = lazy_context
                else:
                    debug.warning('Invalid TypeVar param name %s', key)

    def py__name__(self):
        return self._var_name

    def get_filters(self, *args, **kwargs):
        return iter([])

    def _get_classes(self):
        if self._bound_lazy_context is not None:
            return self._bound_lazy_context.infer()
        if self._constraints_lazy_contexts:
            return self.constraints
        debug.warning('Tried to infer the TypeVar %s without a given type', self._var_name)
        return NO_CONTEXTS

    def is_same_class(self, other):
        # Everything can match an undefined type var.
        return True

    @property
    def constraints(self):
        return ContextSet.from_sets(
            lazy.infer() for lazy in self._constraints_lazy_contexts
        )

    def define_generics(self, type_var_dict):
        try:
            found = type_var_dict[self.py__name__()]
        except KeyError:
            pass
        else:
            if found:
                return found
        return self._get_classes() or ContextSet({self})

    def execute_annotation(self):
        return self._get_classes().execute_annotation()

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.py__name__())


class OverloadFunction(_BaseTypingContext):
    @repack_with_argument_clinic('func, /')
    def py__call__(self, func_context_set):
        # Just pass arguments through.
        return func_context_set


class NewTypeFunction(_BaseTypingContext):
    def py__call__(self, arguments):
        ordered_args = arguments.unpack()
        next(ordered_args, (None, None))
        _, second_arg = next(ordered_args, (None, None))
        if second_arg is None:
            return NO_CONTEXTS
        return ContextSet(
            NewType(
                self.evaluator,
                contextualized_node.context,
                contextualized_node.node,
                second_arg.infer(),
            ) for contextualized_node in arguments.get_calling_nodes())


class NewType(Context):
    def __init__(self, evaluator, parent_context, tree_node, type_context_set):
        super(NewType, self).__init__(evaluator, parent_context)
        self._type_context_set = type_context_set
        self.tree_node = tree_node

    def py__call__(self, arguments):
        return self._type_context_set.execute_annotation()


class CastFunction(_BaseTypingContext):
    @repack_with_argument_clinic('type, object, /')
    def py__call__(self, type_context_set, object_context_set):
        return type_context_set.execute_annotation()


class BoundTypeVarName(AbstractNameDefinition):
    """
    This type var was bound to a certain type, e.g. int.
    """
    def __init__(self, type_var, context_set):
        self._type_var = type_var
        self.parent_context = type_var.parent_context
        self._context_set = context_set

    def infer(self):
        def iter_():
            for context in self._context_set:
                # Replace any with the constraints if they are there.
                if isinstance(context, Any):
                    for constraint in self._type_var.constraints:
                        yield constraint
                else:
                    yield context
        return ContextSet(iter_())

    def py__name__(self):
        return self._type_var.py__name__()

    def __repr__(self):
        return '<%s %s -> %s>' % (self.__class__.__name__, self.py__name__(), self._context_set)


class TypeVarFilter(object):
    """
    A filter for all given variables in a class.

        A = TypeVar('A')
        B = TypeVar('B')
        class Foo(Mapping[A, B]):
            ...

    In this example we would have two type vars given: A and B
    """
    def __init__(self, generics, type_vars):
        self._generics = generics
        self._type_vars = type_vars

    def get(self, name):
        for i, type_var in enumerate(self._type_vars):
            if type_var.py__name__() == name:
                try:
                    return [BoundTypeVarName(type_var, self._generics[i])]
                except IndexError:
                    return [type_var.name]
        return []

    def values(self):
        # The values are not relevant. If it's not searched exactly, the type
        # vars are just global and should be looked up as that.
        return []


class AbstractAnnotatedClass(ClassMixin, ContextWrapper):
    def get_type_var_filter(self):
        return TypeVarFilter(self.get_generics(), self.list_type_vars())

    def get_filters(self, search_global=False, *args, **kwargs):
        filters = super(AbstractAnnotatedClass, self).get_filters(
            search_global,
            *args, **kwargs
        )
        for f in filters:
            yield f

        if search_global:
            # The type vars can only be looked up if it's a global search and
            # not a direct lookup on the class.
            yield self.get_type_var_filter()

    def is_same_class(self, other):
        if not isinstance(other, AbstractAnnotatedClass):
            return False

        if self.tree_node != other.tree_node:
            # TODO not sure if this is nice.
            return False
        given_params1 = self.get_generics()
        given_params2 = other.get_generics()

        if len(given_params1) != len(given_params2):
            # If the amount of type vars doesn't match, the class doesn't
            # match.
            return False

        # Now compare generics
        return all(
            any(
                # TODO why is this ordering the correct one?
                cls2.is_same_class(cls1)
                for cls1 in class_set1
                for cls2 in class_set2
            ) for class_set1, class_set2 in zip(given_params1, given_params2)
        )

    def py__call__(self, arguments):
        instance, = super(AbstractAnnotatedClass, self).py__call__(arguments)
        return ContextSet([InstanceWrapper(instance)])

    def get_generics(self):
        raise NotImplementedError

    def define_generics(self, type_var_dict):
        changed = False
        new_generics = []
        for generic_set in self.get_generics():
            contexts = NO_CONTEXTS
            for generic in generic_set:
                if isinstance(generic, (AbstractAnnotatedClass, TypeVar)):
                    result = generic.define_generics(type_var_dict)
                    contexts |= result
                    if result != ContextSet({generic}):
                        changed = True
                else:
                    contexts |= ContextSet([generic])
            new_generics.append(contexts)

        if not changed:
            # There might not be any type vars that change. In that case just
            # return itself, because it does not make sense to potentially lose
            # cached results.
            return ContextSet([self])

        return ContextSet([GenericClass(
            self._wrapped_context,
            generics=tuple(new_generics)
        )])

    def __repr__(self):
        return '<%s: %s%s>' % (
            self.__class__.__name__,
            self._wrapped_context,
            list(self.get_generics()),
        )

    @to_list
    def py__bases__(self):
        for base in self._wrapped_context.py__bases__():
            yield LazyAnnotatedBaseClass(self, base)


class LazyGenericClass(AbstractAnnotatedClass):
    def __init__(self, class_context, index_context, context_of_index):
        super(LazyGenericClass, self).__init__(class_context)
        self._index_context = index_context
        self._context_of_index = context_of_index

    @evaluator_method_cache()
    def get_generics(self):
        return list(_iter_over_arguments(self._index_context, self._context_of_index))


class GenericClass(AbstractAnnotatedClass):
    def __init__(self, class_context, generics):
        super(GenericClass, self).__init__(class_context)
        self._generics = generics

    def get_generics(self):
        return self._generics


class LazyAnnotatedBaseClass(object):
    def __init__(self, class_context, lazy_base_class):
        self._class_context = class_context
        self._lazy_base_class = lazy_base_class

    @iterator_to_context_set
    def infer(self):
        for base in self._lazy_base_class.infer():
            if isinstance(base, AbstractAnnotatedClass):
                # Here we have to recalculate the given types.
                yield GenericClass.create_cached(
                    base.evaluator,
                    base._wrapped_context,
                    tuple(self._remap_type_vars(base)),
                )
            else:
                yield base

    def _remap_type_vars(self, base):
        filter = self._class_context.get_type_var_filter()
        for type_var_set in base.get_generics():
            new = NO_CONTEXTS
            for type_var in type_var_set:
                if isinstance(type_var, TypeVar):
                    names = filter.get(type_var.py__name__())
                    new |= ContextSet.from_sets(
                        name.infer() for name in names
                    )
                else:
                    # Mostly will be type vars, except if in some cases
                    # a concrete type will already be there. In that
                    # case just add it to the context set.
                    new |= ContextSet([type_var])
            yield new


class InstanceWrapper(ContextWrapper):
    def py__stop_iteration_returns(self):
        for cls in self._wrapped_context.class_context.py__mro__():
            if cls.py__name__() == 'Generator':
                generics = cls.get_generics()
                try:
                    return generics[2].execute_annotation()
                except IndexError:
                    pass
            elif cls.py__name__() == 'Iterator':
                return ContextSet([builtin_from_name(self.evaluator, u'None')])
        return self._wrapped_context.py__stop_iteration_returns()
