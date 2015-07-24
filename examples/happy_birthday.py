"""A basic (single function) API written using Hug"""
import hug


@hug.get('/happy_birthday', example="name=HUG&age=1")
def happy_birthday(name, age:hug.types.number, **kwargs):
    """Says happy birthday to a user"""
    return "Happy {age} Birthday {name}!".format(**locals())
