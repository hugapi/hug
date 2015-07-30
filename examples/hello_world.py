import hug


@hug.get()
def hello_world():
    return "Hello world"
