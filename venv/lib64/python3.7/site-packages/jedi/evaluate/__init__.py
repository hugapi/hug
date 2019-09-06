"""
Evaluation of Python code in |jedi| is based on three assumptions:

* The code uses as least side effects as possible. Jedi understands certain
  list/tuple/set modifications, but there's no guarantee that Jedi detects
  everything (list.append in different modules for example).
* No magic is being used:

  - metaclasses
  - ``setattr()`` / ``__import__()``
  - writing to ``globals()``, ``locals()``, ``object.__dict__``
* The programmer is not a total dick, e.g. like `this
  <https://github.com/davidhalter/jedi/issues/24>`_ :-)

The actual algorithm is based on a principle called lazy evaluation.  That
said, the typical entry point for static analysis is calling
``eval_expr_stmt``. There's separate logic for autocompletion in the API, the
evaluator is all about evaluating an expression.

TODO this paragraph is not what jedi does anymore, it's similar, but not the
same.

Now you need to understand what follows after ``eval_expr_stmt``. Let's
make an example::

    import datetime
    datetime.date.toda# <-- cursor here

First of all, this module doesn't care about completion. It really just cares
about ``datetime.date``. At the end of the procedure ``eval_expr_stmt`` will
return the ``date`` class.

To *visualize* this (simplified):

- ``Evaluator.eval_expr_stmt`` doesn't do much, because there's no assignment.
- ``Context.eval_node`` cares for resolving the dotted path
- ``Evaluator.find_types`` searches for global definitions of datetime, which
  it finds in the definition of an import, by scanning the syntax tree.
- Using the import logic, the datetime module is found.
- Now ``find_types`` is called again by ``eval_node`` to find ``date``
  inside the datetime module.

Now what would happen if we wanted ``datetime.date.foo.bar``? Two more
calls to ``find_types``. However the second call would be ignored, because the
first one would return nothing (there's no foo attribute in ``date``).

What if the import would contain another ``ExprStmt`` like this::

    from foo import bar
    Date = bar.baz

Well... You get it. Just another ``eval_expr_stmt`` recursion. It's really
easy. Python can obviously get way more complicated then this. To understand
tuple assignments, list comprehensions and everything else, a lot more code had
to be written.

Jedi has been tested very well, so you can just start modifying code. It's best
to write your own test first for your "new" feature. Don't be scared of
breaking stuff. As long as the tests pass, you're most likely to be fine.

I need to mention now that lazy evaluation is really good because it
only *evaluates* what needs to be *evaluated*. All the statements and modules
that are not used are just being ignored.
"""
from parso.python import tree
import parso
from parso import python_bytes_to_unicode
from jedi.file_io import FileIO

from jedi import debug
from jedi import parser_utils
from jedi.evaluate.utils import unite
from jedi.evaluate import imports
from jedi.evaluate import recursion
from jedi.evaluate.cache import evaluator_function_cache
from jedi.evaluate import helpers
from jedi.evaluate.names import TreeNameDefinition, ParamName
from jedi.evaluate.base_context import ContextualizedName, ContextualizedNode, \
    ContextSet, NO_CONTEXTS, iterate_contexts
from jedi.evaluate.context import ClassContext, FunctionContext, \
    AnonymousInstance, BoundMethod
from jedi.evaluate.context.iterable import CompForContext
from jedi.evaluate.syntax_tree import eval_trailer, eval_expr_stmt, \
    eval_node, check_tuple_assignments
from jedi.plugins import plugin_manager


