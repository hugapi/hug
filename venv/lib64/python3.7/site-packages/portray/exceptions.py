"""All portray specific exception classes should be defined here"""


class PortrayError(Exception):
    """Base class for all exceptions returned from portray"""

    pass


class NoProjectFound(PortrayError):
    """Thrown when portray is ran in a directory with no Python project"""

    def __init__(self, directory: str):
        super().__init__(
            self,
            f"No Python project found in the given directory: '{directory}'"
            + " See: https://timothycrosley.github.io/portray/TROUBLESHOOTING/#noprojectfound",
        )
        self.directory = directory


class DocumentationAlreadyExists(PortrayError):
    """Thrown when portray has been told to output documentation where it already exists"""

    def __init__(self, directory: str):
        super().__init__(
            self, f"Documentation already exists in '{directory}'. Use --overwrite to ignore"
        )
        self.directory = directory
