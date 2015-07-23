import json as json_converter


def json(content):
    return json_converter.dumps(content).encode('utf8')


def text(content):
    return content.encode('utf8')
