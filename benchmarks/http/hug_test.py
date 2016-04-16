import hug


@hug.get('/text', output_format=hug.output_format.text, parse_body=False)
def text():
    return 'Hello, World!'


app = __hug_wsgi__
