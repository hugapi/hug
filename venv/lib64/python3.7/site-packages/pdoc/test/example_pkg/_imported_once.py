import sys

try:
    sys._pdoc_imported_once_flag
except AttributeError:
    sys._pdoc_imported_once_flag = True
else:
    assert False, 'Module _imported_once already imported'
