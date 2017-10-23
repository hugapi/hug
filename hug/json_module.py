import os

HUG_USE_UJSON = bool(os.environ.get('HUG_USE_UJSON', 1))
try:
    if HUG_USE_UJSON:
        import ujson as json
    else:
        import json
except ImportError:
    import json