class Evaluator(object):
    def __init__(self, project, environment=None, script_path=None):
        if environment is None:
            environment = project.get_environment()
        self.environment = environment
        self.script_path = script_path
        self.compiled_subprocess = environment.get_evaluator_subprocess(self)
        self.grammar = environment.get_grammar()

        self.latest_grammar = parso.load_grammar(version='3.7')
        self.memoize_cache = {}  # for memoize decorators
        self.module_cache = imports.ModuleCache()  # does the job of `sys.modules`.
        self.stub_module_cache = {}  # Dict[Tuple[str, ...], Optional[ModuleContext]]
        self.compiled_cache = {}  # see `evaluate.compiled.create()`
        self.inferred_element_counts = {}
        self.mixed_cache = {}  # see `evaluate.compiled.mixed._create()`
        self.analysis = []
        self.dynamic_params_depth = 0
        self.is_analysis = False
        self.project = project
        self.access_cache = {}
        self.allow_descriptor_getattr = False

        self.reset_recursion_limitations()
        self.allow_different_encoding = True

    def import_module(self, import_names, parent_module_context=None,
                      sys_path=None, prefer_stubs=True):
        if sys_path is None:
            sys_path = self.get_sys_path()
        return imports.import_module(self, import_names, parent_module_context,
                                     sys_path, prefer_stubs=prefer_stubs)

    @staticmethod
    @plugin_manager.decorate()
    def execute(context, arguments):
        debug.dbg('execute: %s %s', context, arguments)
        with debug.increase_indent_cm():
            context_set = context.py__call__(arguments=arguments)
        debug.dbg('execute result: %s in %s', context_set, context)
        return context_set

    @property
    @evaluator_function_cache()
    def builtins_module(self):
        module_name = u'builtins'
        if self.environment.version_info.major == 2:
            module_name = u'__builtin__'
        builtins_module, = self.import_module((module_name,), sys_path=())
        return builtins_module

    @property
    @evaluator_function_cache()
    def typing_module(self):
        typing_module, = self.import_module((u'typing',))
        return typing_module

    def reset_recursion_limitations(self):
        self.recursion_detector = recursion.RecursionDetector()
        self.execution_recursion_detector = recursion.ExecutionRecursionDetector(self)

    def get_sys_path(self, **kwargs):
        """Convenience function"""
        return self.project._get_sys_path(self, environment=self.environment, **kwargs)

    def eval_element(self, context, element):
        if isinstance(context, CompForContext):
            return eval_node(context, element)

        if_stmt = element
        while if_stmt is not None:
            if_stmt = if_stmt.parent
            if if_stmt.type in ('if_stmt', 'for_stmt'):
                break
            if parser_utils.is_scope(if_stmt):
                if_stmt = None
                break
        predefined_if_name_dict = context.predefined_names.get(if_stmt)
        # TODO there's a lot of issues with this one. We actually should do
        # this in a different way. Caching should only be active in certain
        # cases and this all sucks.
        if predefined_if_name_dict is None and if_stmt \
                and if_stmt.type == 'if_stmt' and self.is_analysis:
            if_stmt_test = if_stmt.children[1]
            name_dicts = [{}]
            # If we already did a check, we don't want to do it again -> If
            # context.predefined_names is filled, we stop.
            # We don't want to check the if stmt itself, it's just about
            # the content.
            if element.start_pos > if_stmt_test.end_pos:
                # Now we need to check if the names in the if_stmt match the
                # names in the suite.
                if_names = helpers.get_names_of_node(if_stmt_test)
                element_names = helpers.get_names_of_node(element)
                str_element_names = [e.value for e in element_names]
                if any(i.value in str_element_names for i in if_names):
                    for if_name in if_names:
                        definitions = self.goto_definitions(context, if_name)
                        # Every name that has multiple different definitions
                        # causes the complexity to rise. The complexity should
                        # never fall below 1.
                        if len(definitions) > 1:
                            if len(name_dicts) * len(definitions) > 16:
                                debug.dbg('Too many options for if branch evaluation %s.', if_stmt)
                                # There's only a certain amount of branches
                                # Jedi can evaluate, otherwise it will take to
                                # long.
                                name_dicts = [{}]
                                break

                            original_name_dicts = list(name_dicts)
                            name_dicts = []
                            for definition in definitions:
                                new_name_dicts = list(original_name_dicts)
                                for i, name_dict in enumerate(new_name_dicts):
                                    new_name_dicts[i] = name_dict.copy()
                                    new_name_dicts[i][if_name.value] = ContextSet([definition])

                                name_dicts += new_name_dicts
                        else:
                            for name_dict in name_dicts:
                                name_dict[if_name.value] = definitions
            if len(name_dicts) > 1:
                result = NO_CONTEXTS
                for name_dict in name_dicts:
                    with helpers.predefine_names(context, if_stmt, name_dict):
                        result |= eval_node(context, element)
                return result
            else:
                return self._eval_element_if_evaluated(context, element)
        else:
            if predefined_if_name_dict:
                return eval_node(context, element)
            else:
                return self._eval_element_if_evaluated(context, element)

    def _eval_element_if_evaluated(self, context, element):
        """
        TODO This function is temporary: Merge with eval_element.
        """
        parent = element
        while parent is not None:
            parent = parent.parent
            predefined_if_name_dict = context.predefined_names.get(parent)
            if predefined_if_name_dict is not None:
                return eval_node(context, element)
        return self._eval_element_cached(context, element)

    @evaluator_function_cache(default=NO_CONTEXTS)
    def _eval_element_cached(self, context, element):
        return eval_node(context, element)

    def goto_definitions(self, context, name):
        def_ = name.get_definition(import_name_always=True)
        if def_ is not None:
            type_ = def_.type
            is_classdef = type_ == 'classdef'
            if is_classdef or type_ == 'funcdef':
                if is_classdef:
                    c = ClassContext(self, context, name.parent)
                else:
                    c = FunctionContext.from_context(context, name.parent)
                return ContextSet([c])

            if type_ == 'expr_stmt':
                is_simple_name = name.parent.type not in ('power', 'trailer')
                if is_simple_name:
                    return eval_expr_stmt(context, def_, name)
            if type_ == 'for_stmt':
                container_types = context.eval_node(def_.children[3])
                cn = ContextualizedNode(context, def_.children[3])
                for_types = iterate_contexts(container_types, cn)
                c_node = ContextualizedName(context, name)
                return check_tuple_assignments(self, c_node, for_types)
            if type_ in ('import_from', 'import_name'):
                return imports.infer_import(context, name)
        else:
            result = self._follow_error_node_imports_if_possible(context, name)
            if result is not None:
                return result

        return helpers.evaluate_call_of_leaf(context, name)

    def _follow_error_node_imports_if_possible(self, context, name):
        error_node = tree.search_ancestor(name, 'error_node')
        if error_node is not None:
            # Get the first command start of a started simple_stmt. The error
            # node is sometimes a small_stmt and sometimes a simple_stmt. Check
            # for ; leaves that start a new statements.
            start_index = 0
            for index, n in enumerate(error_node.children):
                if n.start_pos > name.start_pos:
                    break
                if n == ';':
                    start_index = index + 1
            nodes = error_node.children[start_index:]
            first_name = nodes[0].get_first_leaf().value

            # Make it possible to infer stuff like `import foo.` or
            # `from foo.bar`.
            if first_name in ('from', 'import'):
                is_import_from = first_name == 'from'
                level, names = helpers.parse_dotted_names(
                    nodes,
                    is_import_from=is_import_from,
                    until_node=name,
                )
                return imports.Importer(self, names, context.get_root_context(), level).follow()
        return None

    def goto(self, context, name):
        definition = name.get_definition(import_name_always=True)
        if definition is not None:
            type_ = definition.type
            if type_ == 'expr_stmt':
                # Only take the parent, because if it's more complicated than just
                # a name it's something you can "goto" again.
                is_simple_name = name.parent.type not in ('power', 'trailer')
                if is_simple_name:
                    return [TreeNameDefinition(context, name)]
            elif type_ == 'param':
                return [ParamName(context, name)]
            elif type_ in ('import_from', 'import_name'):
                module_names = imports.infer_import(context, name, is_goto=True)
                return module_names
            else:
                return [TreeNameDefinition(context, name)]
        else:
            contexts = self._follow_error_node_imports_if_possible(context, name)
            if contexts is not None:
                return [context.name for context in contexts]

        par = name.parent
        node_type = par.type
        if node_type == 'argument' and par.children[1] == '=' and par.children[0] == name:
            # Named param goto.
            trailer = par.parent
            if trailer.type == 'arglist':
                trailer = trailer.parent
            if trailer.type != 'classdef':
                if trailer.type == 'decorator':
                    context_set = context.eval_node(trailer.children[1])
                else:
                    i = trailer.parent.children.index(trailer)
                    to_evaluate = trailer.parent.children[:i]
                    if to_evaluate[0] == 'await':
                        to_evaluate.pop(0)
                    context_set = context.eval_node(to_evaluate[0])
                    for trailer in to_evaluate[1:]:
                        context_set = eval_trailer(context, context_set, trailer)
                param_names = []
                for context in context_set:
                    for signature in context.get_signatures():
                        for param_name in signature.get_param_names():
                            if param_name.string_name == name.value:
                                param_names.append(param_name)
                return param_names
        elif node_type == 'dotted_name':  # Is a decorator.
            index = par.children.index(name)
            if index > 0:
                new_dotted = helpers.deep_ast_copy(par)
                new_dotted.children[index - 1:] = []
                values = context.eval_node(new_dotted)
                return unite(
                    value.py__getattribute__(name, name_context=context, is_goto=True)
                    for value in values
                )

        if node_type == 'trailer' and par.children[0] == '.':
            values = helpers.evaluate_call_of_leaf(context, name, cut_own_trailer=True)
            return values.py__getattribute__(name, name_context=context, is_goto=True)
        else:
            stmt = tree.search_ancestor(
                name, 'expr_stmt', 'lambdef'
            ) or name
            if stmt.type == 'lambdef':
                stmt = name
            return context.py__getattribute__(
                name,
                position=stmt.start_pos,
                search_global=True, is_goto=True
            )

    def create_context(self, base_context, node, node_is_context=False, node_is_object=False):
        def parent_scope(node):
            while True:
                node = node.parent

                if parser_utils.is_scope(node):
                    return node
                elif node.type in ('argument', 'testlist_comp'):
                    if node.children[1].type in ('comp_for', 'sync_comp_for'):
                        return node.children[1]
                elif node.type == 'dictorsetmaker':
                    for n in node.children[1:4]:
                        # In dictionaries it can be pretty much anything.
                        if n.type in ('comp_for', 'sync_comp_for'):
                            return n

        def from_scope_node(scope_node, is_nested=True, node_is_object=False):
            if scope_node == base_node:
                return base_context

            is_funcdef = scope_node.type in ('funcdef', 'lambdef')
            parent_scope = parser_utils.get_parent_scope(scope_node)
            parent_context = from_scope_node(parent_scope)

            if is_funcdef:
                func = FunctionContext.from_context(parent_context, scope_node)
                if parent_context.is_class():
                    instance = AnonymousInstance(
                        self, parent_context.parent_context, parent_context)
                    func = BoundMethod(
                        instance=instance,
                        function=func
                    )

                if is_nested and not node_is_object:
                    return func.get_function_execution()
                return func
            elif scope_node.type == 'classdef':
                return ClassContext(self, parent_context, scope_node)
            elif scope_node.type in ('comp_for', 'sync_comp_for'):
                if node.start_pos >= scope_node.children[-1].start_pos:
                    return parent_context
                return CompForContext.from_comp_for(parent_context, scope_node)
            raise Exception("There's a scope that was not managed.")

        base_node = base_context.tree_node

        if node_is_context and parser_utils.is_scope(node):
            scope_node = node
        else:
            scope_node = parent_scope(node)
            if scope_node.type in ('funcdef', 'classdef'):
                colon = scope_node.children[scope_node.children.index(':')]
                if node.start_pos < colon.start_pos:
                    parent = node.parent
                    if not (parent.type == 'param' and parent.name == node):
                        scope_node = parent_scope(scope_node)
        return from_scope_node(scope_node, is_nested=True, node_is_object=node_is_object)

    def parse_and_get_code(self, code=None, path=None, encoding='utf-8',
                           use_latest_grammar=False, file_io=None, **kwargs):
        if self.allow_different_encoding:
            if code is None:
                if file_io is None:
                    file_io = FileIO(path)
                code = file_io.read()
            code = python_bytes_to_unicode(code, encoding=encoding, errors='replace')

        grammar = self.latest_grammar if use_latest_grammar else self.grammar
        return grammar.parse(code=code, path=path, file_io=file_io, **kwargs), code

    def parse(self, *args, **kwargs):
        return self.parse_and_get_code(*args, **kwargs)[0]
