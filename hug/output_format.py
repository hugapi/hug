import json as json_converter
from datetime import date, datetime


def _json_converter(item):
    if isinstance(item, datetime):
        return item.isoformat()
    elif isinstance(item, bytes):
        return item.decode('utf8')
    raise TypeError("Type not serializable")


def json(content, **kwargs):
    """JSON (Javascript Serialized Object Notation)"""
    return json_converter.dumps(content, default=_json_converter, **kwargs).encode('utf8')


def text(content):
    """Free form UTF8 text"""
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
    """JSON (Javascript Serialized Object Notation) with all keys camelCased"""
    return _camelcase(json(body))


def pretty_json(content):
    """JSON (Javascript Serialized Object Notion) pretty printed and indented"""
    return json(content, indent=4, separators=(',', ': '))
