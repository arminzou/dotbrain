"""Hermes delivery: an owned copy of the dotbrain plugin in the Hermes home.

Hermes loads user plugins from ``$HERMES_HOME/plugins/<name>/`` once ``<name>`` is listed under
``plugins.enabled`` in ``$HERMES_HOME/config.yaml``. Dotbrain copies its plugin there with an
ownership marker, replaces only its own copy, and enables it through the Hermes CLI; it never edits
the Hermes configuration itself.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

import yaml

from dotbrain import owned_copy, resource_loader
from dotbrain.skills import LinkResult

PLUGIN = "dotbrain"
KIND = "plugin"
ENABLE = f"hermes plugins enable {PLUGIN}"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _default_run(argv: Sequence[str], *, env: dict | None = None) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(list(argv), env=env, check=True, capture_output=True, encoding="utf-8",
                          stdin=subprocess.DEVNULL, timeout=60)


def plugin_dir(hermes_home: Path) -> Path:
    return Path(hermes_home) / "plugins" / PLUGIN


def owned(hermes_home: Path) -> bool:
    return owned_copy.owned(plugin_dir(hermes_home))


def skills_dir(hermes_home: Path) -> Path:
    """Where operator-selected global skills are linked for Hermes."""
    return Path(hermes_home) / "skills"


def state(hermes_home: Path) -> str:
    """``missing``, ``foreign`` (not dotbrain's), ``stale``, or ``current``."""
    return owned_copy.state(plugin_dir(hermes_home), resource_loader.HERMES_PLUGIN_FILES)


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


def trust_hint(checkout: Path) -> str:
    return f"run hermes skills trust {checkout}"


def deliver(hermes_home: Path, *, run: Runner = _default_run) -> LinkResult:
    """Install or update dotbrain's plugin copy, then enable it when the Hermes CLI is available."""
    result = LinkResult()
    target = plugin_dir(hermes_home)
    current = state(hermes_home)
    if current == "foreign":
        result.warnings.append(f"{target} exists and was not created by dotbrain; skipping")
        return result
    if current != "current":
        owned_copy.install(target, resource_loader.HERMES_PLUGIN_FILES)
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


def remove(hermes_home: Path, *, run: Runner = _default_run) -> LinkResult:
    result = LinkResult()
    if not owned(hermes_home):
        return result
    command = ["hermes", "plugins", "disable", PLUGIN]
    if shutil.which("hermes") is None:
        result.warnings.append("hermes: could not disable plugin; hermes is not on PATH")
    else:
        try:
            run(command, env={**os.environ, "HERMES_HOME": str(hermes_home)})
        except (OSError, subprocess.SubprocessError) as exc:
            result.warnings.append(f"hermes: could not disable plugin: {exc}")
    if owned_copy.remove(plugin_dir(hermes_home)):
        result.pruned.append(str(plugin_dir(hermes_home)))
    return result
