"""
PEP 0484 ( https://www.python.org/dev/peps/pep-0484/ ) describes type hints
through function annotations. There is a strong suggestion in this document
that only the type of type hinting defined in PEP0484 should be allowed
as annotations in future python versions.
"""

import re

from parso import ParserSyntaxError, parse

from jedi._compatibility import force_unicode
from jedi.evaluate.cache import evaluator_method_cache
from jedi.evaluate.base_context import ContextSet, NO_CONTEXTS
from jedi.evaluate.gradual.typing import TypeVar, LazyGenericClass, \
    AbstractAnnotatedClass
from jedi.evaluate.gradual.typing import GenericClass
from jedi.evaluate.helpers import is_string
from jedi.evaluate.compiled import builtin_from_name
from jedi import debug
from jedi import parser_utils


def eval_annotation(context, annotation):
    """
    Evaluates an annotation node. This means that it evaluates the part of
    `int` here:

        foo: int = 3

    Also checks for forward references (strings)
    """
    context_set = context.eval_node(annotation)
    if len(context_set) != 1:
        debug.warning("Eval'ed typing index %s should lead to 1 object, "
                      " not %s" % (annotation, context_set))
        return context_set

    evaled_context = list(context_set)[0]
    if is_string(evaled_context):
        result = _get_forward_reference_node(context, evaled_context.get_safe_value())
        if result is not None:
            return context.eval_node(result)
    return context_set


def _evaluate_annotation_string(context, string, index=None):
    node = _get_forward_reference_node(context, string)
    if node is None:
        return NO_CONTEXTS

    context_set = context.eval_node(node)
    if index is not None:
        context_set = context_set.filter(
            lambda context: context.array_type == u'tuple'  # noqa
                            and len(list(context.py__iter__())) >= index
        ).py__simple_getitem__(index)
    return context_set


def _get_forward_reference_node(context, string):
    try:
        new_node = context.evaluator.grammar.parse(
            force_unicode(string),
            start_symbol='eval_input',
            error_recovery=False
        )
    except ParserSyntaxError:
        debug.warning('Annotation not parsed: %s' % string)
        return None
    else:
        module = context.tree_node.get_root_node()
        parser_utils.move(new_node, module.end_pos[0])
        new_node.parent = context.tree_node
        return new_node


def _split_comment_param_declaration(decl_text):
    """
    Split decl_text on commas, but group generic expressions
    together.

    For example, given "foo, Bar[baz, biz]" we return
    ['foo', 'Bar[baz, biz]'].

    """
    try:
        node = parse(decl_text, error_recovery=False).children[0]
    except ParserSyntaxError:
        debug.warning('Comment annotation is not valid Python: %s' % decl_text)
        return []

    if node.type == 'name':
        return [node.get_code().strip()]

    params = []
    try:
        children = node.children
    except AttributeError:
        return []
    else:
        for child in children:
            if child.type in ['name', 'atom_expr', 'power']:
                params.append(child.get_code().strip())

    return params


@evaluator_method_cache()
def infer_param(execution_context, param):
    contexts = _infer_param(execution_context, param)
    evaluator = execution_context.evaluator
    if param.star_count == 1:
        tuple_ = builtin_from_name(evaluator, 'tuple')
        return ContextSet([GenericClass(
            tuple_,
            generics=(contexts,),
        ) for c in contexts])
    elif param.star_count == 2:
        dct = builtin_from_name(evaluator, 'dict')
        return ContextSet([GenericClass(
            dct,
            generics=(ContextSet([builtin_from_name(evaluator, 'str')]), contexts),
        ) for c in contexts])
        pass
    return contexts


