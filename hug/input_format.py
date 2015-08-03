import json as json_converter
import re

UNDERSCORE = (re.compile('(.)([A-Z][a-z]+)'), re.compile('([a-z0-9])([A-Z])'))


def json(body):
    return json_converter.loads(body)


def _under_score_dict(dictionary):
    new_dictionary = {}
    for key, value in dictionary.items():
        if isinstance(value, dict):
            value = _under_score_dict(value)
        if isinstance(key, str):
            key = UNDERSCORE[1].sub(r'\1_\2', UNDERSCORE[0].sub(r'\1_\2', key)).lower()
        new_dictionary[key] = value
    return new_dictionary


def json_underscore(body):
    return _under_score_dict(json(body))
