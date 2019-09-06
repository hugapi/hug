import hug
from handlers import birthday, hello


@hug.extend_api("")
def api():
    return [hello, birthday]
