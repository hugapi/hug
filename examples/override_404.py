import hug


@hug.get()
def hello_world():
    return 'Hello world!'


@hug.not_found()
def not_found():
    return {'Nothing': 'to see'}