def _infer_param(execution_context, param):
    """
    Infers the type of a function parameter, using type annotations.
    """
    annotation = param.annotation
    if annotation is None:
        # If no Python 3-style annotation, look for a Python 2-style comment
        # annotation.
        # Identify parameters to function in the same sequence as they would
        # appear in a type comment.
        all_params = [child for child in param.parent.children
                      if child.type == 'param']

        node = param.parent.parent
        comment = parser_utils.get_following_comment_same_line(node)
        if comment is None:
            return NO_CONTEXTS

        match = re.match(r"^#\s*type:\s*\(([^#]*)\)\s*->", comment)
        if not match:
            return NO_CONTEXTS
        params_comments = _split_comment_param_declaration(match.group(1))

        # Find the specific param being investigated
        index = all_params.index(param)
        # If the number of parameters doesn't match length of type comment,
        # ignore first parameter (assume it's self).
        if len(params_comments) != len(all_params):
            debug.warning(
                "Comments length != Params length %s %s",
                params_comments, all_params
            )
        from jedi.evaluate.context.instance import InstanceArguments
        if isinstance(execution_context.var_args, InstanceArguments):
            if index == 0:
                # Assume it's self, which is already handled
                return NO_CONTEXTS
            index -= 1
        if index >= len(params_comments):
            return NO_CONTEXTS

        param_comment = params_comments[index]
        return _evaluate_annotation_string(
            execution_context.function_context.get_default_param_context(),
            param_comment
        )
    # Annotations are like default params and resolve in the same way.
    context = execution_context.function_context.get_default_param_context()
    return eval_annotation(context, annotation)


def py__annotations__(funcdef):
    dct = {}
    for function_param in funcdef.get_params():
        param_annotation = function_param.annotation
        if param_annotation is not None:
            dct[function_param.name.value] = param_annotation

    return_annotation = funcdef.annotation
    if return_annotation:
        dct['return'] = return_annotation
    return dct


@evaluator_method_cache()
def infer_return_types(function_execution_context):
    """
    Infers the type of a function's return value,
    according to type annotations.
    """
    all_annotations = py__annotations__(function_execution_context.tree_node)
    annotation = all_annotations.get("return", None)
    if annotation is None:
        # If there is no Python 3-type annotation, look for a Python 2-type annotation
        node = function_execution_context.tree_node
        comment = parser_utils.get_following_comment_same_line(node)
        if comment is None:
            return NO_CONTEXTS

        match = re.match(r"^#\s*type:\s*\([^#]*\)\s*->\s*([^#]*)", comment)
        if not match:
            return NO_CONTEXTS

        return _evaluate_annotation_string(
            function_execution_context.function_context.get_default_param_context(),
            match.group(1).strip()
        ).execute_annotation()
        if annotation is None:
            return NO_CONTEXTS

    context = function_execution_context.function_context.get_default_param_context()
    unknown_type_vars = list(find_unknown_type_vars(context, annotation))
    annotation_contexts = eval_annotation(context, annotation)
    if not unknown_type_vars:
        return annotation_contexts.execute_annotation()

    type_var_dict = infer_type_vars_for_execution(function_execution_context, all_annotations)

    return ContextSet.from_sets(
        ann.define_generics(type_var_dict)
        if isinstance(ann, (AbstractAnnotatedClass, TypeVar)) else ContextSet({ann})
        for ann in annotation_contexts
    ).execute_annotation()


def infer_type_vars_for_execution(execution_context, annotation_dict):
    """
    Some functions use type vars that are not defined by the class, but rather
    only defined in the function. See for example `iter`. In those cases we
    want to:

    1. Search for undefined type vars.
    2. Infer type vars with the execution state we have.
    3. Return the union of all type vars that have been found.
    """
    context = execution_context.function_context.get_default_param_context()

    annotation_variable_results = {}
    executed_params, _ = execution_context.get_executed_params_and_issues()
    for executed_param in executed_params:
        try:
            annotation_node = annotation_dict[executed_param.string_name]
        except KeyError:
            continue

        annotation_variables = find_unknown_type_vars(context, annotation_node)
        if annotation_variables:
            # Infer unknown type var
            annotation_context_set = context.eval_node(annotation_node)
            star_count = executed_param._param_node.star_count
            actual_context_set = executed_param.infer(use_hints=False)
            if star_count == 1:
                actual_context_set = actual_context_set.merge_types_of_iterate()
            elif star_count == 2:
                # TODO _dict_values is not public.
                actual_context_set = actual_context_set.try_merge('_dict_values')
            for ann in annotation_context_set:
                _merge_type_var_dicts(
                    annotation_variable_results,
                    _infer_type_vars(ann, actual_context_set),
                )

    return annotation_variable_results


