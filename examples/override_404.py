import hug


@hug.get()
def hello_world():
    return "Hello world!"


@hug.NotFoundRouter()
def not_found():
    return {"Nothing": "to see"}
