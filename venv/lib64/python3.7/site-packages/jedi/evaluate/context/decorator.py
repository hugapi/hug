'''
Decorators are not really contexts, however we need some wrappers to improve
docstrings and other things around decorators.
'''

from jedi.evaluate.base_context import ContextWrapper


class Decoratee(ContextWrapper):
    def __init__(self, wrapped_context, original_context):
        self._wrapped_context = wrapped_context
        self._original_context = original_context

    def py__doc__(self):
        return self._original_context.py__doc__()
