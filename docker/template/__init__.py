import hug

from handlers import hello
from handlers import birthday


@hug.extend_api('')
def api():
    return [hello, birthday]
