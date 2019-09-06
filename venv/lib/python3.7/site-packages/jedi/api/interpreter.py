"""
TODO Some parts of this module are still not well documented.
"""

from jedi.evaluate.context import ModuleContext
from jedi.evaluate import compiled
from jedi.evaluate.compiled import mixed
from jedi.evaluate.compiled.access import create_access_path
from jedi.evaluate.base_context import ContextWrapper


def _create(evaluator, obj):
    return compiled.create_from_access_path(
        evaluator, create_access_path(evaluator, obj)
    )


class NamespaceObject(object):
    def __init__(self, dct):
        self.__dict__ = dct


class MixedModuleContext(ContextWrapper):
    type = 'mixed_module'

    def __init__(self, evaluator, tree_module, namespaces, file_io, code_lines):
        module_context = ModuleContext(
            evaluator, tree_module,
            file_io=file_io,
            string_names=('__main__',),
            code_lines=code_lines
        )
        super(MixedModuleContext, self).__init__(module_context)
        self._namespace_objects = [NamespaceObject(n) for n in namespaces]

    def get_filters(self, *args, **kwargs):
        for filter in self._wrapped_context.get_filters(*args, **kwargs):
            yield filter

        for namespace_obj in self._namespace_objects:
            compiled_object = _create(self.evaluator, namespace_obj)
            mixed_object = mixed.MixedObject(
                compiled_object=compiled_object,
                tree_context=self._wrapped_context
            )
            for filter in mixed_object.get_filters(*args, **kwargs):
                yield filter
