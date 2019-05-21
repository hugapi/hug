"""Provides an example of attaching an action on hug server startup"""
import hug

data = []


@hug.startup()
def add_data(api):
    """Adds initial data to the api on startup"""
    data.append("It's working")


@hug.startup()
def add_more_data(api):
    """Adds initial data to the api on startup"""
    data.append("Even subsequent calls")


@hug.cli()
@hug.get()
def test():
    """Returns all stored data"""
    return data
