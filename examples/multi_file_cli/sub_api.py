import hug


@hug.CLIRouter()
def hello():
    return "Hello world"
