import sys
from collections import OrderedDict, namedtuple
from functools import partial

from falcon import HTTP_BAD_REQUEST, HTTP_METHODS

import hug.output_format
from hug.run import server


class HugAPI(object):
    '''Stores the information necessary to expose API calls within this module externally'''
    __slots__ = ('versions', 'routes')

    def __init__(self, versions=()):
        self.versions = set(versions)
        self.routes = OrderedDict()


def call(urls=None, accept=HTTP_METHODS, output=hug.output_format.json, examples=(), versions=None):
    urls = (urls, ) if isinstance(urls, str) else urls
    examples = (examples, ) if isinstance(examples, str) else examples
    versions = (versions, ) if isinstance(versions, (int, float, None.__class__)) else versions

    def decorator(api_function):
        module = sys.modules[api_function.__module__]
        accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount]
        takes_kwargs = bool(api_function.__code__.co_flags & 0x08)

        defaults = {}
        for index, default in enumerate(reversed(api_function.__defaults__ or ())):
            defaults[accepted_parameters[-(index + 1)]] = default
        required = accepted_parameters[:-(len(api_function.__defaults__ or ())) or None]
        use_examples = examples
        if not required and not use_examples:
            use_examples = (True, )

        def interface(request, response, **kwargs):
            response.content_type = output.content_type
            input_parameters = kwargs
            input_parameters.update(request.params)
            errors = {}
            for key, type_handler in api_function.__annotations__.items():
                try:
                    if key in input_parameters:
                        input_parameters[key] = type_handler(input_parameters[key])
                except Exception as error:
                    errors[key] = str(error)

            input_parameters['request'], input_parameters['response'] = (request, response)
            for require in required:
                if not require in input_parameters:
                    errors[require] = "Required parameter not supplied"
            if errors:
                response.data = output({"errors": errors})
                response.status = HTTP_BAD_REQUEST
                return

            if not takes_kwargs:
                input_parameters = {key: value for key, value in input_parameters.items() if key in accepted_parameters}

            response.data = output(api_function(**input_parameters))

        if not '__hug__' in module.__dict__:
            def api_auto_instantiate(*kargs, **kwargs):
                module.__hug_wsgi__ = server(module)
                return module.__hug_wsgi__(*kargs, **kwargs)
            module.__hug__ = HugAPI(versions)
            module.__hug_wsgi__ = api_auto_instantiate
        elif versions:
            module.__hug__.versions.update(versions)

        for url in urls or ("/{0}".format(api_function.__name__), ):
            handlers = module.__hug__.routes.setdefault(url, {})
            for method in accept:
                version_mapping = handlers.setdefault(method.upper(), {})
                for version in versions:
                    version_mapping[version] = interface

        api_function.interface = interface
        interface.api_function = api_function
        interface.output_format = output
        interface.examples = use_examples
        interface.defaults = defaults
        interface.accepted_parameters = accepted_parameters
        interface.content_type = output.content_type
        return api_function
    return decorator


for method in HTTP_METHODS:
    globals()[method.lower()] = partial(call, accept=(method, ))
