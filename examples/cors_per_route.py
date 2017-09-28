import hug


@hug.get()
def cors_supported(cors: hug.directives.cors="*"):
    return "Hello world!"
