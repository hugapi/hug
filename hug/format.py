def content_type(content_type):
    '''Attaches an explicit HTML content type to a Hug formatting function'''
    def decorator(method):
        method.content_type = content_type
        return method
    return decorator
