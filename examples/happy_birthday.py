"""A basic (single function) API written using Hug"""
import hug


@hug.get('/happy_birthday', examples="name=HUG&age=1")
def happy_birthday(name, age: hug.types.number):
    """Says happy birthday to a user"""
    return "Happy {age} Birthday {name}!".format(**locals())

@hug.get('/greet/{event}')
def greet(event: str):
    """Greets appropriately (from http://blog.ketchum.com/how-to-write-10-common-holiday-greetings/)  """
    greetings = "Happy"
    if event == "Christmas":
        greetings = "Merry"
    if event == "Kwanzaa":
        greetings = "Joyous"
    if event == "wishes":
        greetings = "Warm"

    return "{greetings} {event}!".format(**locals())
