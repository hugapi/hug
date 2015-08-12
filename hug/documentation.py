from collections import OrderedDict

import hug.types


def generate(module, base_url="", api_version=None):
    documentation = OrderedDict()
    overview = module.__doc__
    if overview:
        documentation['overview'] = overview

    documentation['versions'] = OrderedDict()
    versions = module.__hug__.versions
    for version in (api_version, ) if api_version else versions:
        documentation['versions'][version] = OrderedDict()

    for url, methods in module.__hug__.routes.items():
        for method, versions in methods.items():
            for version, handler in versions.items():
                if version == None:
                    applies_to = versions
                else:
                    applies_to = (version, )
                for version in applies_to:
                    if api_version and version != api_version:
                        continue

                    doc = documentation['versions'][version].setdefault(url, OrderedDict())
                    doc = doc.setdefault(method, OrderedDict())

                    usage = handler.api_function.__doc__
                    if usage:
                        doc['usage'] = usage
                    for example in handler.examples:
                        example_text =  "{0}{1}{2}".format(base_url, '/v{0}'.format(version) if version else '', url)
                        if isinstance(example, str):
                            example_text += "?{0}".format(example)
                        doc_examples = doc.setdefault('examples', [])
                        if not example_text in doc_examples:
                            doc_examples.append(example_text)
                    doc['outputs'] = OrderedDict(format=handler.output_format.__doc__,
                                                 content_type=handler.content_type)

                    parameters = [param for param in handler.accepted_parameters if not param in ('request',
                                                                                                  'response')
                                                                                    and not param.startswith('hug_')]
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
