"""Hermes delivery: an owned copy of the dotbrain plugin in the Hermes home.

Hermes loads user plugins from ``$HERMES_HOME/plugins/<name>/`` once ``<name>`` is listed under
``plugins.enabled`` in ``$HERMES_HOME/config.yaml``. Dotbrain copies its plugin there with an
ownership marker, replaces only its own copy, and enables it through the Hermes CLI; it never edits
the Hermes configuration itself.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

import yaml

from dotbrain import resource_loader
from dotbrain.skills import LinkResult

PLUGIN = "dotbrain"
# Holds the digest of the delivered plugin tree; its presence marks the copy as dotbrain's.
MARKER = ".dotbrain-managed"
ENABLE = f"hermes plugins enable {PLUGIN}"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _default_run(argv: Sequence[str], *, env: dict | None = None) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(list(argv), env=env, check=True, capture_output=True, encoding="utf-8",
                          stdin=subprocess.DEVNULL, timeout=60)


def plugin_dir(hermes_home: Path) -> Path:
    return Path(hermes_home) / "plugins" / PLUGIN


def _files(root: Path, names: Sequence[str]) -> Iterator[Path]:
    for name in names:
        path = root / name
        if path.is_dir():
            yield from sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        else:
            yield path


def digest(root: Path, names: Sequence[str] = resource_loader.HERMES_PLUGIN_FILES) -> str:
    """Content digest of the named plugin files below ``root``; the marker is not part of it."""
    h = hashlib.sha256()
    for path in _files(root, names):
        body = path.read_bytes() + b"\0" if path.is_file() else b"\1missing"
        h.update(path.relative_to(root).as_posix().encode() + b"\0" + body)
    return h.hexdigest()


def tree_owned(target: Path) -> bool:
    return not target.is_symlink() and (target / MARKER).is_file()


def tree_state(target: Path, source: Path, names: Sequence[str]) -> str:
    """``missing``, ``foreign`` (not dotbrain's), ``stale``, or ``current`` for an owned copy of
    the named files of ``source`` at ``target``."""
    if not (target.exists() or target.is_symlink()):
        return "missing"
    if not tree_owned(target):
        return "foreign"
    # Compare the delivered files themselves, so a damaged copy is repaired despite its marker.
    return "current" if digest(target, names) == digest(source, names) else "stale"


def replace_tree(target: Path, source: Path, names: Sequence[str]) -> None:
    """Copy the named files of ``source`` to ``target`` with an ownership marker; the caller has
    checked that ``target`` is missing or dotbrain's own copy."""
    target.parent.mkdir(parents=True, exist_ok=True)
    # A fresh staging directory of our own: nothing already beside the target is touched.
    staging = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}-staging-"))
    try:
        for name in names:
            if (source / name).is_dir():
                shutil.copytree(source / name, staging / name, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(source / name, staging / name)
        (staging / MARKER).write_text(digest(source, names) + "\n", encoding="utf-8", newline="\n")
        if target.exists():
            shutil.rmtree(target)  # owned: the caller saw it stale, not foreign
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def owned(hermes_home: Path) -> bool:
    return tree_owned(plugin_dir(hermes_home))


def skills_dir(hermes_home: Path) -> Path:
    """Where operator-selected global skills are linked for Hermes."""
    return Path(hermes_home) / "skills"


def state(hermes_home: Path) -> str:
    """``missing``, ``foreign`` (not dotbrain's), ``stale``, or ``current``."""
    with resource_loader.hermes_plugin() as source:
        return tree_state(plugin_dir(hermes_home), source, resource_loader.HERMES_PLUGIN_FILES)


def activation(hermes_home: Path) -> str:
    """``enabled``, ``disabled``, or ``not enabled``, read from the Hermes configuration."""
    path = Path(hermes_home) / "config.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    plugins = data.get("plugins") if isinstance(data, dict) else None
    plugins = plugins if isinstance(plugins, dict) else {}

    def listed(key: str) -> bool:
        names = plugins.get(key)
        return isinstance(names, list) and PLUGIN in names

    # Hermes lets plugins.disabled win over plugins.enabled.
    return "disabled" if listed("disabled") else "enabled" if listed("enabled") else "not enabled"


def trusted(hermes_home: Path, checkout: Path) -> bool:
    """Whether Hermes loads project skills from this checkout (``skills.trusted_project_dirs``)."""
    path = Path(hermes_home) / "config.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    section = data.get("skills") if isinstance(data, dict) else None
    entries = section.get("trusted_project_dirs") if isinstance(section, dict) else None
    if not isinstance(entries, list):
        return False
    # `hermes skills trust` records absolute paths; a relative entry depends on Hermes's cwd.
    roots = {Path(os.path.expandvars(entry)).expanduser() for entry in entries if isinstance(entry, str)}
    return Path(checkout).resolve() in {root.resolve() for root in roots if root.is_absolute()}


def deliver(hermes_home: Path, *, run: Runner = _default_run) -> LinkResult:
    """Install or update dotbrain's plugin copy, then enable it when the Hermes CLI is available."""
    result = LinkResult()
    target = plugin_dir(hermes_home)
    current = state(hermes_home)
    if current == "foreign":
        result.warnings.append(f"{target} exists and was not created by dotbrain; skipping")
        return result
    if current != "current":
        with resource_loader.hermes_plugin() as source:
            replace_tree(target, source, resource_loader.HERMES_PLUGIN_FILES)
        result.linked.append(f"hermes/plugins/{PLUGIN}")
    if activation(hermes_home) == "not enabled":
        if shutil.which("hermes") is None:
            result.linked.append(f"hermes: run `{ENABLE}` to load the plugin")
        else:
            try:
                run(["hermes", "plugins", "enable", PLUGIN], env={**os.environ, "HERMES_HOME": str(hermes_home)})
                result.linked.append(f"hermes: enabled plugin {PLUGIN}")
            except (OSError, subprocess.SubprocessError) as exc:
                # A timeout carries raw bytes; a fresh Hermes home can outlast it preparing its runtime.
                detail = str(exc) if isinstance(exc, subprocess.TimeoutExpired) else getattr(exc, "stderr", None) or str(exc)
                result.warnings.append(f"hermes: `{ENABLE}` failed: {detail.strip()}")
    return result
