from collections import OrderedDict

import hug.types


def generate(module, base_url=""):
    documentation = OrderedDict()
    overview = module.__doc__
    if overview:
        documentation['overview'] = overview

    documentation['versions'] = OrderedDict()
    versions = module.HUG_VERSIONS
    for version in versions:
        documentation['versions'][version] = OrderedDict()

    for url, methods in module.HUG_API_CALLS.items():
        for method, versions in methods.items():
            for version, handler in versions.items():
                if version == None:
                    applies_to = versions
                else:
                    applies_to = (version, )
                for version in applies_to:
                    doc = documentation['versions'][version].setdefault(url, OrderedDict()).setdefault(method,
                                                                                                       OrderedDict())
                    usage = handler.api_function.__doc__
                    if usage:
                        doc['usage'] = usage
                    if handler.example:
                        doc['example'] = "{0}{1}".format(base_url, url)
                        if isinstance(handler.example, str):
                            doc['example'] += "?{0}".format(handler.example)
                    doc['outputs'] = OrderedDict(format=handler.output_format.__doc__,
                                                 content_type=handler.content_type)

                    parameters = [param for param in handler.accepted_parameters if not param in ('request',
                                                                                                  'response')]
                    if parameters:
                        inputs = doc.setdefault('inputs', OrderedDict())
                        types = handler.api_function.__annotations__
                        for argument in parameters:
                            input_definition = inputs.setdefault(argument, OrderedDict())
                            input_definition['type'] = types.get(argument, hug.types.text).__doc__
                            default = handler.defaults.get(argument, None)
                            if default is not None:
                                input_definition['default'] = default

    if len(documentation['versions']) == 1:
        documentation.update(tuple(documentation['versions'].values())[0])
        documentation.pop('versions')
    else:
        documentation['versions'].pop(None, '')

    return documentation
