"""Conservative, comment-preserving cleanup of legacy global skill destinations."""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from dotbrain import assets, paths, runtimes, skills, subagents


@dataclass
class Plan:
    path: Path
    original: bytes
    updated: bytes


def _updated_text(text: str, data: dict) -> str:
    node = yaml.compose(text)
    if isinstance(node, yaml.ScalarNode) and node.tag == "tag:yaml.org,2002:null" and not node.value:
        node = None
    if node is not None and not isinstance(node, yaml.MappingNode):
        raise ValueError("skills/skills.yaml: expected a YAML mapping")
    newline = "\r\n" if "\r\n" in text else "\n"
    edits: list[tuple[int, int, str]] = []
    if "profiles" not in data:
        if node is None:
            position = next((event.start_mark.index for event in yaml.parse(text)
                             if isinstance(event, yaml.events.DocumentEndEvent)), len(text))
            prefix = newline if position and text[position - 1] != "\n" else ""
            edits.append((position, position, prefix + "profiles: {}" + newline))
        elif node.flow_style:
            position = node.value[0][0].start_mark.index if node.value else text.index("{") + 1
            edits.append((position, position, "profiles: {}" + (", " if node.value else "")))
        else:
            position = node.end_mark.index
            indent = " " * node.value[0][0].start_mark.column
            prefix = "" if not position or text[position - 1] == "\n" else newline
            edits.append((position, position, prefix + indent + "profiles: {}" + newline))

    # Anchors, merge keys and flow mappings need a round-trip editor; retain their targets.
    anchored = any(isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken))
                   for token in yaml.scan(text))
    target_nodes = [(key, value) for key, value in node.value if key.value == "targets"] if node else []
    expected = dict(data)
    expected.setdefault("profiles", {})
    if (not anchored and node and not node.flow_style and len(target_nodes) == 1
            and isinstance(target_nodes[0][1], yaml.MappingNode) and not target_nodes[0][1].flow_style):
        key, targets = target_nodes[0]
        keys = [name.value for name, _ in targets.value]
        removed = []
        if len(set(keys)) == len(keys):
            defaults = runtimes.global_targets("skills")
            for name, value in targets.value:
                if (name.value in ("claude-code", "codex")
                        and value.value.replace("\\", "/") == defaults[name.value]
                        and name.start_mark.line == value.end_mark.line):
                    edits.append((name.start_mark.index, value.end_mark.index, ""))
                    removed.append(name.value)
        if removed:
            remaining = {name: value for name, value in data["targets"].items() if name not in removed}
            if remaining:
                expected["targets"] = remaining
            else:
                del expected["targets"]
                # Remove only the header's YAML tokens, leaving all comments in place.
                end = text.index(":", key.end_mark.index) + 1
                edits.append((key.start_mark.index, end, ""))

    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    if yaml.safe_load(text) != expected:
        raise ValueError("skills/skills.yaml: cannot safely migrate this YAML layout; add profiles: {} manually")
    return text


def plan(root: Path, user_home: Path) -> Plan | None:
    """Validate both asset configurations before proposing any config mutation."""
    path = paths.confined_path(root, "skills/skills.yaml")
    paths.confined_path(root, "agents/agents.yaml")
    skill_config = skills.load_global_config(path)
    if not path.is_file():
        return None
    original = path.read_bytes()
    text = original.decode("utf-8")
    data = yaml.safe_load(text) or {}
    updated = _updated_text(text, data).encode("utf-8")
    if updated == original:
        return None
    agent_config = subagents.load_global_config(root)
    errors: list[str] = []
    for kind, cfg in (("skills", skill_config), ("agents", agent_config)):
        assets.global_targets(cfg.targets, runtimes.select("all"), kind, user_home, explicit=False,
                              errors=errors, dotbrain_home=root, profiles=skill_config.profiles)
    if errors:
        raise ValueError("; ".join(errors))
    skills.resolve_selection(root, skill_config.global_extra)
    errors = subagents.validate_selection(root, agent_config.global_names,
                                          tuple(rt.key for rt in runtimes.select("all") if rt.subagents))
    if errors:
        raise ValueError("; ".join(errors))
    return Plan(path.resolve(), original, updated)


def apply(root: Path, migration: Plan) -> str:
    """Keep the original bytes for recovery and atomically replace the validated file."""
    backup_dir = paths.confined_path(root, ".cache/config-backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="skills-", suffix=".yaml", dir=backup_dir, delete=False) as backup:
        backup.write(migration.original)
        backup.flush()
        os.fsync(backup.fileno())
    staged = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".skills-", suffix=".tmp", dir=migration.path.parent,
                                         delete=False) as stream:
            staged = Path(stream.name)
            stream.write(migration.updated)
            stream.flush()
            os.fsync(stream.fileno())
        shutil.copymode(migration.path, staged)
        if migration.path.read_bytes() != migration.original:
            raise ValueError(f"{migration.path}: changed during migration; rerun dotbrain bootstrap")
        os.replace(staged, migration.path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return f"migrated skills/skills.yaml runtime profiles; original saved to {backup.name}"
