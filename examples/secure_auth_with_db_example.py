from tinydb import TinyDB, Query
import hug
import hashlib
import logging
import os


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
db = TinyDB('db.json')

"""
  Helper Methods
"""


def hash_password(password, salt):
    """
    Securely hash a password using a provided salt
    :param password:
    :param salt:
    :return: Hex encoded SHA512 hash of provided password
    """
    password = str(password).encode('utf-8')
    salt = str(salt).encode('utf-8')
    return hashlib.sha512(password + salt).hexdigest()


def gen_api_key(username):
    """
    Create a random API key for a user
    :param username:
    :return: Hex encoded SHA512 random string
    """
    salt = str(os.urandom(64)).encode('utf-8')
    return hash_password(username, salt)


@hug.cli()
def authenticate_user(username, password):
    """
    Authenticate a username and password against our database
    :param username:
    :param password:
    :return: authenticated username
    """
    user_model = Query()
    user = db.search(user_model.username == username)

    if not user:
        logger.warning("User %s not found", username)
        return False

    if user[0]['password'] == hash_password(password, user[0].get('salt')):
        return user[0]['username']

    return False


@hug.cli()
def authenticate_key(api_key):
    """
    Authenticate an API key against our database
    :param api_key:
    :return: authenticated username
    """
    user_model = Query()
    user = db.search(user_model.api_key == api_key)
    if user:
        return user[0]['username']
    return False

"""
  API Methods start here
"""

api_key_authentication = hug.authentication.api_key(authenticate_key)
basic_authentication = hug.authentication.basic(authenticate_user)


@hug.cli()
def add_user(username, password):
    """
    CLI Parameter to add a user to the database
    :param username:
    :param password:
    :return: JSON status output
    """

    user_model = Query()
    if db.search(user_model.username == username):
        return {
            'error': 'User {0} already exists'.format(username)
        }

    salt = hashlib.sha512(str(os.urandom(64)).encode('utf-8')).hexdigest()
    password = hash_password(password, salt)
    api_key = gen_api_key(username)

    user = {
        'username': username,
        'password': password,
        'salt': salt,
        'api_key': api_key
    }
    user_id = db.insert(user)

    return {
       'result': 'success',
       'eid': user_id,
       'user_created': user
    }


@hug.get('/api/get_api_key', requires=basic_authentication)
def get_token(authed_user: hug.directives.user):
    """
    Get Job details
    :param authed_user:
    :return:
    """
    user_model = Query()
    user = db.search(user_model.username == authed_user)

    if user:
        out = {
            'user': user['username'],
            'api_key': user['api_key']
        }
    else:
        # this should never happen
        out = {
            'error': 'User {0} does not exist'.format(authed_user)
        }

    return out


# Same thing, but authenticating against an API key
@hug.get(('/api/job', '/api/job/{job_id}/'), requires=api_key_authentication)
def get_job_details(job_id):
    """
    Get Job details
    :param job_id:
    :return:
    """
    job = {
        'job_id': job_id,
        'details': 'Details go here'
    }

    return job


if __name__ == '__main__':
    add_user.interface.cli()
