"""Pi delivery: an owned copy of the dotbrain extension in the Pi agent directory.

Pi loads every ``<agent dir>/extensions/<name>/index.js`` on its own, so dotbrain copies its
extension there with an ownership marker and replaces only its own copy; it writes no Pi settings.
The extension hands Pi the packaged skills beside it.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotbrain import owned_copy, resource_loader
from dotbrain.skills import LinkResult

EXTENSION = "dotbrain"
KIND = "extension"


def plugin_dir(agent_dir: Path) -> Path:
    return Path(agent_dir) / "extensions" / EXTENSION


def skills_dir(agent_dir: Path) -> Path:
    """Where operator-selected global skills are linked for Pi."""
    return Path(agent_dir) / "skills"


def owned(agent_dir: Path) -> bool:
    return owned_copy.owned(plugin_dir(agent_dir))


def state(agent_dir: Path) -> str:
    """``missing``, ``foreign`` (not dotbrain's), ``stale``, or ``current``."""
    return owned_copy.state(plugin_dir(agent_dir), resource_loader.PI_EXTENSION_FILES)


def trusted(agent_dir: Path, checkout: Path) -> bool:
    """Whether Pi loads ``<checkout>/.pi/skills``: the nearest decision in ``trust.json`` is true."""
    path = Path(agent_dir) / "trust.json"
    data = json.loads(path.read_text(encoding="utf-8").removeprefix("﻿")) if path.is_file() else {}
    if not isinstance(data, dict):
        return False
    decisions = {Path(key).resolve(): value for key, value in data.items() if isinstance(value, bool)}
    checkout = Path(checkout).resolve()
    return next((decisions[d] for d in (checkout, *checkout.parents) if d in decisions), False)


def trust_hint(checkout: Path) -> str:
    return f"start pi in {checkout} and trust the project"


def deliver(agent_dir: Path, *, run=None) -> LinkResult:
    """Install or update dotbrain's extension copy. ``run`` is unused: Pi needs no enable step."""
    result = LinkResult()
    target = plugin_dir(agent_dir)
    current = state(agent_dir)
    if current == "foreign":
        result.warnings.append(f"{target} exists and was not created by dotbrain; skipping")
    elif current != "current":
        owned_copy.install(target, resource_loader.PI_EXTENSION_FILES)
        result.linked.append(f"pi/extensions/{EXTENSION}")
    return result
