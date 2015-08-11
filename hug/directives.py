from timeit import default_timer as python_timer


class Timer(object):
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

timer = Timer
