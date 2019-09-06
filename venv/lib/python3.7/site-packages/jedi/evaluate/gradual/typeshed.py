import os
import re
from functools import wraps

from jedi.file_io import FileIO
from jedi._compatibility import FileNotFoundError, cast_path
from jedi.parser_utils import get_cached_code_lines
from jedi.evaluate.base_context import ContextSet, NO_CONTEXTS
from jedi.evaluate.gradual.stub_context import TypingModuleWrapper, StubModuleContext

_jedi_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TYPESHED_PATH = os.path.join(_jedi_path, 'third_party', 'typeshed')

_IMPORT_MAP = dict(
    _collections='collections',
    _socket='socket',
)


def _merge_create_stub_map(directories):
    map_ = {}
    for directory in directories:
        map_.update(_create_stub_map(directory))
    return map_


def _create_stub_map(directory):
    """
    Create a mapping of an importable name in Python to a stub file.
    """
    def generate():
        try:
            listed = os.listdir(directory)
        except (FileNotFoundError, OSError):
            # OSError is Python 2
            return

        for entry in listed:
            entry = cast_path(entry)
            path = os.path.join(directory, entry)
            if os.path.isdir(path):
                init = os.path.join(path, '__init__.pyi')
                if os.path.isfile(init):
                    yield entry, init
            elif entry.endswith('.pyi') and os.path.isfile(path):
                name = entry.rstrip('.pyi')
                if name != '__init__':
                    yield name, path

    # Create a dictionary from the tuple generator.
    return dict(generate())


def _get_typeshed_directories(version_info):
    check_version_list = ['2and3', str(version_info.major)]
    for base in ['stdlib', 'third_party']:
        base = os.path.join(TYPESHED_PATH, base)
        base_list = os.listdir(base)
        for base_list_entry in base_list:
            match = re.match(r'(\d+)\.(\d+)$', base_list_entry)
            if match is not None:
                if int(match.group(1)) == version_info.major \
                        and int(match.group(2)) <= version_info.minor:
                    check_version_list.append(base_list_entry)

        for check_version in check_version_list:
            yield os.path.join(base, check_version)


_version_cache = {}


def _cache_stub_file_map(version_info):
    """
    Returns a map of an importable name in Python to a stub file.
    """
    # TODO this caches the stub files indefinitely, maybe use a time cache
    # for that?
    version = version_info[:2]
    try:
        return _version_cache[version]
    except KeyError:
        pass

    _version_cache[version] = file_set = \
        _merge_create_stub_map(_get_typeshed_directories(version_info))
    return file_set


def import_module_decorator(func):
    @wraps(func)
    def wrapper(evaluator, import_names, parent_module_context, sys_path, prefer_stubs):
        try:
            python_context_set = evaluator.module_cache.get(import_names)
        except KeyError:
            if parent_module_context is not None and parent_module_context.is_stub():
                parent_module_contexts = parent_module_context.non_stub_context_set
            else:
                parent_module_contexts = [parent_module_context]
            if import_names == ('os', 'path'):
                # This is a huge exception, we follow a nested import
                # ``os.path``, because it's a very important one in Python
                # that is being achieved by messing with ``sys.modules`` in
                # ``os``.
                python_parent = next(iter(parent_module_contexts))
                if python_parent is None:
                    python_parent, = evaluator.import_module(('os',), prefer_stubs=False)
                python_context_set = python_parent.py__getattribute__('path')
            else:
                python_context_set = ContextSet.from_sets(
                    func(evaluator, import_names, p, sys_path,)
                    for p in parent_module_contexts
                )
            evaluator.module_cache.add(import_names, python_context_set)

        if not prefer_stubs:
            return python_context_set

        stub = _try_to_load_stub_cached(evaluator, import_names, python_context_set,
                                        parent_module_context, sys_path)
        if stub is not None:
            return ContextSet([stub])
        return python_context_set

    return wrapper


def _try_to_load_stub_cached(evaluator, import_names, *args, **kwargs):
    try:
        return evaluator.stub_module_cache[import_names]
    except KeyError:
        pass

    # TODO is this needed? where are the exceptions coming from that make this
    # necessary? Just remove this line.
    evaluator.stub_module_cache[import_names] = None
    evaluator.stub_module_cache[import_names] = result = \
        _try_to_load_stub(evaluator, import_names, *args, **kwargs)
    return result


