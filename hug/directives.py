from timeit import default_timer as timer


class Timer(object):
    __slots__ = ('start', 'format')

    def __init__(self, format=None, **kwargs):
        self.start = timer()
        self.format = format

    def taken(self):
        return (self.format.format or float)(timer() - self.start)

timer = Timer


