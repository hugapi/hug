import importlib
import os
import pkgutil
import typing

import pdocs.doc


class ExtractError(Exception):
    pass


def split_module_spec(spec: str) -> typing.Tuple[str, str]:
    """
        Splits a module specification into a base path (which may be empty), and a module name.

        Raises ExtactError if the spec is invalid.
    """
    if not spec:
        raise ExtractError("Empty module spec.")
    if (os.sep in spec) or (os.altsep and os.altsep in spec):
        dirname, fname = os.path.split(spec)
        if fname.endswith(".py"):
            mname, _ = os.path.splitext(fname)
            return dirname, mname
        else:
            if "." in fname:
                raise ExtractError(
                    "Invalid module name {fname}. Mixing path and module specifications "
                    "is not supported.".format(fname=fname)
                )
            return dirname, fname
    else:
        return "", spec


def load_module(basedir: str, module: str) -> typing.Tuple[typing.Any, bool]:
    """
        Returns a module object, and whether the module is a package or not.
    """
    ispackage = False
    if basedir:
        mods = module.split(".")
        dirname = os.path.join(basedir, *mods[:-1])
        modname = mods[-1]

        pkgloc = os.path.join(dirname, modname, "__init__.py")
        fileloc = os.path.join(dirname, modname + ".py")

        if os.path.exists(pkgloc):
            location, ispackage = pkgloc, True
        elif os.path.exists(fileloc):
            location, ispackage = fileloc, False
        else:
            raise ExtractError(
                "Module {module} not found in {basedir}".format(module=module, basedir=basedir)
            )

        ispec = importlib.util.spec_from_file_location(modname, location)
        mobj = importlib.util.module_from_spec(ispec)
        try:
            # This can literally raise anything
            ispec.loader.exec_module(mobj)  # type: ignore
        except Exception as e:
            raise ExtractError("Error importing {location}: {e}".format(location=location, e=e))
        return mobj, ispackage
    else:
        try:
            # This can literally raise anything
            m = importlib.import_module(module)
        except ImportError:
            raise ExtractError("Module not found: {module}".format(module=module))
        except Exception as e:
            raise ExtractError("Error importing {module}: {e}".format(module=module, e=e))
        # This is the only case where we actually have to test whether we're a package
        if getattr(m, "__package__", False) and getattr(m, "__path__", False):
            ispackage = True
        return m, ispackage


def submodules(dname: str, mname: str) -> typing.Sequence[str]:
    """
        Returns a list of fully qualified submodules within a package, given a
        base directory and a fully qualified module name.
    """
    loc = os.path.join(dname, *mname.split("."))
    ret = []
    for mi in pkgutil.iter_modules([loc], prefix=mname + "."):
        if isinstance(mi, tuple):
            # Python 3.5 compat
            ret.append(mi[1])
        else:
            ret.append(mi.name)
    ret.sort()
    return ret


def _extract_module(dname: str, mname: str, parent=None) -> typing.Any:
    m, pkg = load_module(dname, mname)
    mod = pdocs.doc.Module(mname, m, parent)
    if pkg:
        for submodule_full_name in submodules(dname, mname):
            if submodule_full_name.split(".")[-1].startswith("_"):
                continue

            mod.submodules.append(_extract_module(dname, submodule_full_name, parent=mod))
    return mod


def extract_module(spec: str):
    """
        Extracts and returns a module object. The spec argument can have the
        following forms:

        Simple module: "foo.bar"
        Module path: "./path/to/module"
        File path: "./path/to/file.py"

        This function always invalidates caches to enable hot load and reload.

        May raise ExtactError.
    """
    importlib.invalidate_caches()
    dname, mname = split_module_spec(spec)
    return _extract_module(dname, mname)
