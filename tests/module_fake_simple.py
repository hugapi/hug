"""Simple 1 endpoint Fake HUG API module usable for testing importation of modules"""
import hug


class FakeSimpleException(Exception):
    pass


@hug.get()
def made_up_hello():
    """for science!"""
    return "hello"


@hug.get("/exception")
def made_up_exception():
    raise FakeSimpleException("test")
