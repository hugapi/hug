class BaseContext(object):
    def __init__(self, evaluator, parent_context=None):
        self.evaluator = evaluator
        self.parent_context = parent_context

    def get_root_context(self):
        context = self
        while True:
            if context.parent_context is None:
                return context
            context = context.parent_context


class BaseContextSet(object):
    def __init__(self, iterable):
        self._set = frozenset(iterable)
        for context in iterable:
            assert not isinstance(context, BaseContextSet)

    @classmethod
    def _from_frozen_set(cls, frozenset_):
        self = cls.__new__(cls)
        self._set = frozenset_
        return self

    @classmethod
    def from_sets(cls, sets):
        """
        Used to work with an iterable of set.
        """
        aggregated = set()
        for set_ in sets:
            if isinstance(set_, BaseContextSet):
                aggregated |= set_._set
            else:
                aggregated |= frozenset(set_)
        return cls._from_frozen_set(frozenset(aggregated))

    def __or__(self, other):
        return self._from_frozen_set(self._set | other._set)

    def __and__(self, other):
        return self._from_frozen_set(self._set & other._set)

    def __iter__(self):
        for element in self._set:
            yield element

    def __bool__(self):
        return bool(self._set)

    def __len__(self):
        return len(self._set)

    def __repr__(self):
        return 'S{%s}' % (', '.join(str(s) for s in self._set))

    def filter(self, filter_func):
        return self.__class__(filter(filter_func, self._set))

    def __getattr__(self, name):
        def mapper(*args, **kwargs):
            return self.from_sets(
                getattr(context, name)(*args, **kwargs)
                for context in self._set
            )
        return mapper

    def __eq__(self, other):
        return self._set == other._set

    def __hash__(self):
        return hash(self._set)
