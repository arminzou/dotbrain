"""Operator skill config and symlink linking."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml

from dotbrain import paths

DEFAULT_TARGETS: dict[str, str] = {
    "claude-code": "~/.claude/skills",
    "codex": "~/.codex/skills",
}
@dataclass
class GlobalConfig:
    """Operator-configurable skill-link settings."""

    targets: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_TARGETS))
    global_extra: tuple[str, ...] = ()


@dataclass
class LinkResult:
    """Result of creating/pruning skill links."""

    linked: list[str] = field(default_factory=list)
    pruned: list[str] = field(default_factory=list)
    stashed: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _clean(values: object, *, exclude: Iterable[str] = ()) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple)):
        return ()

    excluded = set(exclude)
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        value = value.strip().strip("/")
        if not value or value in excluded or value in seen:
            continue
        out.append(value)
        seen.add(value)
    return tuple(out)


def discover_skills(skills_root: Path) -> list[str]:
    """Return skill paths under a skills root."""

    skills_root = Path(skills_root)
    if not skills_root.is_dir():
        return []

    out: list[str] = []
    for skill_md in skills_root.rglob("SKILL.md"):
        if "node_modules" in skill_md.parts:
            continue
        out.append(skill_md.parent.relative_to(skills_root).as_posix())
    return sorted(out)


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data


def load_global_config(path: Path) -> GlobalConfig:
    """Parse optional operator skill-link config."""

    path = Path(path)
    if not path.is_file():
        return GlobalConfig()

    data = _read_yaml_mapping(path)
    targets = data.get("targets") or {}
    if not isinstance(targets, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in targets.items()
    ):
        raise ValueError(f"{path}: targets must be a mapping of runtime -> destination")

    merged_targets = dict(DEFAULT_TARGETS)
    merged_targets.update(targets)
    return GlobalConfig(
        targets=merged_targets,
        global_extra=_clean(data.get("global_extra", data.get("extra"))),
    )


def render_global_config(
    targets: dict[str, str],
    global_extra: Iterable[str],
) -> str:
    """Render the optional operator-owned skill-link config."""

    lines = [
        "version: 1",
        "# Operator skill-link config — your global skills, linked into every agent",
        "# session. List global skills under global_extra.",
        "targets:",
    ]
    for key, value in targets.items():
        lines.append(f"  {key}: {value}")
    extra = _clean(global_extra)
    if extra:
        lines.append("global_extra:")
        for skill in extra:
            lines.append(f"  - {skill}")
    else:
        lines.append("global_extra: []")
    return "\n".join(lines) + "\n"


def reconcile_global_config(path: Path) -> GlobalConfig:
    """Normalize optional operator config when present."""

    path = Path(path)
    config = load_global_config(path)
    if path.is_file():
        desired = render_global_config(
            config.targets,
            config.global_extra,
        )
        if path.read_text(encoding="utf-8") != desired:
            path.write_text(desired, encoding="utf-8", newline="\n")
    return config


def project_link_set(extras: Iterable[str]) -> tuple[str, ...]:
    """Return the operator's deduplicated per-project skill selection."""

    return _clean(extras)


def stash_collision(target: Path) -> Path:
    tmp = target.parent / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    moved = tmp / f"{target.name}.{int(time.time())}"
    target.rename(moved)
    return moved


def _points_into(link: Path, root: Path) -> bool:
    try:
        return link.resolve().is_relative_to(root.resolve())
    except FileNotFoundError:
        return False


def _resolve_skill_source(dotbrain_home: Path, skill_path: str) -> Path | None:
    private_src = dotbrain_home / "skills" / skill_path
    return private_src if private_src.is_dir() else None


def _remove_legacy_skill_cache(dotbrain_home: Path) -> None:
    cache = Path(dotbrain_home) / ".cache" / "skills"
    if cache.is_dir() and not cache.is_symlink():
        shutil.rmtree(cache)
    elif cache.exists() or cache.is_symlink():
        cache.unlink()


def link_into(
    dotbrain_home: Path,
    skills_dir: Path,
    skill_paths: Sequence[str],
    *,
    label: str = "",
    prune_owned_only: bool = False,
    preserve_collisions: bool = False,
) -> LinkResult:
    """Link skill paths into an agent runtime skills directory."""

    dotbrain_home = Path(dotbrain_home)
    skills_dir = Path(skills_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{label}/" if label else ""
    result = LinkResult()
    wanted: set[str] = set()
    _remove_legacy_skill_cache(dotbrain_home)
    cache_root = (dotbrain_home / ".cache" / "skills").resolve()
    private_root = (dotbrain_home / "skills").resolve()

    for skill_path in skill_paths:
        src = _resolve_skill_source(dotbrain_home, skill_path)
        if src is None or not src.is_dir():
            result.warnings.append(f"skill not found: {skill_path}")
            continue

        dest = skills_dir / Path(skill_path).name
        wanted.add(dest.name)
        owned = dest.is_symlink() and (
            _points_into(dest, private_root) or _points_into(dest, cache_root)
        )
        if preserve_collisions and (dest.exists() or dest.is_symlink()) and not owned:
            result.warnings.append(f"{dest} exists and was not created by dotbrain; skipping")
            continue
        if dest.exists() and not dest.is_symlink():
            result.stashed.append(stash_collision(dest))
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        try:
            dest.symlink_to(os.path.relpath(src, skills_dir), target_is_directory=True)
        except OSError as exc:
            message = paths.symlink_privilege_message(exc)
            if message is None:
                raise
            raise RuntimeError(f"{dest}: {message}") from exc
        result.linked.append(f"{prefix}{dest.name}")

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_symlink() or entry.name in wanted:
            continue
        if prune_owned_only and not (
            _points_into(entry, private_root) or _points_into(entry, cache_root)
        ):
            continue
        entry.unlink()
        result.pruned.append(f"{prefix}{entry.name}")

    return result


def link_project(
    dotbrain_home: Path,
    brainspace: Path,
    workspaces: Sequence[str],
    skill_paths: Sequence[str],
    *,
    workspace_dirs: Mapping[str, Path] | None = None,
) -> LinkResult:
    brainspace = Path(brainspace)
    result = LinkResult()
    for workspace in workspaces:
        workspace_dir = workspace_dirs.get(workspace) if workspace_dirs else None
        skills_dir = (workspace_dir or brainspace / workspace) / "skills"
        ws_result = link_into(
            dotbrain_home,
            skills_dir,
            skill_paths,
            label=f"{workspace}/skills",
            prune_owned_only=True,
            preserve_collisions=True,
        )
        result.linked += ws_result.linked
        result.pruned += ws_result.pruned
        result.stashed += ws_result.stashed
        result.warnings += ws_result.warnings
    return result
