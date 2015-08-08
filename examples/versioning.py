"""A simple example of a hug API call with versioning"""
import hug


@hug.get('/echo', versions=1)
def echo(text):
    return text


@hug.get('/echo', versions=range(2, 5))
def echo(text):
    return "Echo: {text}".format(**locals())