'''A basic example of authentication requests within a hug API'''
import hug
import jwt

# Several authenticators are included in hug/authentication.py. These functions
# accept a verify_user function, which can be either an included function (such
# as the basic username/password function demonstrated below), or logic of your
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
    magic_key = '5F00832B-DE24-4CAF-9638-C10D1C642C6C'  # Obviously, this would hit your database
    if api_key == magic_key:
        # Success!
        return APIUser('user_foo', api_key)
    else:
        # Invalid key
        return None


api_key_authentication = hug.authentication.api_key(api_key_verify)


@hug.get('/key_authenticated', requires=api_key_authentication)  # noqa
def basic_auth_api_call(user: hug.directives.user):
    return 'Successfully authenticated with user: {0}'.format(user.user_id)


def token_verify(token):
    secret_key = 'super-secret-key-please-change'
    try:
        return jwt.decode(token, secret_key, algorithm='HS256')
    except jwt.DecodeError:
        return False


token_key_authentication = hug.authentication.token(token_verify)


@hug.get('/token_authenticated', requires=token_key_authentication)  # noqa
def token_auth_call(user: hug.directives.user):
    return 'You are user: {0} with data {1}'.format(user['user'], user['data'])


@hug.post('/token_generation')  # noqa
def token_gen_call(username, password):
    """Authenticate and return a token"""
    secret_key = 'super-secret-key-please-change'
    mockusername = 'User2'
    mockpassword = 'Mypassword'
    if mockpassword == password and mockusername == username: # This is an example. Don't do that.
        return {"token" : jwt.encode({'user': username, 'data': 'mydata'}, secret_key, algorithm='HS256')}
    return 'Invalid username and/or password for user: {0}'.format(username)

# JWT AUTH EXAMPLE #
replace_this = False
config = {
    'jwt_secret': 'super-secret-key-please-change',
    # token will expire in 3600 seconds if it is not refreshed and the user will be required to log in again
    'token_expiration_seconds': 3600,
    # if a request is made at a time less than 1000 seconds before expiry, a new jwt is sent in the response header
    'token_refresh_seconds': 1000 
}
# enable authenticated endpoints, example @authenticated.get('/users/me')
authenticated = hug.http(requires=hug.authentication.json_web_token(hug.authentication.verify_jwt, config['jwt_secret']))

# check the token and issue a new one if it is about to expire (within token_refresh_seconds from expiry)
@hug.response_middleware()
def refresh_jwt(request, response, resource):
    authorization = request.get_header('Authorization')
    if authorization:
        token = hug.authentication.refresh_jwt(authorization, config['token_refresh_seconds'], 
            config['token_expiration_seconds'], config['jwt_secret'])
        if token:
            response.set_header('token', token)

@hug.post('/login')
def login(request, response,
          email: fields.Email(),
          password: fields.String()
         ):
    response.status = falcon.HTTP_400

    user = replace_this # store.get_user_by_email(email)
    if not user:
        return {'errors': {'Issue': "User not found."}}
    elif 'password_hash' in user:
        if replace_this: # if bcrypt.checkpw(password.encode('utf8'), user.password_hash):
            response.status = falcon.HTTP_201
            token = hug.authentication.new_jwt(
                        str(user['_id']), 
                        config['token_expiration_seconds'], 
                        config['jwt_secret'])
            response.set_header('token', token)
        else:
            return {'errors': {'Issue': "Password hash mismatch."}}
    else:
        return {'errors': {'Issue': "Please check your email to complete registration."}}
# END - JWT AUTH EXAMPLE #
