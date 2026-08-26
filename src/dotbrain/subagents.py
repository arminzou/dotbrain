"""Vendor-native subagent config and symlink linking."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from dotbrain import resource_loader, skills

AGENT_TARGETS: dict[str, str] = {
    "claude-code": "~/.claude/agents",
    "codex": "~/.codex/agents",
}

RUNTIME_SPEC: dict[str, tuple[str, str]] = {
    "claude-code": ("claude", ".md"),
    "codex": ("codex", ".toml"),
}

WORKSPACE_RUNTIME: dict[str, str] = {
    ".claude": "claude-code",
    ".codex": "codex",
}


def _required_core() -> tuple[str, ...]:
    """Read the packaged project subagent core from core.yaml."""

    import yaml

    src = resource_loader.resource("core.yaml")
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("packaged core.yaml: expected a YAML mapping")
    subagents_data = data.get("subagents")
    if not isinstance(subagents_data, dict):
        raise ValueError("packaged core.yaml: expected a subagents mapping")
    return skills._clean(subagents_data.get("project_required"))


PROJECT_BASELINE = _required_core()


@dataclass
class GlobalConfig:
    """Operator-configurable global subagent-link settings."""

    targets: dict[str, str] = field(default_factory=lambda: dict(AGENT_TARGETS))
    global_names: tuple[str, ...] = ()


def render_global_subagents(names: Sequence[str] = ()) -> str:
    lines = [
        "# Global vendor-native subagents linked into personal agent homes.",
        "# Remove entries to prune dotbrain-managed links on the next relink.",
        "# Project-scoped extras belong in project.yaml; this file is for personal-home reach and extras.",
        "# Optional target overrides (defaults shown):",
        "# targets:",
        "#   claude-code: ~/.claude/agents",
        "#   codex: ~/.codex/agents",
    ]
    cleaned = skills._clean(names)
    if not cleaned:
        lines += ["# global:", "#   - some-shared-subagent"]
        return "\n".join(lines) + "\n"
    lines.append("global:")
    lines.extend(f"  - {name}" for name in cleaned)
    return "\n".join(lines) + "\n"


def _copy_resource_file(resource_path: str, dest: Path) -> None:
    if dest.exists() or dest.is_symlink():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        resource_loader.resource(resource_path).read_text(encoding="utf-8"),
        encoding="utf-8",
        newline="\n",
    )


def rehydrate_packaged_subagents(dotbrain_home: Path) -> list[Path]:
    root = Path(dotbrain_home)
    cached: list[Path] = []
    for rel, src in resource_loader.iter_resource_files("agents"):
        dest = root / ".cache" / "agents" / rel
        if dest.exists() or dest.is_symlink():
            if dest.is_dir() and not dest.is_symlink():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            src.read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
        cached.append(dest)
    return cached


def seed_private_subagents(dotbrain_home: Path) -> list[Path]:
    """Seed bundled examples into the private agents tree without overwriting overrides."""

    root = Path(dotbrain_home)
    seeded: list[Path] = []
    for rel, src in resource_loader.iter_resource_files("agents"):
        dest = root / "agents" / rel
        if dest.exists() or dest.is_symlink():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            src.read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
        seeded.append(dest)
    return seeded


def _resolve_subagent_files(dotbrain_home: Path, name: str) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    root = Path(dotbrain_home)
    for runtime, (subdir, ext) in RUNTIME_SPEC.items():
        private_src = root / "agents" / subdir / f"{name}{ext}"
        if private_src.is_file():
            resolved[runtime] = private_src
            continue

        resource_path = f"agents/{subdir}/{name}{ext}"
        try:
            resource = resource_loader.resource(resource_path)
        except FileNotFoundError:
            continue
        if not resource.is_file():
            continue

        cached = root / ".cache" / "agents" / subdir / f"{name}{ext}"
        _copy_resource_file(resource_path, cached)
        resolved[runtime] = cached
    return resolved


def link_files_into(
    dotbrain_home: Path,
    target_dir: Path,
    files: Sequence[Path],
    *,
    label: str,
    preserve_collisions: bool = False,
) -> skills.LinkResult:
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    private_root = (Path(dotbrain_home) / "agents").resolve()
    cache_root = (Path(dotbrain_home) / ".cache" / "agents").resolve()
    result = skills.LinkResult()
    wanted: set[str] = set()
    prefix = f"{label}/" if label else ""

    for src in files:
        dest = target_dir / src.name
        wanted.add(dest.name)
        owned = dest.is_symlink() and (
            skills._points_into(dest, private_root) or skills._points_into(dest, cache_root)
        )
        if preserve_collisions and (dest.exists() or dest.is_symlink()) and not owned:
            result.warnings.append(f"{dest} exists and was not created by dotbrain; skipping")
            continue
        if dest.exists() and not dest.is_symlink():
            result.stashed.append(skills.stash_collision(dest))
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        dest.symlink_to(os.path.relpath(src, target_dir))
        result.linked.append(f"{prefix}{dest.name}")

    for entry in sorted(target_dir.iterdir()):
        if not entry.is_symlink() or entry.name in wanted:
            continue
        owned = skills._points_into(entry, private_root) or skills._points_into(entry, cache_root)
        if not owned:
            continue
        entry.unlink()
        result.pruned.append(f"{prefix}{entry.name}")

    return result


def load_global_config(dotbrain_home: Path) -> GlobalConfig:
    path = Path(dotbrain_home) / "agents" / "agents.yaml"
    if not path.is_file():
        return GlobalConfig()
    data = skills._read_yaml_mapping(path)
    targets = data.get("targets") or {}
    if not isinstance(targets, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in targets.items()
    ):
        raise ValueError(f"{path}: targets must be a mapping of runtime -> destination")
    merged_targets = dict(AGENT_TARGETS)
    merged_targets.update(targets)
    return GlobalConfig(
        targets=merged_targets,
        global_names=skills._clean(data.get("global")),
    )


def load_global_subagents(dotbrain_home: Path) -> tuple[str, ...]:
    return load_global_config(dotbrain_home).global_names


def project_link_set(extras: Sequence[str]) -> tuple[str, ...]:
    """Compose per-project link set: required core + operator extras."""

    return PROJECT_BASELINE + skills._clean(extras, exclude=PROJECT_BASELINE)


def link_project_subagents(
    dotbrain_home: Path,
    brainspace: Path,
    workspaces: Sequence[str],
    names: Sequence[str],
) -> skills.LinkResult:
    root = Path(dotbrain_home)
    resolved = {name: _resolve_subagent_files(root, name) for name in names}
    result = skills.LinkResult()

    result.warnings += [f"subagent not found: {name}" for name, files in resolved.items() if not files]

    for workspace in workspaces:
        runtime = WORKSPACE_RUNTIME.get(workspace)
        if runtime is None:
            continue
        files = [resolved[name][runtime] for name in names if runtime in resolved[name]]
        ws_result = link_files_into(
            root,
            Path(brainspace) / workspace / "agents",
            files,
            label=f"{workspace}/agents",
            preserve_collisions=True,
        )
        result.linked += ws_result.linked
        result.pruned += ws_result.pruned
        result.stashed += ws_result.stashed
        result.warnings += ws_result.warnings
    return result
