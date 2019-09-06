import bottle

app = bottle.Bottle()


@app.route("/text")
def text():
    return "Hello, world!"