def _merge_type_var_dicts(base_dict, new_dict):
    for type_var_name, contexts in new_dict.items():
        try:
            base_dict[type_var_name] |= contexts
        except KeyError:
            base_dict[type_var_name] = contexts


def _infer_type_vars(annotation_context, context_set):
    """
    This function tries to find information about undefined type vars and
    returns a dict from type var name to context set.

    This is for example important to understand what `iter([1])` returns.
    According to typeshed, `iter` returns an `Iterator[_T]`:

        def iter(iterable: Iterable[_T]) -> Iterator[_T]: ...

    This functions would generate `int` for `_T` in this case, because it
    unpacks the `Iterable`.
    """
    type_var_dict = {}
    if isinstance(annotation_context, TypeVar):
        return {annotation_context.py__name__(): context_set.py__class__()}
    elif isinstance(annotation_context, LazyGenericClass):
        name = annotation_context.py__name__()
        if name == 'Iterable':
            given = annotation_context.get_generics()
            if given:
                for nested_annotation_context in given[0]:
                    _merge_type_var_dicts(
                        type_var_dict,
                        _infer_type_vars(
                            nested_annotation_context,
                            context_set.merge_types_of_iterate()
                        )
                    )
        elif name == 'Mapping':
            given = annotation_context.get_generics()
            if len(given) == 2:
                for context in context_set:
                    try:
                        method = context.get_mapping_item_contexts
                    except AttributeError:
                        continue
                    key_contexts, value_contexts = method()

                    for nested_annotation_context in given[0]:
                        _merge_type_var_dicts(
                            type_var_dict,
                            _infer_type_vars(
                                nested_annotation_context,
                                key_contexts,
                            )
                        )
                    for nested_annotation_context in given[1]:
                        _merge_type_var_dicts(
                            type_var_dict,
                            _infer_type_vars(
                                nested_annotation_context,
                                value_contexts,
                            )
                        )
    return type_var_dict


def find_type_from_comment_hint_for(context, node, name):
    return _find_type_from_comment_hint(context, node, node.children[1], name)


def find_type_from_comment_hint_with(context, node, name):
    assert len(node.children[1].children) == 3, \
        "Can only be here when children[1] is 'foo() as f'"
    varlist = node.children[1].children[2]
    return _find_type_from_comment_hint(context, node, varlist, name)


def find_type_from_comment_hint_assign(context, node, name):
    return _find_type_from_comment_hint(context, node, node.children[0], name)


def _find_type_from_comment_hint(context, node, varlist, name):
    index = None
    if varlist.type in ("testlist_star_expr", "exprlist", "testlist"):
        # something like "a, b = 1, 2"
        index = 0
        for child in varlist.children:
            if child == name:
                break
            if child.type == "operator":
                continue
            index += 1
        else:
            return []

    comment = parser_utils.get_following_comment_same_line(node)
    if comment is None:
        return []
    match = re.match(r"^#\s*type:\s*([^#]*)", comment)
    if match is None:
        return []
    return _evaluate_annotation_string(
        context, match.group(1).strip(), index
    ).execute_annotation()


def find_unknown_type_vars(context, node):
    def check_node(node):
        if node.type in ('atom_expr', 'power'):
            trailer = node.children[-1]
            if trailer.type == 'trailer' and trailer.children[0] == '[':
                for subscript_node in _unpack_subscriptlist(trailer.children[1]):
                    check_node(subscript_node)
        else:
            type_var_set = context.eval_node(node)
            for type_var in type_var_set:
                if isinstance(type_var, TypeVar) and type_var not in found:
                    found.append(type_var)

    found = []  # We're not using a set, because the order matters.
    check_node(node)
    return found


def _unpack_subscriptlist(subscriptlist):
    if subscriptlist.type == 'subscriptlist':
        for subscript in subscriptlist.children[::2]:
            if subscript.type != 'subscript':
                yield subscript
    else:
        if subscriptlist.type != 'subscript':
            yield subscriptlist
