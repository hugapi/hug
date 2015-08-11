from timeit import default_timer as python_timer


class Timer(object):
    '''Keeps track of time surpased since instanciation, outputed by doing float(instance)'''
    __slots__ = ('start', 'round_to')

    def __init__(self, round_to=None, **kwargs):
        self.start = python_timer()
        self.round_to = round_to

    @property
    def elapsed(self):
        return round(self.start, self.round_to) if self.round_to else self.start

    def __float__(self):
        return self.elapsed

    def __int__(self):
        return int(round(self.elapsed))


def module(default=None, module=None, **kwargs):
    '''Returns the module that is running this hug API function'''
    if not module:
        return default

    return module


def api(default=None, module=None, **kwargs):
    '''Returns the api instance in which this API function is being ran'''
    return getattr(module, '__hug__', default)


class CurrentAPI(object):
    '''Returns quick access to all api functions on the current version of the api'''
    __slots__ = ('api_version', 'api')

    def __init__(self, default=None, api_version=None, **kwargs):
        self.api_version = api_version
        self.api = api(**kwargs)

    def __getattr__(self, name):
        function = self.api.versioned.get(self.api_version, {}).get(name, None)
        if function:
            return function

        function = self.api.versioned.get(None, {}).get(name, None)
        if function:
            return function

        raise AttributeError('API Function {0} not found'.format(name))

