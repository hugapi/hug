import os

import hug


DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@hug.get("/get/document", output=hug.output_format.html)
def nagiosCommandHelp(**kwargs):
    """
    Returns command help document when no command is specified
    """
    with open(os.path.join(DIRECTORY, "document.html")) as document:
        return document.read()
