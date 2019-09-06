from parso.python import tree

from jedi._compatibility import use_metaclass
from jedi import debug
from jedi.evaluate.cache import evaluator_method_cache, CachedMetaClass
from jedi.evaluate import compiled
from jedi.evaluate import recursion
from jedi.evaluate import docstrings
from jedi.evaluate import flow_analysis
from jedi.evaluate import helpers
from jedi.evaluate.signature import TreeSignature
from jedi.evaluate.arguments import AnonymousArguments
from jedi.evaluate.filters import ParserTreeFilter, FunctionExecutionFilter
from jedi.evaluate.names import ContextName, AbstractNameDefinition, ParamName
from jedi.evaluate.base_context import ContextualizedNode, NO_CONTEXTS, \
    ContextSet, TreeContext, ContextWrapper
from jedi.evaluate.lazy_context import LazyKnownContexts, LazyKnownContext, \
    LazyTreeContext
from jedi.evaluate.context import iterable
from jedi import parser_utils
from jedi.evaluate.parser_cache import get_yield_exprs
from jedi.evaluate.helpers import contexts_from_qualified_names


class LambdaName(AbstractNameDefinition):
    string_name = '<lambda>'
    api_type = u'function'

    def __init__(self, lambda_context):
        self._lambda_context = lambda_context
        self.parent_context = lambda_context.parent_context

    @property
    def start_pos(self):
        return self._lambda_context.tree_node.start_pos

    def infer(self):
        return ContextSet([self._lambda_context])


class FunctionAndClassBase(TreeContext):
    def get_qualified_names(self):
        if self.parent_context.is_class():
            n = self.parent_context.get_qualified_names()
            if n is None:
                # This means that the parent class lives within a function.
                return None
            return n + (self.py__name__(),)
        elif self.parent_context.is_module():
            return (self.py__name__(),)
        else:
            return None


class FunctionMixin(object):
    api_type = u'function'

    def get_filters(self, search_global=False, until_position=None, origin_scope=None):
        if search_global:
            yield ParserTreeFilter(
                self.evaluator,
                context=self,
                until_position=until_position,
                origin_scope=origin_scope
            )
        else:
            cls = self.py__class__()
            for instance in cls.execute_evaluated():
                for filter in instance.get_filters(search_global=False, origin_scope=origin_scope):
                    yield filter

    def py__get__(self, instance, class_context):
        from jedi.evaluate.context.instance import BoundMethod
        if instance is None:
            # Calling the Foo.bar results in the original bar function.
            return ContextSet([self])
        return ContextSet([BoundMethod(instance, self)])

    def get_param_names(self):
        function_execution = self.get_function_execution()
        return [ParamName(function_execution, param.name)
                for param in self.tree_node.get_params()]

    @property
    def name(self):
        if self.tree_node.type == 'lambdef':
            return LambdaName(self)
        return ContextName(self, self.tree_node.name)

    def py__name__(self):
        return self.name.string_name

    def py__call__(self, arguments):
        function_execution = self.get_function_execution(arguments)
        return function_execution.infer()

    def get_function_execution(self, arguments=None):
        if arguments is None:
            arguments = AnonymousArguments()

        return FunctionExecutionContext(self.evaluator, self.parent_context, self, arguments)

    def get_signatures(self):
        return [TreeSignature(f) for f in self.get_signature_functions()]


class FunctionContext(use_metaclass(CachedMetaClass, FunctionMixin, FunctionAndClassBase)):
    """
    Needed because of decorators. Decorators are evaluated here.
    """
    def is_function(self):
        return True

    @classmethod
    def from_context(cls, context, tree_node):
        def create(tree_node):
            if context.is_class():
                return MethodContext(
                    context.evaluator,
                    context,
                    parent_context=parent_context,
                    tree_node=tree_node
                )
            else:
                return cls(
                    context.evaluator,
                    parent_context=parent_context,
                    tree_node=tree_node
                )

        overloaded_funcs = list(_find_overload_functions(context, tree_node))

        parent_context = context
        while parent_context.is_class() or parent_context.is_instance():
            parent_context = parent_context.parent_context

        function = create(tree_node)

        if overloaded_funcs:
            return OverloadedFunctionContext(
                function,
                [create(f) for f in overloaded_funcs]
            )
        return function

    def py__class__(self):
        c, = contexts_from_qualified_names(self.evaluator, u'types', u'FunctionType')
        return c

    def get_default_param_context(self):
        return self.parent_context

    def get_signature_functions(self):
        return [self]


class MethodContext(FunctionContext):
    def __init__(self, evaluator, class_context, *args, **kwargs):
        super(MethodContext, self).__init__(evaluator, *args, **kwargs)
        self.class_context = class_context

    def get_default_param_context(self):
        return self.class_context

    def get_qualified_names(self):
        # Need to implement this, because the parent context of a method
        # context is not the class context but the module.
        names = self.class_context.get_qualified_names()
        if names is None:
            return None
        return names + (self.py__name__(),)


