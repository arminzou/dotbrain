"""OpenCode delivery: an owned plugin file and owned skill directories in the OpenCode config.

OpenCode loads every ``plugins/*.js`` file in its config directory (``$XDG_CONFIG_HOME/opencode``,
by default ``~/.config/opencode``). Dotbrain copies its plugin file there, the packaged skills to
``dotbrain/packaged/`` and the operator's global skill links to ``dotbrain/skills/``; OpenCode
scans neither on its own, and the plugin adds both to ``skills.paths``. Dotbrain replaces only
files it marked as its own and never edits the OpenCode configuration.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import yaml

from dotbrain import owned_copy, resource_loader
from dotbrain.skills import LinkResult

PLUGIN_FILE = "dotbrain.js"
# First line of the plugin file; it marks the copy as dotbrain's.
HEADER = b"// dotbrain-managed:"
SKILL_FILES = ("skills",)
# Skill directories a user may keep themselves that OpenCode scans as well: the same skill name
# found twice is loaded from one of them at random.
FOREIGN_SKILL_ROOTS = ("skills", "skill")
USER_SKILL_ROOTS = (".claude/skills", ".agents/skills")


def plugin_file(config_dir: Path) -> Path:
    return Path(config_dir) / "plugins" / PLUGIN_FILE


def packaged_dir(config_dir: Path) -> Path:
    return Path(config_dir) / "dotbrain" / "packaged"


def skills_dir(config_dir: Path) -> Path:
    """Where operator-selected global skills are linked for OpenCode."""
    return Path(config_dir) / "dotbrain" / "skills"


def _global_roots(config_dir: Path) -> list[Path]:
    return [packaged_dir(config_dir) / "skills", skills_dir(config_dir)]


class _Loader(yaml.SafeLoader):
    """YAML 1.2 booleans, as OpenCode's js-yaml reads them: `yes` and `on` stay strings."""


_Loader.yaml_implicit_resolvers = {
    key: [(tag, regex) for tag, regex in resolvers if tag != "tag:yaml.org,2002:bool"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
                              list("tTfF"))

_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(?:(.*?)\r?\n)?---[ \t]*(?:\r?\n|\Z)", re.S)


def _sanitize(block: str) -> str:
    """OpenCode's retry for unquoted colons: such a value becomes a block scalar."""
    out = []
    for line in block.splitlines():
        entry = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.*)$", line)
        value = entry.group(2).strip() if entry else ""
        if (not entry or line.strip().startswith("#") or re.match(r"^\s+", line) or value in ("", ">", "|")
                or value[0] in "\"'" or ":" not in value):
            out.append(line)
        else:
            out += [f"{entry.group(1)}: |-", f"  {value}"]
    return "\n".join(out)


def _frontmatter(file: Path):
    """The parsed frontmatter, ``{}`` without one, or ``None`` when OpenCode could not read it."""
    try:
        # As OpenCode reads it: invalid bytes become U+FFFD, and a BOM is stripped.
        text = file.read_bytes().decode("utf-8-sig", errors="replace")
    except OSError:
        return None
    match = _FRONTMATTER.match(text)
    if not match:
        return {}
    for block in (match.group(1) or "", _sanitize(match.group(1) or "")):
        try:
            return yaml.load(block, Loader=_Loader) or {}
        except yaml.YAMLError:
            continue
    return None


def _skill_files(root: Path, *, dot: bool = False, _ancestors: frozenset = frozenset()) -> list[Path]:
    """``SKILL.md`` files below ``root``, following links as OpenCode's scan does."""
    try:
        real = os.path.realpath(root)
        entries = sorted(os.scandir(root), key=lambda entry: entry.name)
    except OSError:
        return []
    if real in _ancestors:  # a link back up the tree
        return []
    found = []
    for entry in entries:
        try:
            if entry.name == "SKILL.md" and entry.is_file():
                found.append(Path(entry.path))
            elif entry.is_dir() and (dot or not entry.name.startswith(".")):
                found += _skill_files(Path(entry.path), dot=dot, _ancestors=_ancestors | {real})
        except OSError:
            continue
    return found


