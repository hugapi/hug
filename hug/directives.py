from timeit import default_timer as python_timer


class Timer(object):
    __slots__ = ('start', 'format')

    def __init__(self, format=None, **kwargs):
        self.start = python_timer()
        self.format = format

    def taken(self):
        return (self.format.format if self.format else float)(python_timer() - self.start)

timer = Timer
