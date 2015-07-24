from collections import OrderedDict
import hug.types


def generate(module, base_url=""):
    documentation = OrderedDict()
    documentation['overview'] = module.__doc__
    for url, method_handler in module.HUG_API_CALLS.items():
        url_doc = documentation.setdefault(url, {})

        mapping = OrderedDict()
        for method, handler in method_handler.items():
            mapping.setdefault(handler, []).append(method.split("_")[-1].upper())

        for handler, methods in mapping.items():
            doc = url_doc.setdefault(",".join(methods), OrderedDict())
            doc['usage'] = handler.api_function.__doc__
            if handler.example:
                doc['example'] = "{0}{1}".format(base_url, url)
                if isinstance(handler.example, str):
                    doc['example'] += "?{0}".format(handler.example)
            inputs = doc.setdefault('inputs', OrderedDict())
            doc['outputs'] = OrderedDict(format=handler.output_format.__doc__)

            api = handler.api_function
            types = api.__annotations__
            arguments = api.__code__.co_varnames[:api.__code__.co_argcount]

            defaults = {}
            for index, default in enumerate(api.__defaults__ or ()):
                defaults[arguments[-(index + 1)]] = default

            for argument in arguments:
                if argument in ('request', 'response'):
                    continue

                input_definition = inputs.setdefault(argument, OrderedDict())
                input_definition['type'] = types.get(argument, hug.types.text).__doc__
                default = defaults.get(argument, None)
                if default is not None:
                    input_definition['default'] = default

    return documentation

