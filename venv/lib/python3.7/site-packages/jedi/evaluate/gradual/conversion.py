from jedi import debug
from jedi.evaluate.base_context import ContextSet, \
    NO_CONTEXTS
from jedi.evaluate.utils import to_list
from jedi.evaluate.gradual.stub_context import StubModuleContext


def _stub_to_python_context_set(stub_context, ignore_compiled=False):
    stub_module = stub_context.get_root_context()
    if not stub_module.is_stub():
        return ContextSet([stub_context])

    was_instance = stub_context.is_instance()
    if was_instance:
        stub_context = stub_context.py__class__()

    qualified_names = stub_context.get_qualified_names()
    if qualified_names is None:
        return NO_CONTEXTS

    was_bound_method = stub_context.is_bound_method()
    if was_bound_method:
        # Infer the object first. We can infer the method later.
        method_name = qualified_names[-1]
        qualified_names = qualified_names[:-1]
        was_instance = True

    contexts = _infer_from_stub(stub_module, qualified_names, ignore_compiled)
    if was_instance:
        contexts = ContextSet.from_sets(
            c.execute_evaluated()
            for c in contexts
            if c.is_class()
        )
    if was_bound_method:
        # Now that the instance has been properly created, we can simply get
        # the method.
        contexts = contexts.py__getattribute__(method_name)
    return contexts


def _infer_from_stub(stub_module, qualified_names, ignore_compiled):
    from jedi.evaluate.compiled.mixed import MixedObject
    assert isinstance(stub_module, (StubModuleContext, MixedObject)), stub_module
    non_stubs = stub_module.non_stub_context_set
    if ignore_compiled:
        non_stubs = non_stubs.filter(lambda c: not c.is_compiled())
    for name in qualified_names:
        non_stubs = non_stubs.py__getattribute__(name)
    return non_stubs


@to_list
def _try_stub_to_python_names(names, prefer_stub_to_compiled=False):
    for name in names:
        module = name.get_root_context()
        if not module.is_stub():
            yield name
            continue

        name_list = name.get_qualified_names()
        if name_list is None:
            contexts = NO_CONTEXTS
        else:
            contexts = _infer_from_stub(
                module,
                name_list[:-1],
                ignore_compiled=prefer_stub_to_compiled,
            )
        if contexts and name_list:
            new_names = contexts.py__getattribute__(name_list[-1], is_goto=True)
            for new_name in new_names:
                yield new_name
            if new_names:
                continue
        elif contexts:
            for c in contexts:
                yield c.name
            continue
        # This is the part where if we haven't found anything, just return the
        # stub name.
        yield name


def _load_stub_module(module):
    if module.is_stub():
        return module
    from jedi.evaluate.gradual.typeshed import _try_to_load_stub_cached
    return _try_to_load_stub_cached(
        module.evaluator,
        import_names=module.string_names,
        python_context_set=ContextSet([module]),
        parent_module_context=None,
        sys_path=module.evaluator.get_sys_path(),
    )


@to_list
def _python_to_stub_names(names, fallback_to_python=False):
    for name in names:
        module = name.get_root_context()
        if module.is_stub():
            yield name
            continue

        if name.is_import():
            for new_name in name.goto():
                # Imports don't need to be converted, because they are already
                # stubs if possible.
                if fallback_to_python or new_name.is_stub():
                    yield new_name
            continue

        name_list = name.get_qualified_names()
        stubs = NO_CONTEXTS
        if name_list is not None:
            stub_module = _load_stub_module(module)
            if stub_module is not None:
                stubs = ContextSet({stub_module})
                for name in name_list[:-1]:
                    stubs = stubs.py__getattribute__(name)
        if stubs and name_list:
            new_names = stubs.py__getattribute__(name_list[-1], is_goto=True)
            for new_name in new_names:
                yield new_name
            if new_names:
                continue
        elif stubs:
            for c in stubs:
                yield c.name
            continue
        if fallback_to_python:
            # This is the part where if we haven't found anything, just return
            # the stub name.
            yield name


def convert_names(names, only_stubs=False, prefer_stubs=False):
    assert not (only_stubs and prefer_stubs)
    with debug.increase_indent_cm('convert names'):
        if only_stubs or prefer_stubs:
            return _python_to_stub_names(names, fallback_to_python=prefer_stubs)
        else:
            return _try_stub_to_python_names(names, prefer_stub_to_compiled=True)


def convert_contexts(contexts, only_stubs=False, prefer_stubs=False, ignore_compiled=True):
    assert not (only_stubs and prefer_stubs)
    with debug.increase_indent_cm('convert contexts'):
        if only_stubs or prefer_stubs:
            return ContextSet.from_sets(
                to_stub(context)
                or (ContextSet({context}) if prefer_stubs else NO_CONTEXTS)
                for context in contexts
            )
        else:
            return ContextSet.from_sets(
                _stub_to_python_context_set(stub_context, ignore_compiled=ignore_compiled)
                or ContextSet({stub_context})
                for stub_context in contexts
            )


# TODO merge with _python_to_stub_names?
def to_stub(context):
    if context.is_stub():
        return ContextSet([context])

    was_instance = context.is_instance()
    if was_instance:
        context = context.py__class__()

    qualified_names = context.get_qualified_names()
    stub_module = _load_stub_module(context.get_root_context())
    if stub_module is None or qualified_names is None:
        return NO_CONTEXTS

    was_bound_method = context.is_bound_method()
    if was_bound_method:
        # Infer the object first. We can infer the method later.
        method_name = qualified_names[-1]
        qualified_names = qualified_names[:-1]
        was_instance = True

    stub_contexts = ContextSet([stub_module])
    for name in qualified_names:
        stub_contexts = stub_contexts.py__getattribute__(name)

    if was_instance:
        stub_contexts = ContextSet.from_sets(
            c.execute_evaluated()
            for c in stub_contexts
            if c.is_class()
        )
    if was_bound_method:
        # Now that the instance has been properly created, we can simply get
        # the method.
        stub_contexts = stub_contexts.py__getattribute__(method_name)
    return stub_contexts
