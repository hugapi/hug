'''A basic example of authentication requests within a hug API'''
import hug

authenticates = hug.authentication.basic(hug.authentication.verify('User1', 'mypassword'))


@hug.get(only_if=authenticates)
def api_call1():
    return "Passed Authentication"


@hug.get()
def api_call2():
    return "Needs no authentication"
