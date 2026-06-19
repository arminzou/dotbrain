"""Machine-readiness bootstrap.

This module owns machine-global setup: data-root seeding, Claude/Codex
worktree-bootstrap hooks, and the shared subprocess seam.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from dotbrain import brainspaces, resource_loader, skills

# --------------------------------------------------------------------------- data-root seeding


@dataclass
class DataRootResult:
    """What happened during data-root seeding (idempotent)."""

    created: bool = False
    config_seeded: bool = False
    skills_seeded: bool = False
    logs: list[str] = field(default_factory=list)


def ensure_data_root(dotbrain_root: Path) -> DataRootResult:
    """Create the data root and seed ``config.yaml`` from the packaged template.

    Idempotent — if ``config.yaml`` already exists it is left untouched.
    """
    root = Path(dotbrain_root)
    result = DataRootResult()

    if not root.exists():
        root.mkdir(parents=True)
        result.created = True
        result.logs.append(f"created data root: {root}")

    config_dest = root / "config.yaml"
    if not config_dest.exists():
        src = resource_loader.resource("config.yaml")
        if src.is_file():
            config_dest.write_text(src.read_text())
            result.config_seeded = True
            result.logs.append(f"seeded config.yaml into {root}")

    # Seed the operator skill-link config so there's a clear home to manage
    # global skills. Rendered via the same function reconcile uses, so the
    # seeded file is already normalized.
    skills_dest = root / "skills" / "skills.yaml"
    if not skills_dest.exists():
        skills_dest.parent.mkdir(parents=True, exist_ok=True)
        skills_dest.write_text(skills.render_global_config(skills.DEFAULT_TARGETS, ()))
        result.skills_seeded = True
        result.logs.append(f"seeded skills/skills.yaml into {root}")

    return result


# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


@dataclass
class GlobalSkillBootstrapResult:
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _default_run(
    argv: Sequence[str], *, cwd: Path | None = None, env: dict | None = None, check: bool = True
) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True)


def _global_hook_command(script_name: str, dotbrain_root: Path, home: Path | None = None) -> str:
    command_by_script = {
        "claude-worktree-bootstrap.sh": "dotbrain hook claude-worktree-bootstrap",
        "codex-worktree-bootstrap.sh": "dotbrain hook codex-worktree-bootstrap",
    }
    return command_by_script.get(script_name, f"dotbrain hook {Path(script_name).stem}")


def install_global_claude_hook(
    dotbrain_root: Path,
    *,
    settings: Path | None = None,
    home: Path | None = None,
) -> None:
    h = Path(home) if home is not None else Path.home()
    target = Path(settings) if settings is not None else h / ".claude" / "settings.json"
    brainspaces.ensure_json_hook(
        target,
        "SessionStart",
        _global_hook_command("claude-worktree-bootstrap.sh", dotbrain_root, h),
    )


def install_global_codex_hook(
    dotbrain_root: Path,
    *,
    hooks: Path | None = None,
    home: Path | None = None,
) -> None:
    h = Path(home) if home is not None else Path.home()
    target = Path(hooks) if hooks is not None else h / ".codex" / "hooks.json"
    brainspaces.ensure_json_hook(
        target,
        "SessionStart",
        _global_hook_command("codex-worktree-bootstrap.sh", dotbrain_root, h),
        "startup|resume|clear",
        "Bootstrapping dotbrain worktree",
    )


def link_global_skills(dotbrain_root: Path, target: str = "all") -> GlobalSkillBootstrapResult:
    root = Path(dotbrain_root)
    config_path = root / "skills" / "skills.yaml"
    result = GlobalSkillBootstrapResult()
    config = skills.reconcile_global_config(config_path)
    skill_paths = config.linked
    if target == "all":
        keys = list(config.targets)
    elif target in config.targets:
        keys = [target]
    else:
        result.warnings.append(f"target '{target}' not configured; skipping")
        return result

    for key in keys:
        dest = Path(config.targets[key]).expanduser()
        link_result = skills.link_into(root, dest, skill_paths, label=key, prune_owned_only=True)
        result.warnings += [f"{warning} (global {key})" for warning in link_result.warnings]
        result.logs += [f"stashed real path aside: {moved}" for moved in link_result.stashed]
        result.logs += [f"pruned stale {pruned}" for pruned in link_result.pruned]
        result.logs.append(f"global: linked {len(skill_paths)} skill(s) into {dest}")
    return result
