"""OpenCode delivery: an owned plugin file and owned skill directories in the OpenCode config.

OpenCode loads every ``plugins/*.js`` file in its config directory (``$XDG_CONFIG_HOME/opencode``,
by default ``~/.config/opencode``). Dotbrain copies its plugin file there, the packaged skills to
``dotbrain/packaged/`` and the operator's global skill links to ``dotbrain/skills/``; OpenCode
scans neither on its own, and the plugin adds both to ``skills.paths``. Dotbrain replaces only
files it marked as its own and never edits the OpenCode configuration.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotbrain import hermes, resource_loader
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


def _file_owned(config_dir: Path) -> bool:
    target = plugin_file(config_dir)
    if target.is_symlink() or not target.is_file():
        return False
    with target.open("rb") as handle:
        return handle.read(len(HEADER)) == HEADER


def owned(config_dir: Path) -> bool:
    """Whether any of dotbrain's delivery is present, so later runs keep it current."""
    return _file_owned(config_dir) or hermes.tree_owned(packaged_dir(config_dir))


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
    with resource_loader.opencode_plugin() as source, resource_loader.hermes_plugin() as tree:
        states = {_file_state(config_dir, source), hermes.tree_state(packaged_dir(config_dir), tree, SKILL_FILES)}
    if "foreign" in states:
        return "foreign"
    return states.pop() if len(states) == 1 else "stale"


def foreign_entry(config_dir: Path) -> Path | None:
    """The delivery path held by something dotbrain did not create, if any."""
    with resource_loader.opencode_plugin() as source, resource_loader.hermes_plugin() as tree:
        if _file_state(config_dir, source) == "foreign":
            return plugin_file(config_dir)
        if hermes.tree_state(packaged_dir(config_dir), tree, SKILL_FILES) == "foreign":
            return packaged_dir(config_dir)
    return None


def deliver(config_dir: Path, *, run=None) -> LinkResult:
    """Install or update dotbrain's plugin file and packaged skills; ``run`` is unused."""
    result = LinkResult()
    foreign = foreign_entry(config_dir)
    if foreign is not None:
        result.warnings.append(f"{foreign} exists and was not created by dotbrain; skipping")
        return result
    with resource_loader.opencode_plugin() as source, resource_loader.hermes_plugin() as tree:
        if hermes.tree_state(packaged_dir(config_dir), tree, SKILL_FILES) != "current":
            hermes.replace_tree(packaged_dir(config_dir), tree, SKILL_FILES)
            result.linked.append("opencode/dotbrain/packaged")
        if _file_state(config_dir, source) != "current":
            target = plugin_file(config_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Written beside the target and moved over it, so OpenCode never loads half a file.
            handle, staging = tempfile.mkstemp(dir=target.parent, prefix=f".{PLUGIN_FILE}-", suffix=".tmp")
            try:
                with os.fdopen(handle, "wb") as out:
                    out.write(source.read_bytes())
                os.replace(staging, target)
            finally:
                if os.path.exists(staging):
                    os.unlink(staging)
            result.linked.append(f"opencode/plugins/{PLUGIN_FILE}")
    return result


def duplicate_skills(config_dir: Path, user_home: Path) -> list[tuple[str, Path]]:
    """``(skill, other copy)`` for each dotbrain skill OpenCode also finds in a directory the user
    keeps, as a different file; OpenCode then loads one of the two at random."""
    ours: dict[str, Path] = {}
    for root in (packaged_dir(config_dir) / "skills", skills_dir(config_dir)):
        if root.is_dir():
            for entry in sorted(root.iterdir()):
                if (entry / "SKILL.md").is_file():
                    ours.setdefault(entry.name, (entry / "SKILL.md").resolve())
    roots = [Path(config_dir) / name for name in FOREIGN_SKILL_ROOTS] + [Path(user_home) / name for name in USER_SKILL_ROOTS]
    found = []
    # ponytail: matches top-level skill directories by name; OpenCode keys on the frontmatter name.
    for root in roots:
        for name, mine in ours.items():
            other = root / name / "SKILL.md"
            if other.is_file() and other.resolve() != mine:
                found.append((name, root / name))
    return found
