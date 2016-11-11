import hug
import sys


@hug.get()
def quick():
    return 'Serving!'


if __name__ == '__main__':
    hug.API(sys.modules[__name__]).http.serve()
