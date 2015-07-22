"""A simple example of a hug API call with versioning"""

@hug.version[1].get('/echo')
def echo(text, **kwargs):
    return text

@hug.version[2:].get('/echo')
def echo(text, **kwargs):
    return "Echo: {text}".format(**locals())
