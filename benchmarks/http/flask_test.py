import flask

app = flask.Flask(__name__)


@app.route("/text")
def text():
    return "Hello, world!"
