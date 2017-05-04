"""A simple file upload example.

To test, run this server with `hug -f file_upload_example.py`

Then run the following from ipython
(you may want to replace .wgetrc with some other small text file that you have,
and it's better to specify absolute path to it):

    import requests
    with open('.wgetrc', 'rb') as wgetrc_handle:
        response = requests.post('http://localhost:8000/upload', files={'.wgetrc': wgetrc_handle})
    print(response.headers)
    print(response.content)

This should both print in the terminal and return back the filename and filesize of the uploaded file.
"""

import hug

@hug.post('/upload')
def upload_file(body):
    """accepts file uploads"""
    # <body> is a simple dictionary of {filename: b'content'}
    print('body: ', body)
    return {'filename': list(body.keys()).pop(), 'filesize': len(list(body.values()).pop())}
