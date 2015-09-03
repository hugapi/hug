import example_resource
import hug


@hug.get()
def hello():
    return example_resource.hi()