class FunctionExecutionContext(TreeContext):
    """
    This class is used to evaluate functions and their returns.

    This is the most complicated class, because it contains the logic to
    transfer parameters. It is even more complicated, because there may be
    multiple calls to functions and recursion has to be avoided. But this is
    responsibility of the decorators.
    """
    function_execution_filter = FunctionExecutionFilter

    def __init__(self, evaluator, parent_context, function_context, var_args):
        super(FunctionExecutionContext, self).__init__(
            evaluator,
            parent_context,
            function_context.tree_node,
        )
        self.function_context = function_context
        self.var_args = var_args

    @evaluator_method_cache(default=NO_CONTEXTS)
    @recursion.execution_recursion_decorator()
    def get_return_values(self, check_yields=False):
        funcdef = self.tree_node
        if funcdef.type == 'lambdef':
            return self.eval_node(funcdef.children[-1])

        if check_yields:
            context_set = NO_CONTEXTS
            returns = get_yield_exprs(self.evaluator, funcdef)
        else:
            returns = funcdef.iter_return_stmts()
            from jedi.evaluate.gradual.annotation import infer_return_types
            context_set = infer_return_types(self)
            if context_set:
                # If there are annotations, prefer them over anything else.
                # This will make it faster.
                return context_set
            context_set |= docstrings.infer_return_types(self.function_context)

        for r in returns:
            check = flow_analysis.reachability_check(self, funcdef, r)
            if check is flow_analysis.UNREACHABLE:
                debug.dbg('Return unreachable: %s', r)
            else:
                if check_yields:
                    context_set |= ContextSet.from_sets(
                        lazy_context.infer()
                        for lazy_context in self._get_yield_lazy_context(r)
                    )
                else:
                    try:
                        children = r.children
                    except AttributeError:
                        ctx = compiled.builtin_from_name(self.evaluator, u'None')
                        context_set |= ContextSet([ctx])
                    else:
                        context_set |= self.eval_node(children[1])
            if check is flow_analysis.REACHABLE:
                debug.dbg('Return reachable: %s', r)
                break
        return context_set

    def _get_yield_lazy_context(self, yield_expr):
        if yield_expr.type == 'keyword':
            # `yield` just yields None.
            ctx = compiled.builtin_from_name(self.evaluator, u'None')
            yield LazyKnownContext(ctx)
            return

        node = yield_expr.children[1]
        if node.type == 'yield_arg':  # It must be a yield from.
            cn = ContextualizedNode(self, node.children[1])
            for lazy_context in cn.infer().iterate(cn):
                yield lazy_context
        else:
            yield LazyTreeContext(self, node)

    @recursion.execution_recursion_decorator(default=iter([]))
    def get_yield_lazy_contexts(self, is_async=False):
        # TODO: if is_async, wrap yield statements in Awaitable/async_generator_asend
        for_parents = [(y, tree.search_ancestor(y, 'for_stmt', 'funcdef',
                                                'while_stmt', 'if_stmt'))
                       for y in get_yield_exprs(self.evaluator, self.tree_node)]

        # Calculate if the yields are placed within the same for loop.
        yields_order = []
        last_for_stmt = None
        for yield_, for_stmt in for_parents:
            # For really simple for loops we can predict the order. Otherwise
            # we just ignore it.
            parent = for_stmt.parent
            if parent.type == 'suite':
                parent = parent.parent
            if for_stmt.type == 'for_stmt' and parent == self.tree_node \
                    and parser_utils.for_stmt_defines_one_name(for_stmt):  # Simplicity for now.
                if for_stmt == last_for_stmt:
                    yields_order[-1][1].append(yield_)
                else:
                    yields_order.append((for_stmt, [yield_]))
            elif for_stmt == self.tree_node:
                yields_order.append((None, [yield_]))
            else:
                types = self.get_return_values(check_yields=True)
                if types:
                    yield LazyKnownContexts(types)
                return
            last_for_stmt = for_stmt

        for for_stmt, yields in yields_order:
            if for_stmt is None:
                # No for_stmt, just normal yields.
                for yield_ in yields:
                    for result in self._get_yield_lazy_context(yield_):
                        yield result
            else:
                input_node = for_stmt.get_testlist()
                cn = ContextualizedNode(self, input_node)
                ordered = cn.infer().iterate(cn)
                ordered = list(ordered)
                for lazy_context in ordered:
                    dct = {str(for_stmt.children[1].value): lazy_context.infer()}
                    with helpers.predefine_names(self, for_stmt, dct):
                        for yield_in_same_for_stmt in yields:
                            for result in self._get_yield_lazy_context(yield_in_same_for_stmt):
                                yield result

    def merge_yield_contexts(self, is_async=False):
        return ContextSet.from_sets(
            lazy_context.infer()
            for lazy_context in self.get_yield_lazy_contexts()
        )

    def get_filters(self, search_global=False, until_position=None, origin_scope=None):
        yield self.function_execution_filter(self.evaluator, self,
                                             until_position=until_position,
                                             origin_scope=origin_scope)

    @evaluator_method_cache()
    def get_executed_params_and_issues(self):
        return self.var_args.get_executed_params_and_issues(self)

    def matches_signature(self):
        executed_params, issues = self.get_executed_params_and_issues()
        if issues:
            return False

        matches = all(executed_param.matches_signature()
                      for executed_param in executed_params)
        if debug.enable_notice:
            signature = parser_utils.get_call_signature(self.tree_node)
            if matches:
                debug.dbg("Overloading match: %s@%s (%s)",
                          signature, self.tree_node.start_pos[0], self.var_args, color='BLUE')
            else:
                debug.dbg("Overloading no match: %s@%s (%s)",
                          signature, self.tree_node.start_pos[0], self.var_args, color='BLUE')
        return matches

    def infer(self):
        """
        Created to be used by inheritance.
        """
        evaluator = self.evaluator
        is_coroutine = self.tree_node.parent.type in ('async_stmt', 'async_funcdef')
        is_generator = bool(get_yield_exprs(evaluator, self.tree_node))
        from jedi.evaluate.gradual.typing import GenericClass

        if is_coroutine:
            if is_generator:
                if evaluator.environment.version_info < (3, 6):
                    return NO_CONTEXTS
                async_generator_classes = evaluator.typing_module \
                    .py__getattribute__('AsyncGenerator')

                yield_contexts = self.merge_yield_contexts(is_async=True)
                # The contravariant doesn't seem to be defined.
                generics = (yield_contexts.py__class__(), NO_CONTEXTS)
                return ContextSet(
                    # In Python 3.6 AsyncGenerator is still a class.
                    GenericClass(c, generics)
                    for c in async_generator_classes
                ).execute_annotation()
            else:
                if evaluator.environment.version_info < (3, 5):
                    return NO_CONTEXTS
                async_classes = evaluator.typing_module.py__getattribute__('Coroutine')
                return_contexts = self.get_return_values()
                # Only the first generic is relevant.
                generics = (return_contexts.py__class__(), NO_CONTEXTS, NO_CONTEXTS)
                return ContextSet(
                    GenericClass(c, generics) for c in async_classes
                ).execute_annotation()
        else:
            if is_generator:
                return ContextSet([iterable.Generator(evaluator, self)])
            else:
                return self.get_return_values()


