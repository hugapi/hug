import sys
from collections import OrderedDict, namedtuple
from functools import partial

from falcon import HTTP_BAD_REQUEST, HTTP_METHODS

import hug.output_format
from hug.run import server


class Versioning(object):
    METHODS  = tuple(method.lower() for method in HTTP_METHODS + ('call', ))

    def __getitem__(self, value):
        versions = None
        if isinstance(value, int):
            versionss = (int)
        elif isinstance(value, slice) and not (value.start is None and value.stop is None and value.step is None):
            versions = []
            if value.step:
                raise ValueError('Step values are not supported for defining versionss')
            if value.start and value.stop and value.start > value.stop:
                raise ValueError('Reverse indexes are not supported for defining versionss')

            if value.start:
                versions.append(value.start)

            if value.start and value.stop:
                versions.extend(range(value.start, value.stop))
            elif value.stop and value.start is None:
                versions.extend(range(1, value.stop))
            elif value.start and value.stop is None:
                versions.extend((value.start, float('inf')))

        return namedtuple('Router', self.METHODS)(**{name: partial(globals()[name.lower()], versions=versions)
                                                  for name in self.METHODS})
version = Versioning()


def call(urls=None, accept=HTTP_METHODS, output=hug.output_format.json, example=None, versions=None):
    if isinstance(urls, str):
        urls = (urls, )
    if not isinstance(version, (list, tuple)):
        versions = (versions, )

    def decorator(api_function):
        module = sys.modules[api_function.__module__]
        accepted_parameters = api_function.__code__.co_varnames[:api_function.__code__.co_argcount]
        takes_kwargs = bool(api_function.__code__.co_flags & 0x08)

        defaults = {}
        for index, default in enumerate(reversed(api_function.__defaults__ or ())):
            defaults[accepted_parameters[-(index + 1)]] = default
        required = accepted_parameters[:-(len(api_function.__defaults__ or ())) or None]
        use_example = example
        if not required and example is None:
            use_example = True

        def interface(request, response):
            response.content_type = output.content_type
            input_parameters = request.params
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

        if not 'HUG' in module.__dict__:
            def api_auto_instantiate(*kargs, **kwargs):
                module.HUG = server(module)
                return module.HUG(*kargs, **kwargs)
            module.HUG = api_auto_instantiate
            module.HUG_API_CALLS = OrderedDict()
            module.HUG_VERSIONS = []
        if versions:
            module.HUG_VERSIONS.extend(versions)

        for url in urls or ("/{0}".format(api_function.__name__), ):
            version_routes = module.HUG_API_CALLS.setdefault(url, {})
            method_routes = {"on_{0}".format(method.lower()): interface for method in accept}
            for version in versions:
                version_routes.setdefault(version, {}).update(method_routes)
            if float("inf") in versions:
                start = versions[0]
                for version_number in version_routes.keys():
                    if isinstance(version_number, (float, int)) and version_number > start:
                        version_routes.setdefault(version_number, {}).update(method_routes)

        api_function.interface = interface
        interface.api_function = api_function
        interface.output_format = output
        interface.example = use_example
        interface.defaults = defaults
        interface.accepted_parameters = accepted_parameters
        interface.content_type = output.content_type
        return api_function
    return decorator


for method in HTTP_METHODS:
    globals()[method.lower()] = partial(call, accept=(method, ))
