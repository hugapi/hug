import hug


@hug.get()
def hello(request):
    """Says hello"""
    import pdb; pdb.set_trace()
    return 'Hello World!'
