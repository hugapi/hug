'''A basic example of authentication requests within a hug API'''
import hug

authentication = hug.authentication.basic(hug.authentication.verify('User1', 'mypassword'))


@hug.get(requires=authentication)
def api_call1():
    return "Passed Authentication"


@hug.get()
def api_call2():
    return "Needs no authentication"
