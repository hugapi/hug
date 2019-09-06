import pathlib
import typing

import pdocs.doc
import pdocs.render


class StaticError(Exception):
    pass


def module_to_path(m: pdocs.doc.Module, extension="html") -> pathlib.Path:
    """
        Calculates the filesystem path for the static output of a given module.
    """
    p = pathlib.Path(*m.name.split("."))
    if m.submodules:
        p /= f"index.{extension}"
    else:
        p = p.with_suffix(f".{extension}")
    return p


def path_to_module(
    roots: typing.Sequence[pdocs.doc.Module], path: pathlib.Path
) -> pdocs.doc.Module:
    """
        Retrieves the matching module for a given path from a module tree.
    """
    if path.suffix == ".html":
        path = path.with_suffix("")
    parts = list(path.parts)
    if parts[-1] == "index":
        parts = parts[:-1]
    elif parts[-1] == "index.m":
        parts[-1] = "index"
    for root in roots:
        mod = root.find_ident(".".join(parts))
        if isinstance(mod, pdocs.doc.Module):
            return mod
    raise StaticError("No matching module for {path}".format(path=path))


def would_overwrite(destination: pathlib.Path, roots: typing.Sequence[pdocs.doc.Module]) -> bool:
    """Would rendering root to dst overwrite any file?"""
    if len(roots) > 1:
        path = destination / "index.html"
        if path.exists():
            return True
    for root in roots:
        if destination.joinpath(root.name).exists():
            return True
    return False


def html_out(
    dst: pathlib.Path,
    roots: typing.Sequence[pdocs.doc.Module],
    external_links: bool = True,
    link_prefix: str = "",
    source: bool = False,
):
    if len(roots) > 1:
        dst.mkdir(parents=True, exist_ok=True)
        p = dst / "index.html"
        idx = pdocs.render.html_index(roots, link_prefix=link_prefix)
        p.write_text(idx, encoding="utf-8")
    for root in roots:
        for m in root.allmodules():
            p = dst.joinpath(module_to_path(m))
            p.parent.mkdir(parents=True, exist_ok=True)
            out = pdocs.render.html_module(
                m, external_links=external_links, link_prefix=link_prefix, source=source
            )
            p.write_text(out, encoding="utf-8")


def md_out(
    dst: pathlib.Path,
    roots: typing.Sequence[pdocs.doc.Module],
    externel_links: bool = True,
    source: bool = False,
):
    for root in roots:
        for m in root.allmodules():
            p = dst.joinpath(module_to_path(m, extension="md"))
            p.parent.mkdir(parents=True, exist_ok=True)
            out = pdocs.render.text(m, source=source)
            p.write_text(out, encoding="utf-8")