def _try_to_load_stub(evaluator, import_names, python_context_set,
                      parent_module_context, sys_path):
    """
    Trying to load a stub for a set of import_names.

    This is modelled to work like "PEP 561 -- Distributing and Packaging Type
    Information", see https://www.python.org/dev/peps/pep-0561.
    """
    if parent_module_context is None and len(import_names) > 1:
        try:
            parent_module_context = _try_to_load_stub_cached(
                evaluator, import_names[:-1], NO_CONTEXTS,
                parent_module_context=None, sys_path=sys_path)
        except KeyError:
            pass

    # 1. Try to load foo-stubs folders on path for import name foo.
    if len(import_names) == 1:
        # foo-stubs
        for p in sys_path:
            init = os.path.join(p, *import_names) + '-stubs' + os.path.sep + '__init__.pyi'
            m = _try_to_load_stub_from_file(
                evaluator,
                python_context_set,
                file_io=FileIO(init),
                import_names=import_names,
            )
            if m is not None:
                return m

    # 2. Try to load pyi files next to py files.
    for c in python_context_set:
        try:
            method = c.py__file__
        except AttributeError:
            pass
        else:
            file_path = method()
            file_paths = []
            if c.is_namespace():
                file_paths = [os.path.join(p, '__init__.pyi') for p in c.py__path__()]
            elif file_path is not None and file_path.endswith('.py'):
                file_paths = [file_path + 'i']

            for file_path in file_paths:
                m = _try_to_load_stub_from_file(
                    evaluator,
                    python_context_set,
                    # The file path should end with .pyi
                    file_io=FileIO(file_path),
                    import_names=import_names,
                )
                if m is not None:
                    return m

    # 3. Try to load typeshed
    m = _load_from_typeshed(evaluator, python_context_set, parent_module_context, import_names)
    if m is not None:
        return m

    # 4. Try to load pyi file somewhere if python_context_set was not defined.
    if not python_context_set:
        if parent_module_context is not None:
            try:
                method = parent_module_context.py__path__
            except AttributeError:
                check_path = []
            else:
                check_path = method()
            # In case import_names
            names_for_path = (import_names[-1],)
        else:
            check_path = sys_path
            names_for_path = import_names

        for p in check_path:
            m = _try_to_load_stub_from_file(
                evaluator,
                python_context_set,
                file_io=FileIO(os.path.join(p, *names_for_path) + '.pyi'),
                import_names=import_names,
            )
            if m is not None:
                return m

    # If no stub is found, that's fine, the calling function has to deal with
    # it.
    return None


def _load_from_typeshed(evaluator, python_context_set, parent_module_context, import_names):
    import_name = import_names[-1]
    map_ = None
    if len(import_names) == 1:
        map_ = _cache_stub_file_map(evaluator.grammar.version_info)
        import_name = _IMPORT_MAP.get(import_name, import_name)
    elif isinstance(parent_module_context, StubModuleContext):
        if not parent_module_context.is_package:
            # Only if it's a package (= a folder) something can be
            # imported.
            return None
        path = parent_module_context.py__path__()
        map_ = _merge_create_stub_map(path)

    if map_ is not None:
        path = map_.get(import_name)
        if path is not None:
            return _try_to_load_stub_from_file(
                evaluator,
                python_context_set,
                file_io=FileIO(path),
                import_names=import_names,
            )


def _try_to_load_stub_from_file(evaluator, python_context_set, file_io, import_names):
    try:
        stub_module_node = evaluator.parse(
            file_io=file_io,
            cache=True,
            use_latest_grammar=True
        )
    except (OSError, IOError):  # IOError is Python 2 only
        # The file that you're looking for doesn't exist (anymore).
        return None
    else:
        return create_stub_module(
            evaluator, python_context_set, stub_module_node, file_io,
            import_names
        )


def create_stub_module(evaluator, python_context_set, stub_module_node, file_io, import_names):
    if import_names == ('typing',):
        module_cls = TypingModuleWrapper
    else:
        module_cls = StubModuleContext
    file_name = os.path.basename(file_io.path)
    stub_module_context = module_cls(
        python_context_set, evaluator, stub_module_node,
        file_io=file_io,
        string_names=import_names,
        # The code was loaded with latest_grammar, so use
        # that.
        code_lines=get_cached_code_lines(evaluator.latest_grammar, file_io.path),
        is_package=file_name == '__init__.pyi',
    )
    return stub_module_context
