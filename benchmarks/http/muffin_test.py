import muffin

app = muffin.Application('web')


@app.register('/text')
def text(request):
    return 'Hello, World!'
