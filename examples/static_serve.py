"""Serves a directory from the filesystem using Hug.

try /static/a/hi.txt  /static/a/hi.html  /static/a/hello.html
"""
import tempfile
import os

import hug

tmp_dir_object = None

def setup(api=None):
    """Sets up and fills test directory for serving.

    Using different filetypes to see how they are dealt with.
    The tempoary directory will clean itself up.
    """
    global tmp_dir_object

    tmp_dir_object = tempfile.TemporaryDirectory()

    dir_name = tmp_dir_object.name

    dir_a = os.path.join(dir_name, "a")
    os.mkdir(dir_a)
    dir_b = os.path.join(dir_name, "b")
    os.mkdir(dir_b)

    # populate directory a with text files
    file_list = [
            ["hi.txt", """Hi World!"""],
            ["hi.html", """<strong>Hi World!</strong>"""],
            ["hello.html", """
                <img src='/static/b/smile.png'</img>
                pop-up
                <script src='/static/a/hi.js'></script>"""],
            ["hi.js", """alert('Hi World')""" ]
    ]

    for f in file_list:
        with open(os.path.join(dir_a, f[0]), mode="wt") as fo:
            fo.write(f[1])

    # populate directory b with binary file
    image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\n\x00\x00\x00\n\x08\x02\x00\x00\x00\x02PX\xea\x00\x00\x006IDAT\x18\xd3c\xfc\xff\xff?\x03n\xc0\xc4\x80\x170100022222\xc2\x85\x90\xb9\x04t3\x92`7\xb2\x15D\xeb\xc6\xe34\xa8n4c\xe1F\x120\x1c\x00\xc6z\x12\x1c\x8cT\xf2\x1e\x00\x00\x00\x00IEND\xaeB`\x82'

    with open(os.path.join(dir_b, "smile.png"), mode="wb") as fo:
            fo.write(image)


@hug.static('/static')
def my_static_dirs():
    """Returns static directory names to be served."""
    global tmp_dir_object
    if tmp_dir_object == None:
        setup()
    return(tmp_dir_object.name,)
