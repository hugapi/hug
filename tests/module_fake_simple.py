"""Simple 1 endpoint Fake HUG API module usable for testing importation of modules"""
import hug


@hug.get()
def made_up_hello():
    """for science!"""
    return 'hello'
