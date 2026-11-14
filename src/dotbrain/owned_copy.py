"""Owned copies of files from the shared plugin tree in a runtime's user home.

A marker identifies dotbrain's copy. Dotbrain replaces only a directory it marked.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Iterator, Sequence
from pathlib import Path

from dotbrain import paths, resource_loader, run_cache, skills

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


def _stamps(root: Path, names: Sequence[str]) -> list[tuple[str, int, int]]:
    """Each file's path, size and modification time; copies keep the source's times."""
    return [(path.relative_to(root).as_posix(), *((s := path.stat()).st_size, s.st_mtime_ns))
            if path.is_file() else (path.relative_to(root).as_posix(), -1, -1) for path in _files(root, names)]


def owned(target: Path) -> bool:
    marker = target / MARKER
    return (not target.is_symlink() and not skills._is_junction(target)
            and not marker.is_symlink() and marker.is_file())


def remove(target: Path) -> bool:
    """Remove only a copy carrying our ownership marker."""
    if not owned(target):
        return False
    paths.refuse_checkout(target)
    preserved = _preserve_retired(target)
    if preserved:
        raise ValueError(f"modified or ambiguous retired resources preserved at {preserved}; inspect before removing")
    shutil.rmtree(target)
    run_cache.clear()
    return True


def state(target: Path, names: Sequence[str]) -> str:
    """``missing``, ``foreign`` (not dotbrain's), ``stale``, or ``current``."""
    if not (target.exists() or target.is_symlink()):
        return "missing"
    if not owned(target):
        return "foreign"
    # Compare the delivered files themselves, so a damaged copy is repaired despite its marker.
    with resource_loader.plugin_tree() as source:
        # Matching sizes and times mean an untouched copy; anything else is decided by content.
        current = _stamps(target, names) == _stamps(source, names) or digest(target, names) == digest(source, names)
    return "current" if current else "stale"


def _preserve_retired(target: Path) -> Path | None:
    """Keep changed old skill bundles outside discovery paths before replacing them."""
    known = json.loads(resource_loader.resource("retired-skills.json").read_text(encoding="utf-8"))
    skill_root = target / "skills"
    with resource_loader.plugin_tree() as source:
        retained = {entry.name for entry in (source / "skills").iterdir() if entry.is_dir()}
    retired = {Path(name).parts[1] for name in known
               if name.startswith("skills/") and len(Path(name).parts) > 2} - retained
    if not (skill_root.is_symlink() or skills._is_junction(skill_root)
            or any((skill_root / name).exists() or (skill_root / name).is_symlink() for name in retired)):
        return None

    def changed(directory: Path) -> bool:
        for entry in directory.iterdir():
            if entry.is_symlink() or skills._is_junction(entry):
                return True
            if entry.name == "__pycache__" and entry.is_dir():
                continue
            if entry.is_dir():
                prefix = entry.relative_to(target).as_posix() + "/"
                if not any(name.startswith(prefix) for name in known) or changed(entry):
                    return True
            elif entry.relative_to(target).as_posix() not in (MARKER, ".global-delivery"):
                expected = known.get(entry.relative_to(target).as_posix())
                if not entry.is_file() or hashlib.sha256(entry.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected:
                    return True
        return False

    if changed(target):
        # Outside each adapter's plugin/extension and skills discovery directories.
        parent = target.parent.parent / ".dotbrain-preserved"
        if parent.is_symlink() or skills._is_junction(parent):
            raise ValueError(f"{parent}: preservation directory must be a real directory")
        paths.refuse_checkout(parent)
        parent.mkdir(exist_ok=True)
        backup = Path(tempfile.mkdtemp(dir=parent, prefix=f"{target.name}-"))
        backup.rmdir()
        target.rename(backup)
        return backup
    return None


def install(target: Path, names: Sequence[str]) -> Path | None:
    """Replace ``target`` with a fresh copy; the caller has checked it is missing or owned."""
    paths.refuse_checkout(target)
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
        preserved = _preserve_retired(target) if target.exists() else None
        if target.exists():
            shutil.rmtree(target)
        try:
            staging.rename(target)
        except OSError:
            if preserved and not target.exists():
                preserved.rename(target)
            raise
        run_cache.clear()
        return preserved
    finally:
        if staging.exists():
            shutil.rmtree(staging)
