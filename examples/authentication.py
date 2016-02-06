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

@hug.get('/public')
def public_api_call():
    return "Needs no authentication"

# Note that the logged in user can be accessed via a built-in directive.
# Directives can provide computed input parameters via an abstraction
# layer so as not to clutter your API functions with access to the raw
# request object.
@hug.get('/authenticated', requires=authentication)
def basic_auth_api_call(user: hug.directives.user):
    return 'Successfully authenticated with user: {0}'.format(user)


# Here is a slightly less trivial example of how authentication might
# look in an API that uses keys.

# First, the user object stored in the context need not be a string,
# but can be any Python object.
class APIUser(object):
    """A minimal example of a rich User object"""
    def __init__(self, user_id, api_key):
        self.user_id = user_id
        self.api_key = api_key

def api_key_verify(api_key):
    magic_key = '5F00832B-DE24-4CAF-9638-C10D1C642C6C' # Obviously, this would hit your database
    if api_key == magic_key:
        # Success!
        return APIUser('user_foo', api_key)
    else:
        # Invalid key
        return None

api_key_authentication = hug.authentication.api_key(api_key_verify)

@hug.get('/key_authenticated', requires=api_key_authentication)
def basic_auth_api_call(user: hug.directives.user):
    return 'Successfully authenticated with user: {0}'.format(user.user_id)
