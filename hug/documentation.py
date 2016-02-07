"""hug/documentation.py

Defines tools that automate the creation of documentation for an API build using the Hug Framework

Copyright (C) 2015  Timothy Edmund Crosley

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

"""
from collections import OrderedDict

import hug.types


def for_handler(handler, version=None, doc=None, base_url="", url=""):
    """Generates documentation for a single API handler function"""
    if doc is None:
        doc = OrderedDict()

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
    if handler.output_type:
        doc['outputs']['type'] = handler.output_type

    parameters = [param for param in handler.accepted_parameters if not param in ('request', 'response', 'self')
                                                                    and not param.startswith('hug_')
                                                                    and not hasattr(param, 'directive')]

    if parameters:
        inputs = doc.setdefault('inputs', OrderedDict())
        types = handler.api_function.__annotations__
        for argument in parameters:
            kind = types.get(argument, hug.types.text)
            input_definition = inputs.setdefault(argument, OrderedDict())
            input_definition['type'] = kind if isinstance(kind, str) else kind.__doc__
            default = handler.defaults.get(argument, None)
            if default is not None:
                input_definition['default'] = default

    return doc


def for_module(module, base_url="", api_version=None, handler_documentation=for_handler):
    """Generates documentation based on a Hug API module, base_url, and api_version (if applicable)"""
    documentation = OrderedDict()
    overview = module.__doc__
    if overview:
        documentation['overview'] = overview

    documentation['versions'] = OrderedDict()
    versions = module.__hug__.versions
    for version in (api_version, ) if api_version else versions:
        documentation['versions'][version] = OrderedDict()

    for url, methods in module.__hug__.routes.items():
        for method, method_versions in methods.items():
            for version, handler in method_versions.items():
                if version == None:
                    applies_to = versions
                else:
                    applies_to = (version, )
                for version in applies_to:
                    if api_version and version != api_version:
                        continue

                    doc = documentation['versions'][version].setdefault(url, OrderedDict())
                    doc[method] = handler_documentation(handler, version, doc=doc.get(method, None), base_url=base_url,
                                                        url=url)

    if len(documentation['versions']) == 1:
        documentation.update(tuple(documentation['versions'].values())[0])
        documentation.pop('versions')
    else:
        documentation['versions'].pop(None, '')

    return documentation
