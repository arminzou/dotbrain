"""Operator skill config and symlink linking."""

from __future__ import annotations

import os
import shutil
import stat
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml

from dotbrain import paths, runtimes


@dataclass
class GlobalConfig:
    """Operator-configurable skill-link settings."""

    targets: dict[str, str] = field(default_factory=lambda: runtimes.global_targets("skills"))
    global_extra: tuple[str, ...] = ()
    profiles: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class LinkResult:
    """Result of creating/pruning skill links."""

    linked: list[str] = field(default_factory=list)
    pruned: list[str] = field(default_factory=list)
    stashed: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)  # non-fatal: reported, but the command still succeeds


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
        value = value.strip()
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

    merged_targets = runtimes.global_targets("skills")
    merged_targets.update(targets)
    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict) or not all(
        k in ("claude-code", "codex") and isinstance(v, list)
        and all(isinstance(home, str) and home.strip() for home in v)
        for k, v in profiles.items()
    ):
        raise ValueError(f"{path}: profiles must map claude-code or codex to lists of runtime homes")
    return GlobalConfig(
        targets=merged_targets,
        global_extra=_clean(data.get("global_extra", data.get("extra"))),
        profiles=profiles,
    )


def render_global_config(
    global_extra: Iterable[str],
) -> str:
    """Render the optional operator-owned skill-link config."""

    lines = [
        "version: 1",
        "# Operator skill-link config — your global skills, linked into every agent",
        "# session. List global skills under global_extra.",
        "profiles: {}",
    ]
    extra = _clean(global_extra)
    if extra:
        lines.append("global_extra:")
        for skill in extra:
            lines.append(f"  - {skill}")
    else:
        lines.append("global_extra: []")
    return "\n".join(lines) + "\n"


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
    except (OSError, RuntimeError):
        return False


def _resolve_skill_source(dotbrain_home: Path, skill_path: str) -> Path | None:
    skills_root = paths.confined_path(Path(dotbrain_home), "skills")
    private_src = paths.confined_path(skills_root, skill_path)
    return private_src if private_src.is_dir() else None


def resolve_selection(dotbrain_home: Path, entries: Iterable[str]) -> tuple[str, ...]:
    """Expand declarations to a complete, confined, collision-free skill set."""
    root = paths.confined_path(Path(dotbrain_home), "skills")
    effective: dict[Path, str] = {}
    for entry in sorted(_clean(list(entries))):
        source = paths.confined_path(root, entry)
        if not source.exists():
            raise ValueError(f"skill not found: {entry}")
        if not source.is_dir():
            raise ValueError(f"skill selection is not a directory: {entry}")
        marker = paths.confined_path(root, str(Path(entry) / "SKILL.md"))
        candidates = [entry] if marker.is_file() else [str(Path(entry) / child) for child in discover_skills(source)]
        if not candidates:
            raise ValueError(f"skill folder contains no skills: {entry}")
        for candidate in candidates:
            directory = paths.confined_path(root, candidate)
            marker = paths.confined_path(root, str(Path(candidate) / "SKILL.md"))
            if not directory.is_dir() or not marker.is_file():
                raise ValueError(f"skill has no readable SKILL.md: {candidate}")
            physical = directory.resolve()
            effective.setdefault(physical, physical.relative_to(root.resolve()).as_posix())
    leaves: dict[str, str] = {}
    for candidate in sorted(effective.values()):
        leaf = Path(candidate).name.casefold()
        if leaf in leaves and leaves[leaf] != candidate:
            raise ValueError(f"skill destination collision: {leaves[leaf]} and {candidate}")
        leaves[leaf] = candidate
    return tuple(sorted(effective.values()))


