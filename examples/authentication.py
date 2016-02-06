'''A basic example of authentication requests within a hug API'''
import hug

# Several authenticators are included in hug/authentication.py. These functions
# accept a verify_user function, which can be either an included function (such
# as the basic username/bassword function demonstrated below), or logic of your
# own. Verification functions return an object to store in the request context
# on successful authentication. Naturally, this is a trivial demo, and a much
# more robust verification function is recommended. This is for strictly
# illustrative purposes.
authentication = hug.authentication.basic(hug.authentication.verify('User1', 'mypassword'))


# Note that the logged in user can be accessed via a built-in directive.
# Directives can provide computed input parameters via an abstraction
# layer so as not to clutter your API functions with access to the raw
# request object.
@hug.get('/authenticated', requires=authentication)
def api_call1(user: hug.directives.user):
    return "Successfully authenticated with user: {0}".format(user)


@hug.get('/public')
def api_call2():
    return "Needs no authentication"
