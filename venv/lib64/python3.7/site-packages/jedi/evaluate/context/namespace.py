from jedi.evaluate.cache import evaluator_method_cache
from jedi.evaluate.filters import DictFilter
from jedi.evaluate.names import ContextNameMixin, AbstractNameDefinition
from jedi.evaluate.base_context import Context
from jedi.evaluate.context.module import SubModuleDictMixin


class ImplicitNSName(ContextNameMixin, AbstractNameDefinition):
    """
    Accessing names for implicit namespace packages should infer to nothing.
    This object will prevent Jedi from raising exceptions
    """
    def __init__(self, implicit_ns_context, string_name):
        self._context = implicit_ns_context
        self.string_name = string_name


class ImplicitNamespaceContext(Context, SubModuleDictMixin):
    """
    Provides support for implicit namespace packages
    """
    # Is a module like every other module, because if you import an empty
    # folder foobar it will be available as an object:
    # <module 'foobar' (namespace)>.
    api_type = u'module'
    parent_context = None

    def __init__(self, evaluator, fullname, paths):
        super(ImplicitNamespaceContext, self).__init__(evaluator, parent_context=None)
        self.evaluator = evaluator
        self._fullname = fullname
        self._paths = paths

    def get_filters(self, search_global=False, until_position=None, origin_scope=None):
        yield DictFilter(self.sub_modules_dict())

    @property
    @evaluator_method_cache()
    def name(self):
        string_name = self.py__package__()[-1]
        return ImplicitNSName(self, string_name)

    def py__file__(self):
        return None

    def py__package__(self):
        """Return the fullname
        """
        return self._fullname.split('.')

    def py__path__(self):
        return self._paths

    def py__name__(self):
        return self._fullname

    def is_namespace(self):
        return True

    def is_stub(self):
        return False

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self._fullname)
