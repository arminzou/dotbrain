"""Cursor skill discovery, reusing shared sources and owned-copy delivery."""
import os
import re
import json
import sys
from pathlib import Path

import yaml

from dotbrain import claude_plugins, owned_copy, resource_loader, skills

KIND = "skill bundle"
ROOTS = (".cursor/skills", ".claude/skills", ".codex/skills", ".grok/skills", ".agents/skills")
FILES = ("skills",)
GLOBAL = ".global-delivery"

# Launch-time resume retains the original convention on the server but runs no startup sync.
# preCompact is observe-only: it cannot return context. Startup context accompanies every
# request, so compaction needs no refresh callback. Native lifecycle qualification is separate.
HOOK_EVENTS = {"sessionStart": "startup", "stop": "turn-end", "sessionEnd": "session-end"}


def hook_entries(*, windows: bool | None = None) -> dict:
    windows = sys.platform == "win32" if windows is None else windows
    checkout = '$env:CURSOR_PROJECT_DIR' if windows else '"$CURSOR_PROJECT_DIR"'
    return {native: [{"command": f"dotbrain hook run --event {event} --checkout {checkout} --format json",
                      "timeout": 15 if event == "startup" else 5}]
            for native, event in HOOK_EVENTS.items()}


def _owned_hook(entry: dict) -> bool:
    return bool(re.search(r"(?<![\w./-])dotbrain(?:\.exe)?\s+hook\s+(?:run|session-start|stop|session-end)\b",
                          entry["command"]))


def _read_hooks(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8").removeprefix("\ufeff")) if path.exists() else {}
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        raise ValueError("expected an object with a hooks object")
    for entries in data.get("hooks", {}).values():
        if not isinstance(entries, list) or any(not isinstance(e, dict) or not isinstance(e.get("command"), str)
                                                for e in entries):
            raise ValueError("expected hook arrays with command strings")
    return data


def reconcile_hooks(user_home: Path, *, remove: bool = False) -> skills.LinkResult:
    """Merge or remove command-owned entries, preserving every unrelated setting."""
    result = skills.LinkResult()
    path = user_home / ".cursor/hooks.json"
    try:
        data = _read_hooks(path)
        original = json.loads(json.dumps(data))
        hooks = data.setdefault("hooks", {})
        for event, entries in list(hooks.items()):
            kept = [entry for entry in entries if not _owned_hook(entry)]
            if kept:
                hooks[event] = kept
            elif entries:  # keep unrelated empty event arrays
                del hooks[event]
        if not remove:
            data.setdefault("version", 1)
            for event, entries in hook_entries().items():
                hooks.setdefault(event, []).extend(entries)
        if data == original or (remove and not path.exists()):
            return result
        if remove and not hooks and not (data.keys() - {"version", "hooks"}):
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
        (result.pruned if remove else result.linked).append("cursor/hooks.json")
    except (OSError, ValueError) as exc:
        result.warnings.append(f"{path}: cannot reconcile Cursor hooks: {exc}")
    return result


def hook_state(user_home: Path) -> str:
    path = user_home / ".cursor/hooks.json"
    try:
        data = _read_hooks(path)
    except (OSError, ValueError):
        return "malformed"
    actual = {event: [entry for entry in entries if _owned_hook(entry)]
              for event, entries in data.get("hooks", {}).items()}
    actual = {event: entries for event, entries in actual.items() if entries}
    if not actual:
        return "foreign" if path.exists() else "missing"
    return "current" if actual == hook_entries() else "stale"


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


def sources(home: Path, selection, *, scopes: tuple[Path, ...] = ()) -> dict[str, Path]:
    selected = skills.resolve_selection(home, selection)
    with resource_loader.plugin_tree() as source:
        packaged = skills.discover_skills(source / "skills")
    result = {Path(name).name: plugin_dir(home) / "skills" / name for name in packaged}
    for identifier, installation in claude_plugins.enabled_installs(scopes, include_stale=False):
        if identifier == "dotbrain@dotbrain":
            for name in packaged:
                result[Path(name).name] = installation / "skills" / name
    for name in selected:
        leaf = _identity(home / "skills" / name)
        if leaf in result:
            raise ValueError(f"skill destination collision: packaged skill and {name}")
        result[leaf] = home / "skills" / name
    return result


def discovered(*scopes: Path, exclude: Path | None = None, include_stale: bool = True) -> dict[str, set[Path]]:
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
    for _, installation in claude_plugins.enabled_installs(scopes, include_stale=include_stale):
        for directory in directories(installation / "skills"):
            found.setdefault(_identity(directory), set()).add(directory.resolve())
    return found


def deliver(home: Path, receiver: Path, selection, *, scopes: tuple[Path, ...], global_scope: bool = False) -> skills.LinkResult:
    desired = sources(home, selection, scopes=scopes)  # validate before mutation
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
    roots = (home / "skills",) + ((plugin_dir(home),) if owned(home) else ())
    elsewhere = discovered(*scopes, exclude=receiver, include_stale=False)
    # Remove only obsolete owned links, including ones another discovery root now supplies.
    for entry in receiver.iterdir():
        if not entry.is_symlink() or not any(skills._points_into(entry, root) for root in roots):
            continue
        if entry.name not in desired or entry.resolve() != desired[entry.name].resolve() or entry.name in elsewhere:
            entry.unlink()
            result.pruned.append(f".cursor/skills/{entry.name}")
    visible = discovered(*scopes, include_stale=False)
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
