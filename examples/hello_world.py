import hug


@hug.get()
def hello(request):
    """Says hello"""
    return 'Hello World! '
