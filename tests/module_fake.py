"""Fake HUG API module usable for testing importation of modules"""
import hug


class FakeException(BaseException):
    pass


@hug.directive(apply_globally=False)
def my_directive(default=None, **kwargs):
    """for testing"""
    return default


@hug.default_input_format('application/made-up')
def made_up_formatter(data):
    """for testing"""
    return data


@hug.default_output_format()
def output_formatter(data):
    """for testing"""
    return hug.output_format.json(data)


@hug.get()
def made_up_api(hug_my_directive=True):
    """for testing"""
    return hug_my_directive


@hug.directive(apply_globally=True)
def my_directive_global(default=None, **kwargs):
    """for testing"""
    return default


@hug.default_input_format('application/made-up', apply_globally=True)
def made_up_formatter_global(data):
    """for testing"""
    return data


@hug.default_output_format(apply_globally=True)
def output_formatter_global(data):
    """for testing"""
    return hug.output_format.json(data)


@hug.request_middleware()
def handle_request(request, response):
    """for testing"""
    return


@hug.startup()
def on_startup(api):
    """for testing"""
    return

@hug.static()
def static():
    """for testing"""
    return ('', )


@hug.exception(FakeException)
def handle_exception(exception):
    """Handles the provided exception for testing"""
    return True