class OverloadedFunctionContext(FunctionMixin, ContextWrapper):
    def __init__(self, function, overloaded_functions):
        super(OverloadedFunctionContext, self).__init__(function)
        self._overloaded_functions = overloaded_functions

    def py__call__(self, arguments):
        debug.dbg("Execute overloaded function %s", self._wrapped_context, color='BLUE')
        function_executions = []
        context_set = NO_CONTEXTS
        matched = False
        for f in self._overloaded_functions:
            function_execution = f.get_function_execution(arguments)
            function_executions.append(function_execution)
            if function_execution.matches_signature():
                matched = True
                return function_execution.infer()

        if matched:
            return context_set

        if self.evaluator.is_analysis:
            # In this case we want precision.
            return NO_CONTEXTS
        return ContextSet.from_sets(fe.infer() for fe in function_executions)

    def get_signature_functions(self):
        return self._overloaded_functions


def _find_overload_functions(context, tree_node):
    def _is_overload_decorated(funcdef):
        if funcdef.parent.type == 'decorated':
            decorators = funcdef.parent.children[0]
            if decorators.type == 'decorator':
                decorators = [decorators]
            else:
                decorators = decorators.children
            for decorator in decorators:
                dotted_name = decorator.children[1]
                if dotted_name.type == 'name' and dotted_name.value == 'overload':
                    # TODO check with contexts if it's the right overload
                    return True
        return False

    if tree_node.type == 'lambdef':
        return

    if _is_overload_decorated(tree_node):
        yield tree_node

    while True:
        filter = ParserTreeFilter(
            context.evaluator,
            context,
            until_position=tree_node.start_pos
        )
        names = filter.get(tree_node.name.value)
        assert isinstance(names, list)
        if not names:
            break

        found = False
        for name in names:
            funcdef = name.tree_name.parent
            if funcdef.type == 'funcdef' and _is_overload_decorated(funcdef):
                tree_node = funcdef
                found = True
                yield funcdef

        if not found:
            break