def skill_index(roots, *, dot: bool = False) -> list[dict]:
    """``{"name", "file"}`` for each skill OpenCode finds below ``roots``, named as OpenCode names it."""
    index = []
    for root in roots:
        for file in _skill_files(Path(root), dot=dot):
            data = _frontmatter(file)
            name, description = (data.get("name"), data.get("description")) if isinstance(data, dict) else (None, None)
            if not isinstance(name, str) or not (description is None or isinstance(description, str)):
                continue  # OpenCode does not load it as a skill
            index.append({"name": name, "file": str(file)})
    return index


def _write_atomic(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    # Written beside the target and moved over it, so OpenCode never reads half a file.
    handle, staging = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}-", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        os.replace(staging, target)
    finally:
        if os.path.exists(staging):
            os.unlink(staging)


def _file_owned(config_dir: Path) -> bool:
    target = plugin_file(config_dir)
    if target.is_symlink() or not target.is_file():
        return False
    with target.open("rb") as handle:
        return handle.read(len(HEADER)) == HEADER


def owned(config_dir: Path) -> bool:
    """Whether any of dotbrain's delivery is present, so later runs keep it current."""
    return _file_owned(config_dir) or owned_copy.owned(packaged_dir(config_dir))


def _file_state(config_dir: Path, source: Path) -> str:
    target = plugin_file(config_dir)
    if not (target.exists() or target.is_symlink()):
        return "missing"
    if not _file_owned(config_dir):
        return "foreign"
    return "current" if target.read_bytes() == source.read_bytes() else "stale"


def state(config_dir: Path) -> str:
    """``missing``, ``foreign`` (not dotbrain's), ``stale``, or ``current``, for the plugin file
    and the packaged skills together."""
    with resource_loader.opencode_plugin() as source:
        states = {_file_state(config_dir, source), owned_copy.state(packaged_dir(config_dir), SKILL_FILES)}
    if "foreign" in states:
        return "foreign"
    return states.pop() if len(states) == 1 else "stale"


def foreign_entry(config_dir: Path) -> Path | None:
    """The delivery path held by something dotbrain did not create, if any."""
    with resource_loader.opencode_plugin() as source:
        if _file_state(config_dir, source) == "foreign":
            return plugin_file(config_dir)
        if owned_copy.state(packaged_dir(config_dir), SKILL_FILES) == "foreign":
            return packaged_dir(config_dir)
    return None


def deliver(config_dir: Path, *, run=None) -> LinkResult:
    """Install or update dotbrain's plugin file and packaged skills; ``run`` is unused."""
    result = LinkResult()
    foreign = foreign_entry(config_dir)
    if foreign is not None:
        result.warnings.append(f"{foreign} exists and was not created by dotbrain; skipping")
        return result
    with resource_loader.opencode_plugin() as source:
        if owned_copy.state(packaged_dir(config_dir), SKILL_FILES) != "current":
            owned_copy.install(packaged_dir(config_dir), SKILL_FILES)
            result.linked.append("opencode/dotbrain/packaged")
        if _file_state(config_dir, source) != "current":
            _write_atomic(plugin_file(config_dir), source.read_bytes())
            result.linked.append(f"opencode/plugins/{PLUGIN_FILE}")
    return result


def duplicate_skills(config_dir: Path, user_home: Path) -> list[tuple[str, Path]]:
    """``(skill, other copy)`` for each dotbrain skill OpenCode also finds, under the same name, in a
    directory the user keeps, as a different file; OpenCode then loads one of the two at random."""
    ours: dict[str, set[Path]] = {}
    for skill in skill_index(_global_roots(config_dir)):
        if skill["name"] is not None:
            ours.setdefault(skill["name"], set()).add(Path(skill["file"]).resolve())
    # The folders OpenCode scans besides dotbrain's: its config's own, without hidden folders, and
    # the Claude and agents homes, with them.
    others = (skill_index([Path(config_dir) / name for name in FOREIGN_SKILL_ROOTS])
              + skill_index([Path(user_home) / name for name in USER_SKILL_ROOTS], dot=True))
    return [(skill["name"], Path(skill["file"]).parent) for skill in others
            if skill["name"] in ours and Path(skill["file"]).resolve() not in ours[skill["name"]]]
