from falcon import HTTP_206
import hug


def change_status(content, response):
    response.status = HTTP_206
    return content


@hug.get(transform=change_status)
def hello():
    '''Says hello'''
    raise ValueError('hiii')


