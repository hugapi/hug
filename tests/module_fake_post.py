"""Fake HUG API module usable for testing importation of modules"""
import hug


@hug.post()
def made_up_hello():
    """POSTing for science!"""
    return 'hello from POST'
