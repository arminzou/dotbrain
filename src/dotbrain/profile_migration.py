"""One-time migration of the retired global settings files into ``config.yaml`` version 4.

``skills/skills.yaml`` and ``agents/agents.yaml`` are merged into ``config.yaml``, backed up and
removed, and the ``agents/`` source directory becomes ``subagents/``. Every check runs in
:func:`plan` before :func:`apply` writes anything, so a refused migration changes no file.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dotbrain import adopter_repos, config, paths, resource_loader, runtimes, skills, subagents

CONFIG_VERSION = 4
SKILLS_FILE, AGENTS_FILE = paths.LEGACY_GLOBAL_FILES
_KNOWN_KEYS = {SKILLS_FILE: {"version", "targets", "profiles", "global_extra", "extra"},
               AGENTS_FILE: {"version", "targets", "global"}}


@dataclass
class Plan:
    originals: dict[str, bytes]  # data-root relative path -> bytes, including config.yaml when it exists
    config_updated: bytes | None  # None when no legacy file needs merging
    rename_dir: bool  # move agents/ to subagents/
    remove_dir: bool  # agents/ holds nothing beyond empty folders and subagents/ already exists
    reports: list[str] = field(default_factory=list)


def _refuse(location: str, reason: str) -> ValueError:
    return ValueError(f"{location}: {reason}; global settings migration stopped and no file was changed")


def _read(path: Path, location: str) -> dict:
    """Parse a mapping, refusing layouts whose meaning a plain merge could change."""
    text = path.read_text(encoding="utf-8")
    try:
        tokens = list(yaml.scan(text))
        node = yaml.compose(text)
    except yaml.YAMLError as exc:
        raise _refuse(location, f"unparseable YAML ({exc.__class__.__name__})") from exc
    if any(isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken))
           for token in tokens):
        raise _refuse(location, "anchors, aliases, merge keys and tags are ambiguous")
    if node is None or (isinstance(node, yaml.ScalarNode) and node.tag.endswith(":null")):
        return {}
    if not isinstance(node, yaml.MappingNode):
        raise _refuse(location, "expected a YAML mapping")
    keys = [key.value for key, _ in node.value]
    if len(set(keys)) != len(keys):
        raise _refuse(location, "duplicate keys are ambiguous")
    return yaml.safe_load(text) or {}


def _convert_targets(data: dict, kind: str, location: str, user_home: Path,
                     profiles: dict[str, list[str]], reports: list[str]) -> None:
    """Drop targets equal to the default home; turn custom ones into profiles."""
    targets = data.get("targets") or {}
    if not isinstance(targets, dict):
        raise _refuse(location, "targets must be a mapping of runtime -> destination")
    for key, value in targets.items():
        rt = runtimes.find(str(key))
        if not isinstance(value, str) or not value.strip():
            raise _refuse(location, f"targets.{key} must be a destination path")
        if rt is None or rt.key not in ("claude-code", "codex"):
            raise _refuse(location, f"targets.{key} has no profile equivalent; remove it")
        default = runtimes.user_dir(rt, user_home) / kind
        if adopter_repos.expand_path(value.replace("\\", "/"), home=user_home).resolve() == default.resolve():
            reports.append(f"{location}: dropped targets.{key}, which names the default home")
            continue
        normalized = value.replace("\\", "/").rstrip("/")
        home, _, leaf = normalized.rpartition("/")
        if leaf != kind or not home:
            raise _refuse(location, f"targets.{key} does not end in /{kind}, so no runtime home matches it")
        homes = profiles.setdefault(rt.key, [])
        if home not in homes:
            homes.append(home)
        reports.append(f"{location}: converted targets.{key} to profiles.{rt.key}: [{home}]; "
                       "a profile receives both skills and subagents")


def _set_version(text: str) -> str:
    line = f"version: {CONFIG_VERSION}"
    updated, count = re.subn(r"^version:[^\n]*$", line, text, count=1, flags=re.MULTILINE)
    return updated if count else line + "\n" + text


def plan(root: Path, user_home: Path) -> Plan | None:
    """Validate every retired file and compute the merged ``config.yaml``; None when nothing remains."""
    root = Path(root)
    legacy_dir = paths.confined_path(root, paths.LEGACY_SUBAGENTS_DIR)
    present = [name for name in paths.LEGACY_GLOBAL_FILES if paths.confined_path(root, name).is_file()]
    if not present and not legacy_dir.is_dir():
        return None

    originals: dict[str, bytes] = {}
    reports: list[str] = []
    updated = None
    if present:
        loaded = {}
        for name in present:
            path = root / name
            originals[name] = path.read_bytes()
            loaded[name] = data = _read(path, name)
            unknown = sorted(str(key) for key in data if key not in _KNOWN_KEYS[name])
            if unknown:
                raise _refuse(name, f"unknown keys {', '.join(unknown)} cannot be carried into config.yaml")
        skill_data = loaded.get(SKILLS_FILE, {})
        agent_data = loaded.get(AGENTS_FILE, {})
        if "global_extra" in skill_data and "extra" in skill_data:
            raise _refuse(SKILLS_FILE, "both global_extra and extra are set")

        try:
            profiles = {key: list(homes) for key, homes in config.parse_profiles(skill_data.get("profiles"), SKILLS_FILE).items()}
        except ValueError as exc:
            raise _refuse(SKILLS_FILE, str(exc).removeprefix(f"{SKILLS_FILE}: ")) from exc
        _convert_targets(skill_data, "skills", SKILLS_FILE, user_home, profiles, reports)
        _convert_targets(agent_data, "agents", AGENTS_FILE, user_home, profiles, reports)
        names = skills._clean(agent_data.get("global"))
        dropped = [name for name in names if subagents.is_packaged(name)]
        if dropped:
            reports.append(f"{AGENTS_FILE}: dropped packaged subagents {', '.join(dropped)} from global; "
                           "packaged subagents are selected per project in project.yaml")
        merged = {
            "profiles": profiles,
            "skills": list(skills._clean(skill_data.get("global_extra", skill_data.get("extra")))),
            "subagents": [name for name in names if name not in dropped],
        }

        config_path = paths.confined_path(root, "config.yaml")
        if config_path.is_file():
            originals["config.yaml"] = config_path.read_bytes()
            text = originals["config.yaml"].decode("utf-8")
            current = _read(config_path, "config.yaml")
        else:
            text = resource_loader.resource("config.yaml").read_text(encoding="utf-8")
            current = yaml.safe_load(text) or {}
        missing = {}
        for key, value in merged.items():
            if key not in current:
                missing[key] = value
            elif current[key] != value and value:
                raise _refuse("config.yaml", f"{key} conflicts with the value in the retired files")
        expected = {**current, "version": CONFIG_VERSION, **missing}
        text = _set_version(text)
        if missing:
            text += ("" if not text or text.endswith("\n") else "\n") + yaml.safe_dump(
                missing, sort_keys=False, default_flow_style=False)
        if yaml.safe_load(text) != expected:
            raise _refuse("config.yaml", "this YAML layout cannot be merged safely")
        updated = text.encode("utf-8")

    rename_dir = remove_dir = False
    if legacy_dir.is_dir():
        leftovers = [p for p in legacy_dir.rglob("*") if not p.is_dir() and p != root / AGENTS_FILE]
        if not (root / paths.SUBAGENTS_DIR).exists():
            rename_dir = True
        elif leftovers:
            raise _refuse(paths.LEGACY_SUBAGENTS_DIR, f"both {paths.LEGACY_SUBAGENTS_DIR}/ and "
                          f"{paths.SUBAGENTS_DIR}/ hold files; move custom subagent sources into {paths.SUBAGENTS_DIR}/")
        else:
            remove_dir = True
    return Plan(originals, updated, rename_dir, remove_dir, reports)


def apply(root: Path, migration: Plan) -> list[str]:
    """Back up the originals, write the merged ``config.yaml``, then retire the old files."""
    root = Path(root)
    for name, original in migration.originals.items():
        if (root / name).read_bytes() != original:
            raise ValueError(f"{root / name}: changed during migration; rerun dotbrain bootstrap")
    logs = list(migration.reports)
    if migration.originals:
        backup_root = paths.confined_path(root, ".cache/config-backups")
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix="global-settings-", dir=backup_root))
        for name, original in migration.originals.items():
            (backup / name).parent.mkdir(parents=True, exist_ok=True)
            (backup / name).write_bytes(original)
    if migration.config_updated is not None:
        target = root / "config.yaml"
        with tempfile.NamedTemporaryFile(prefix=".config-", suffix=".tmp", dir=root, delete=False) as stream:
            staged = Path(stream.name)
            stream.write(migration.config_updated)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_file():
            shutil.copymode(target, staged)
        os.replace(staged, target)
        for name in paths.LEGACY_GLOBAL_FILES:
            if name in migration.originals:
                (root / name).unlink()
        retired = ", ".join(name for name in paths.LEGACY_GLOBAL_FILES if name in migration.originals)
        logs.append(f"migrated {retired} into config.yaml version {CONFIG_VERSION}; originals saved to {backup}")
    legacy_dir = root / paths.LEGACY_SUBAGENTS_DIR
    if migration.rename_dir:
        os.replace(legacy_dir, root / paths.SUBAGENTS_DIR)
        logs.append(f"renamed {paths.LEGACY_SUBAGENTS_DIR}/ to {paths.SUBAGENTS_DIR}/")
    elif migration.remove_dir:
        shutil.rmtree(legacy_dir)
        logs.append(f"removed empty {paths.LEGACY_SUBAGENTS_DIR}/")
    return logs