def _remove_legacy_skill_cache(dotbrain_home: Path) -> None:
    cache = paths.confined_path(dotbrain_home, ".cache/skills")
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
    owned_roots: Sequence[Path] = (),
    cleanup_cache: bool = True,
) -> LinkResult:
    """Link skill paths into an agent runtime skills directory."""

    dotbrain_home = Path(dotbrain_home)
    skills_dir = Path(skills_dir)
    # Validate the complete source selection before creating a destination,
    # deleting the legacy cache, or linking/pruning any workspace entries.
    try:
        selected = resolve_selection(dotbrain_home, skill_paths)
        paths.confined_path(dotbrain_home, ".cache/skills")
    except ValueError as exc:
        return LinkResult(warnings=[str(exc)])
    sources = [(skill_path, _resolve_skill_source(dotbrain_home, skill_path)) for skill_path in selected]
    skills_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{label}/" if label else ""
    result = LinkResult()
    wanted: set[str] = set()
    if cleanup_cache:
        _remove_legacy_skill_cache(dotbrain_home)
    cache_root = (dotbrain_home / ".cache" / "skills").resolve()
    private_root = (dotbrain_home / "skills").resolve()

    for skill_path, src in sources:
        if src is None or not src.is_dir():
            result.warnings.append(f"skill not found: {skill_path}")
            continue

        dest = skills_dir / Path(skill_path).name
        wanted.add(os.path.normcase(dest.name))
        owned = dest.is_symlink() and (
            any(_points_into(dest, root) for root in (private_root, cache_root, *owned_roots))
        )
        if owned and dest.resolve() == src.resolve():
            continue
        if preserve_collisions and (dest.exists() or dest.is_symlink()) and not owned:
            result.warnings.append(f"{dest} exists and was not created by dotbrain; skipping")
            continue
        if dest.exists() and not dest.is_symlink():
            result.stashed.append(stash_collision(dest))
        if not owned and (dest.is_symlink() or dest.exists()):
            dest.unlink()
        # Build a replacement before changing an owned link, so failed delivery retains it.
        staged = skills_dir / f".{dest.name}.{uuid.uuid4().hex}.tmp" if owned else dest
        try:
            staged.symlink_to(os.path.relpath(src, skills_dir), target_is_directory=True)
            if owned:
                # Windows cannot replace a directory symlink in place. Keep a recoverable
                # link until promotion succeeds, on every platform.
                backup = skills_dir / f".{dest.name}.{uuid.uuid4().hex}.backup"
                dest.rename(backup)
                try:
                    os.replace(staged, dest)
                except OSError:
                    backup.rename(dest)
                    raise
                else:
                    backup.unlink()
        except OSError as exc:
            message = paths.symlink_privilege_message(exc)
            if message is None:
                raise
            raise RuntimeError(f"{dest}: {message}") from exc
        finally:
            if owned and staged.is_symlink():
                staged.unlink()
        result.linked.append(f"{prefix}{dest.name}")

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_symlink() or os.path.normcase(entry.name) in wanted:
            continue
        if prune_owned_only and not any(
            _points_into(entry, root) for root in (private_root, cache_root, *owned_roots)
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
    try:
        skill_paths = resolve_selection(dotbrain_home, skill_paths)
        paths.confined_path(dotbrain_home, ".cache/skills")
    except ValueError as exc:
        result.warnings.append(str(exc))
        return result
    for workspace in workspaces:
        workspace_dir = workspace_dirs.get(workspace) if workspace_dirs else None
        base = (workspace_dir or brainspace / workspace).parent
        rt = runtimes.for_workspace(workspace)
        skills_dir = base / rt.skill_path
        # A shared skill directory is never an ownership claim on its parent or receiver.
        conflict = project_directory_conflict(base, rt.skill_path)
        if conflict:
            result.warnings.append(conflict)
            continue
        ws_result = link_into(
            dotbrain_home,
            skills_dir,
            skill_paths,
            label=rt.skill_path,
            prune_owned_only=True,
            preserve_collisions=True,
            # A project/runtime cannot retire a shared cache that preserved legacy
            # links in another runtime or checkout may still need.
            cleanup_cache=False,
        )
        if rt.name == "codex":
            _prune_codex_legacy(dotbrain_home, base, skills_dir, skill_paths, ws_result)
        result.linked += ws_result.linked
        result.pruned += ws_result.pruned
        result.stashed += ws_result.stashed
        result.warnings += ws_result.warnings
    return result


def _is_junction(directory: Path) -> bool:
    """Recognize Windows junctions on every supported Python, including 3.11."""
    if os.name != "nt":
        return False
    try:
        return directory.lstat().st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    except OSError:
        return False


def project_directory_conflict(base: Path, relative: str) -> str | None:
    """Reject linked parents as well as linked receivers before any project writes."""
    directory = base
    for part in Path(relative).parts:
        directory /= part
        if (directory.is_symlink() or _is_junction(directory)
                or (directory.exists() and not directory.is_dir())):
            return f"{directory}: foreign asset directory conflicts with delivery"
    return None


def codex_legacy_entries(dotbrain_home: Path, base: Path) -> tuple[list[Path], list[str]]:
    """Classify legacy entries using the same target-root ownership as skill delivery."""
    legacy = base / ".codex/skills"
    conflict = project_directory_conflict(base, ".codex/skills")
    if conflict:
        return [], [conflict]
    owned, warnings = [], []
    roots = (dotbrain_home / "skills", dotbrain_home / ".cache/skills")
    if legacy.is_dir():
        for entry in sorted(legacy.iterdir()):
            if entry.is_symlink() and any(_points_into(entry, root) for root in roots):
                owned.append(entry)
            else:
                warnings.append(f"{entry}: legacy skill ownership is ambiguous; leaving it unchanged")
    return owned, warnings


def _prune_codex_legacy(home: Path, base: Path, destination: Path,
                       selection: Sequence[str], result: LinkResult) -> None:
    owned, warnings = codex_legacy_entries(home, base)
    result.warnings.extend(warnings)
    selected = {os.path.normcase(Path(name).name): (Path(name).name, _resolve_skill_source(home, name))
                for name in resolve_selection(home, selection)}
    for entry in owned:
        name, source = selected.get(os.path.normcase(entry.name), (entry.name, None))
        replacement = destination / name
        # Selected links leave the legacy discovery path only after a verified delivery.
        if source is not None and not (replacement.is_symlink() and _points_into(replacement, source)
                                       and replacement.resolve() == source.resolve()):
            result.warnings.append(f"{entry}: replacement was not delivered; leaving legacy skill unchanged")
            continue
        entry.unlink()
        result.pruned.append(entry.relative_to(base).as_posix())
