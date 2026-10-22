"""Cursor skill discovery, reusing shared sources and owned-copy delivery."""
import os
import re
from pathlib import Path

import yaml

from dotbrain import owned_copy, resource_loader, skills

KIND = "skill bundle"
ROOTS = (".cursor/skills", ".claude/skills", ".codex/skills", ".grok/skills", ".agents/skills")
FILES = ("skills",)
GLOBAL = ".global-delivery"


def plugin_dir(directory: Path) -> Path:
    return Path(directory) / ".cache/cursor"


def owned(directory: Path) -> bool:
    return owned_copy.owned(plugin_dir(directory))


def state(directory: Path) -> str:
    return owned_copy.state(plugin_dir(directory), FILES)


def global_delivery(home: Path) -> bool:
    return owned(home) and (plugin_dir(home) / GLOBAL).is_file()


def _identity(directory: Path) -> str:
    body = (directory / "SKILL.md").read_text(encoding="utf-8")
    metadata = yaml.safe_load(body.split("---", 2)[1]) if body.startswith("---") else {}
    name = metadata.get("name") if isinstance(metadata, dict) else None
    return name if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) else directory.name


def sources(home: Path, selection) -> dict[str, Path]:
    selected = skills.resolve_selection(home, selection)
    with resource_loader.plugin_tree() as source:
        packaged = skills.discover_skills(source / "skills")
    result = {Path(name).name: plugin_dir(home) / "skills" / name for name in packaged}
    for name in selected:
        leaf = _identity(home / "skills" / name)
        if leaf in result:
            raise ValueError(f"skill destination collision: packaged skill and {name}")
        result[leaf] = home / "skills" / name
    return result


def discovered(*scopes: Path, exclude: Path | None = None) -> dict[str, set[Path]]:
    """Native discovery roots, deduplicated by real path; supporting files stay beside SKILL.md."""
    found: dict[str, set[Path]] = {}
    visited: set[Path] = set()

    def directories(root):
        if not root.is_dir() or root.resolve() in visited or (exclude and root.resolve() == exclude.resolve()):
            return
        visited.add(root.resolve())
        if (root / "SKILL.md").is_file():
            yield root
            return
        for entry in root.iterdir():
            if entry.name != "node_modules" and entry.is_dir():
                yield from directories(entry)

    for scope in dict.fromkeys(scopes):
        for relative in (*ROOTS, ".cursor/skills-cursor"):
            root = scope / relative
            for directory in directories(root):
                found.setdefault(_identity(directory), set()).add(directory.resolve())
    return found


def deliver(home: Path, receiver: Path, selection, *, scopes: tuple[Path, ...], global_scope: bool = False) -> skills.LinkResult:
    desired = sources(home, selection)  # validate before mutation
    result = skills.LinkResult()
    current = state(home)
    opted_in = global_delivery(home)
    if current == "foreign":
        result.warnings.append(f"{plugin_dir(home)} exists and was not created by dotbrain; skipping")
    elif current != "current":
        owned_copy.install(plugin_dir(home), FILES)
        result.linked.append("cursor/skill-bundle")
    if current != "foreign" and (opted_in or global_scope):
        (plugin_dir(home) / GLOBAL).touch()
    if receiver.is_symlink() or (receiver.exists() and not receiver.is_dir()):
        result.warnings.append(f"{receiver}: foreign asset directory conflicts with delivery")
        return result
    receiver.mkdir(parents=True, exist_ok=True)
    roots = (home / "skills", plugin_dir(home))
    elsewhere = discovered(*scopes, exclude=receiver)
    # Remove only obsolete owned links, including ones another discovery root now supplies.
    for entry in receiver.iterdir():
        if not entry.is_symlink() or not any(skills._points_into(entry, root) for root in roots):
            continue
        if entry.name not in desired or entry.resolve() != desired[entry.name].resolve() or entry.name in elsewhere:
            entry.unlink()
            result.pruned.append(f".cursor/skills/{entry.name}")
    visible = discovered(*scopes)
    for name, source in desired.items():
        seen = visible.get(name, set())
        if seen:
            if seen != {source.resolve()}:
                result.warnings.append(f"cursor: foreign or duplicate skill {name}; preserving existing discovery")
            continue
        dest = receiver / name
        if dest.exists() or dest.is_symlink():
            result.warnings.append(f"{dest} exists and was not created by dotbrain; skipping")
        elif source.is_dir() and (source.is_relative_to(home / "skills") or current != "foreign"):
            dest.symlink_to(os.path.relpath(source, receiver), target_is_directory=True)
            result.linked.append(f".cursor/skills/{name}")
    return result
