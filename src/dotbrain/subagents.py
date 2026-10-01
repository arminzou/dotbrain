"""Vendor-native subagent config and symlink linking."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from dotbrain import resource_loader, skills, paths

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


def _copy_resource_file(resource_path: str, dest: Path) -> bool:
    desired = resource_loader.resource(resource_path).read_text(encoding="utf-8")
    if dest.is_file() and not dest.is_symlink() and dest.read_text(encoding="utf-8") == desired:
        return False
    if dest.exists() or dest.is_symlink():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        desired,
        encoding="utf-8",
        newline="\n",
    )
    return True


def rehydrate_packaged_subagents(dotbrain_home: Path) -> list[Path]:
    root = Path(dotbrain_home)
    cached: list[Path] = []
    for rel, _src in resource_loader.iter_resource_files("agents"):
        dest = paths.confined_path(root, f".cache/agents/{rel.as_posix()}")
        if _copy_resource_file(f"agents/{rel.as_posix()}", dest):
            cached.append(dest)
    return cached


def seed_private_subagents(dotbrain_home: Path) -> list[Path]:
    """Seed bundled examples into the private agents tree without overwriting overrides."""

    root = Path(dotbrain_home)
    seeded: list[Path] = []
    for rel, src in resource_loader.iter_resource_files("agents"):
        dest = paths.confined_path(root, f"agents/{rel.as_posix()}")
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
    paths.validate_project_name(name)
    resolved: dict[str, Path] = {}
    root = Path(dotbrain_home)
    for runtime, (subdir, ext) in RUNTIME_SPEC.items():
        private_src = paths.confined_path(root / "agents", f"{subdir}/{name}{ext}")
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

        cached = paths.confined_path(root, f".cache/agents/{subdir}/{name}{ext}")
        _copy_resource_file(resource_path, cached)
        resolved[runtime] = cached
    return resolved


def validate_selection(dotbrain_home: Path, names: Sequence[str], runtimes: Sequence[str]) -> list[str]:
    """Check every selected source without writing the packaged cache."""
    errors: list[str] = []
    for name in names:
        paths.validate_project_name(name)
        available: set[str] = set()
        for runtime, (directory, suffix) in RUNTIME_SPEC.items():
            private = paths.confined_path(Path(dotbrain_home) / "agents", f"{directory}/{name}{suffix}")
            resource = resource_loader.resource(f"agents/{directory}/{name}{suffix}")
            if private.is_file() or resource.is_file():
                paths.confined_path(Path(dotbrain_home), f".cache/agents/{directory}/{name}{suffix}")
                available.add(runtime)
        if not available:
            errors.append(f"subagent not found: {name}")
        else:
            errors.extend(f"subagent '{name}' has no definition for runtime '{runtime}'"
                          for runtime in runtimes if runtime not in available)
    return errors


MANAGED_MARKER = "# dotbrain-managed-agent: v1"
GENERATED_NOTICE = "# Generated by dotbrain. Do not edit; customize the source agent definition."


def managed_content(source: Path) -> str:
    return GENERATED_NOTICE + "\n" + MANAGED_MARKER + "\n\n" + source.read_text(encoding="utf-8")


def is_managed_copy(path: Path) -> bool:
    if path.is_symlink() or not path.is_file() or path.suffix != ".toml":
        return False
    with path.open(encoding="utf-8") as stream:
        return (stream.readline().rstrip("\r\n") == GENERATED_NOTICE
                and stream.readline().rstrip("\r\n") == MANAGED_MARKER)


def link_files_into(
    dotbrain_home: Path,
    target_dir: Path,
    files: Sequence[Path],
    *,
    label: str,
    preserve_collisions: bool = False,
    runtime: str | None = None,
) -> skills.LinkResult:
    target_dir = Path(target_dir)
    materialize = runtime == "codex" or (runtime is None and bool(files) and all(src.suffix == ".toml" for src in files))
    target_dir.mkdir(parents=True, exist_ok=True)
    private_root = (Path(dotbrain_home) / "agents").resolve()
    cache_root = (Path(dotbrain_home) / ".cache" / "agents").resolve()
    result = skills.LinkResult()
    wanted: set[str] = set()
    prefix = f"{label}/" if label else ""

    for src in files:
        dest = target_dir / src.name
        wanted.add(dest.name)
        if not materialize and dest.is_symlink() and dest.resolve() == src.resolve():
            continue
        owned = dest.is_symlink() and (
            skills._points_into(dest, private_root) or skills._points_into(dest, cache_root)
        )
        owned = owned or (materialize and is_managed_copy(dest))
        desired = managed_content(src) if materialize else None
        if materialize and owned and not dest.is_symlink() and dest.read_text(encoding="utf-8") == desired:
            continue
        if (preserve_collisions or materialize) and (dest.exists() or dest.is_symlink()) and not owned:
            result.warnings.append(f"{dest} exists and was not created by dotbrain; skipping")
            continue
        if dest.exists() and not dest.is_symlink() and not owned:
            result.stashed.append(skills.stash_collision(dest))
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        try:
            if materialize:
                dest.write_text(desired, encoding="utf-8", newline="\n")
            else:
                dest.symlink_to(os.path.relpath(src, target_dir))
        except OSError as exc:
            message = paths.symlink_privilege_message(exc)
            if message is None:
                raise
            raise RuntimeError(f"{dest}: {message}") from exc
        result.linked.append(f"{prefix}{dest.name}")

    for entry in sorted(target_dir.iterdir()):
        if entry.name in wanted:
            continue
        owned = (entry.is_symlink() and (skills._points_into(entry, private_root) or skills._points_into(entry, cache_root))) or (materialize and is_managed_copy(entry))
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
    *,
    workspace_dirs: Mapping[str, Path] | None = None,
) -> skills.LinkResult:
    root = Path(dotbrain_home)
    errors = validate_selection(root, names, [WORKSPACE_RUNTIME[workspace] for workspace in workspaces if workspace in WORKSPACE_RUNTIME])
    if errors:
        return skills.LinkResult(warnings=errors)
    resolved = {name: _resolve_subagent_files(root, name) for name in names}
    result = skills.LinkResult()

    for workspace in workspaces:
        runtime = WORKSPACE_RUNTIME.get(workspace)
        if runtime is None:
            continue
        files = [resolved[name][runtime] for name in names if runtime in resolved[name]]
        ws_result = link_files_into(
            root,
            ((workspace_dirs.get(workspace) if workspace_dirs else None) or Path(brainspace) / workspace) / "agents",
            files,
            label=f"{workspace}/agents",
            preserve_collisions=True,
            runtime=runtime,
        )
        result.linked += ws_result.linked
        result.pruned += ws_result.pruned
        result.stashed += ws_result.stashed
        result.warnings += ws_result.warnings
    return result
