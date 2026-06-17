"""Skill config (packaged required core + operator extras) and symlink linking."""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import yaml

from dotbrain import paths, resource_loader


def _normalize(values: object) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        value = value.strip().strip("/")
        if value and value not in seen:
            out.append(value)
            seen.add(value)
    return tuple(out)


def _required_core() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Read the brain-coupled required core from the packaged skills.yaml.

    Product-owned, read-only data: the tool always force-wires these regardless
    of operator config. Read fresh from the package so new releases reach every
    adopter without a data-root migration.
    """
    src = resource_loader.resource("skills.yaml")
    data = yaml.safe_load(src.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError("packaged skills.yaml: expected a YAML mapping")
    return _normalize(data.get("global_required")), _normalize(data.get("project_required"))


# Brain-coupled required core (force-wired). Operators add extras on top; they
# cannot remove these. See resources/skills.yaml.
GLOBAL_BASELINE, PROJECT_BASELINE = _required_core()

DEFAULT_TARGETS: dict[str, str] = {
    "claude-code": "~/.claude/skills",
    "codex": "~/.codex/skills",
}
BUNDLED_SKILL_PREFIXES: tuple[str, ...] = ("brain/",)


@dataclass
class GlobalConfig:
    """Operator-configurable skill-link settings.

    Product baselines are code-owned constants. This config carries runtime
    targets and user/private global extras only.
    """

    targets: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_TARGETS))
    project_baseline: tuple[str, ...] = PROJECT_BASELINE
    global_extra: tuple[str, ...] = ()

    @property
    def linked(self) -> tuple[str, ...]:
        return GLOBAL_BASELINE + self.global_extra


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
        out.append(str(skill_md.parent.relative_to(skills_root)))
    return sorted(out)


def _read_yaml_mapping(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data


def load_global_config(path: Path) -> GlobalConfig:
    """Parse optional operator skill-link config.

    Missing config is valid: product baselines and default runtime targets come
    from code-owned defaults.
    """

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
        project_baseline=PROJECT_BASELINE,
        global_extra=_clean(
            data.get("global_extra", data.get("extra")),
            exclude=GLOBAL_BASELINE + PROJECT_BASELINE,
        ),
    )


def render_global_config(
    targets: dict[str, str],
    global_extra: Iterable[str],
    project_baseline: Iterable[str] = PROJECT_BASELINE,
) -> str:
    """Render the optional operator-owned skill-link config."""

    lines = [
        "version: 1",
        "# Operator skill-link config — your global skills, linked into every agent",
        "# session.  The brain-coupled required core is wired automatically; list only",
        "# your own extra global skills under global_extra.",
        "targets:",
    ]
    for key, value in targets.items():
        lines.append(f"  {key}: {value}")
    extra = _clean(global_extra, exclude=GLOBAL_BASELINE + tuple(project_baseline))
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
            project_baseline=config.project_baseline,
        )
        if path.read_text() != desired:
            path.write_text(desired)
    return config


def project_baseline(dotbrain_root: Path | None = None) -> tuple[str, ...]:
    """Return code-owned project baseline skills."""

    return PROJECT_BASELINE


def project_link_set(extras: Iterable[str]) -> tuple[str, ...]:
    """Compose the per-project link set: required core + operator extras.

    ``extras`` come from ``project.yaml`` (``config.load_project_skills``) and are
    already deduped with the required core excluded.
    """

    base = project_baseline()
    return base + _clean(extras, exclude=base)


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


def _is_bundled_skill(skill_path: str) -> bool:
    return any(skill_path.startswith(prefix) for prefix in BUNDLED_SKILL_PREFIXES)


def _copy_resource_tree(resource_path: str, dest: Path) -> None:
    if dest.exists() or dest.is_symlink():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    for rel, src in resource_loader.iter_resource_files(resource_path):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(src.read_text())


def _resolve_skill_source(dotbrain_root: Path, skill_path: str) -> Path | None:
    private_src = dotbrain_root / "skills" / skill_path
    if private_src.is_dir():
        return private_src

    if not _is_bundled_skill(skill_path):
        return None

    resource_path = f"skills/{skill_path}"
    if not resource_loader.resource(resource_path).is_dir():
        return None

    cached = dotbrain_root / ".cache" / "skills" / skill_path
    _copy_resource_tree(resource_path, cached)
    return cached


def link_into(
    dotbrain_root: Path,
    skills_dir: Path,
    skill_paths: Sequence[str],
    *,
    label: str = "",
    prune_owned_only: bool = False,
) -> LinkResult:
    """Link skill paths into an agent runtime skills directory."""

    dotbrain_root = Path(dotbrain_root)
    skills_dir = Path(skills_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{label}/" if label else ""
    result = LinkResult()
    wanted: set[str] = set()
    cache_root = (dotbrain_root / ".cache" / "skills").resolve()
    private_root = (dotbrain_root / "skills").resolve()

    for skill_path in skill_paths:
        src = _resolve_skill_source(dotbrain_root, skill_path)
        if src is None or not src.is_dir():
            result.warnings.append(f"skill not found: {skill_path}")
            continue

        dest = skills_dir / Path(skill_path).name
        wanted.add(dest.name)
        if dest.exists() and not dest.is_symlink():
            result.stashed.append(stash_collision(dest))
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(os.path.relpath(src, skills_dir))
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
    dotbrain_root: Path,
    control_root: Path,
    workspaces: Sequence[str],
    skill_paths: Sequence[str],
) -> LinkResult:
    control_root = Path(control_root)
    result = LinkResult()
    for workspace in workspaces:
        skills_dir = control_root / workspace / "skills"
        ws_result = link_into(dotbrain_root, skills_dir, skill_paths, label=workspace)
        result.linked += ws_result.linked
        result.pruned += ws_result.pruned
        result.stashed += ws_result.stashed
        result.warnings += ws_result.warnings
    return result
