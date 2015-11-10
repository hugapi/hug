'''A simple post reading server example.

To test run this server with `hug -f post_body_example`
then run the following from ipython:
    import requests

    requests.post('http://localhost:8000/post_here', json={'one': 'two'}).json()

    This should return back the json data that you posted
'''
import hug


@hug.post()
def post_here(body):
    '''This example shows how to read in post data w/ hug outside of its automatic param parsing'''
    return body
