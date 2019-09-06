import hug


@hug.cli()
def hello():
    return "Hello world"
