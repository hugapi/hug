import bobo


@bobo.query('/text', content_type='text/plain')
def text():
    return 'Hello, world!'


app = bobo.Application(bobo_resources=__name__)
