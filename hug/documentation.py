from collections import OrderedDict
import hug.types


def generate(module, base_url=""):
    documentation = OrderedDict()
    overview = module.__doc__
    if overview:
        documentation['overview'] = overview
    for url, method_handler in module.HUG_API_CALLS.items():
        url_doc = documentation.setdefault(url, {})

        mapping = OrderedDict()
        for method, handler in method_handler.items():
            mapping.setdefault(handler, []).append(method.split("_")[-1].upper())

        for handler, methods in mapping.items():
            doc = url_doc.setdefault(",".join(methods), OrderedDict())
            usage = handler.api_function.__doc__
            if usage:
                doc['usage'] = usage
            if handler.example:
                doc['example'] = "{0}{1}".format(base_url, url)
                if isinstance(handler.example, str):
                    doc['example'] += "?{0}".format(handler.example)
            doc['outputs'] = OrderedDict(format=handler.output_format.__doc__)

            if handler.accepted_parameters:
                inputs = doc.setdefault('inputs', OrderedDict())
                types = handler.api_function.__annotations__
                for argument in handler.accepted_parameters:
                    if argument in ('request', 'response'):
                        continue

                    input_definition = inputs.setdefault(argument, OrderedDict())
                    input_definition['type'] = types.get(argument, hug.types.text).__doc__
                    default = handler.defaults.get(argument, None)
                    if default is not None:
                        input_definition['default'] = default

    return documentation

