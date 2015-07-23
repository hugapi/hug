import json as json_converter


def json(content):
    return json_converter.dumps(content).encode('utf8')


def text(content):
    return content.encode('utf8')


def _camelcase(dictionary):
    if not isinstance(dictionary, dict):
        return dictionary

    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(key, str):
            key = key[0] + "".join(key.title().split('_'))[1:]
        new_dictionary[key] = _camelcase(dictionary)


def json_camelcase(content):
    return _camelcase(json(body))
