def import_module(callback):
    """
    Handle "magic" Flask extension imports:
    ``flask.ext.foo`` is really ``flask_foo`` or ``flaskext.foo``.
    """
    def wrapper(evaluator, import_names, module_context, *args, **kwargs):
        if len(import_names) == 3 and import_names[:2] == ('flask', 'ext'):
            # New style.
            ipath = (u'flask_' + import_names[2]),
            context_set = callback(evaluator, ipath, None, *args, **kwargs)
            if context_set:
                return context_set
            context_set = callback(evaluator, (u'flaskext',), None, *args, **kwargs)
            return callback(
                evaluator,
                (u'flaskext', import_names[2]),
                next(iter(context_set)),
                *args, **kwargs
            )
        return callback(evaluator, import_names, module_context, *args, **kwargs)
    return wrapper
