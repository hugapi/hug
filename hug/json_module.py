import os

HUG_USE_UJSON = bool(os.environ.get('HUG_USE_UJSON', 1))
try:  # pragma: no cover
    if HUG_USE_UJSON:
        import ujson as json

        class dumps_proxy:
            """Proxies the call so non supported kwargs are skipped
            and it enables escape_forward_slashes to simulate built-in json
            """
            _dumps = json.dumps

            def __call__(self, *args, **kwargs):
                kwargs.pop('default', None)
                kwargs.pop('separators', None)
                kwargs.update(escape_forward_slashes=False)
                try:
                    return self._dumps(*args, **kwargs)
                except Exception as exc:
                    raise TypeError("Type[ujson] is not Serializable", exc)

        json.dumps = dumps_proxy()
    else:
        import json
except ImportError:  # pragma: no cover
    import json
