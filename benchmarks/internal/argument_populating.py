import time

from hug.decorators import auto_kwargs
from hug.introspect import generate_accepted_kwargs

DATA = {'request': None}


class Timer(object):

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, *args):
        print("{0} took {1}".format(self.name, time.clock() - self.start))


def my_method(name, request=None):
    pass


def my_method_with_kwargs(name, request=None, **kwargs):
    pass


with Timer('generate_kwargs'):
    accept_kwargs = generate_accepted_kwargs(my_method, ('request', 'response', 'version'))

    for test in range(100000):
        my_method(test, **accept_kwargs(DATA))


with Timer('auto_kwargs'):
    wrapped_method = auto_kwargs(my_method)

    for test in range(100000):
        wrapped_method(test, **DATA)


with Timer('native_kwargs'):
    for test in range(100000):
        my_method_with_kwargs(test, **DATA)


with Timer('no_kwargs'):
    for test in range(100000):
        my_method(test, request=None)
