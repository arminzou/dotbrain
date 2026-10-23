"""Owned copies of files from the shared plugin tree in a runtime's user home.

A marker identifies dotbrain's copy. Dotbrain replaces only a directory it marked.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from collections.abc import Iterator, Sequence
from pathlib import Path

from dotbrain import resource_loader

MARKER = ".dotbrain-managed"


def _files(root: Path, names: Sequence[str]) -> Iterator[Path]:
    for name in names:
        path = root / name
        if path.is_dir():
            yield from sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        else:
            yield path


def digest(root: Path, names: Sequence[str]) -> str:
    """Content digest of the named files below ``root``; the marker is not part of it."""
    h = hashlib.sha256()
    for path in _files(root, names):
        body = path.read_bytes() + b"\0" if path.is_file() else b"\1missing"
        h.update(path.relative_to(root).as_posix().encode() + b"\0" + body)
    return h.hexdigest()


def owned(target: Path) -> bool:
    return not target.is_symlink() and (target / MARKER).is_file()


def remove(target: Path) -> bool:
    """Remove only a copy carrying our ownership marker."""
    if not owned(target):
        return False
    shutil.rmtree(target)
    return True


def state(target: Path, names: Sequence[str]) -> str:
    """``missing``, ``foreign`` (not dotbrain's), ``stale``, or ``current``."""
    if not (target.exists() or target.is_symlink()):
        return "missing"
    if not owned(target):
        return "foreign"
    # Compare the delivered files themselves, so a damaged copy is repaired despite its marker.
    with resource_loader.plugin_tree() as source:
        current = digest(target, names) == digest(source, names)
    return "current" if current else "stale"


def install(target: Path, names: Sequence[str]) -> None:
    """Replace ``target`` with a fresh copy; the caller has checked it is missing or owned."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # A fresh staging directory of our own: nothing already beside the target is touched.
    staging = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}-staging-"))
    try:
        with resource_loader.plugin_tree() as source:
            for name in names:
                if (source / name).is_dir():
                    shutil.copytree(source / name, staging / name, ignore=shutil.ignore_patterns("__pycache__"))
                else:
                    shutil.copy2(source / name, staging / name)
            (staging / MARKER).write_text("dotbrain\n", encoding="utf-8", newline="\n")
        if target.exists():
            shutil.rmtree(target)
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
