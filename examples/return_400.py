import hug
from falcon import HTTP_400

@hug.get()
def only_positive(positive: int, response):
    if positive < 0:
        response.status = HTTP_400