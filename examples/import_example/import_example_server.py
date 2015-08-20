import hug

import example_resource


@hug.get()
def hello():
    return example_resource.hi()