import hug
import time

base_error_message = "500 Internal Server Error"
friendly_error_message = "Friendly error message"


class BaseError(Exception):
    code = 500
    message = base_error_message

    def __init__(self):
        ...

    def __str__(self):
        return self.message


class FriendlyError(BaseError):
    message = friendly_error_message


api = hug.API(__name__)


# @hug.exception(UserError, api=api)
def handler_friendly_error(request, response, exception):
    # do something
    response.status = hug.falcon.HTTP_200
    data = dict(data=None, msg=exception.message, timestamp=time.time(), code=exception.code)
    response.body = hug.output_format.json(data)


def test_handler_direct_exception():
    @hug.object.urls("/test", requires=())
    class MyClass(object):
        @hug.object.get()
        def test(self):
            raise FriendlyError()

    api.http.add_exception_handler(FriendlyError, handler_friendly_error)
    assert hug.test.get(api, "/test").data.get("msg", "") == friendly_error_message

    # fix issues: https://github.com/hugapi/hug/issues/911
    api.http.add_exception_handler(BaseError, handler_friendly_error)
    assert hug.test.get(api, "/test").data.get("msg", "") == friendly_error_message


if __name__ == "__main__":
    test_handler_direct_exception()