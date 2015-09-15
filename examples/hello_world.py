import hug


@hug.get()
def hello():
    '''Says hello'''
    return "Hello world!"
