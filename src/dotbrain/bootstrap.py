"""Machine-readiness bootstrap.

This module owns machine-global setup: data-root seeding and global runtime links.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from dotbrain import paths, resource_loader, skills, subagents

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _default_run(
    argv: Sequence[str], *, cwd: Path | None = None, check: bool = True
) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(argv), cwd=cwd, check=check,
        capture_output=True, encoding="utf-8", stdin=subprocess.DEVNULL,
    )


# --------------------------------------------------------------------------- data-root seeding


@dataclass
class DataRootResult:
    """What happened during data-root seeding (idempotent)."""

    created: bool = False
    config_seeded: bool = False
    skills_seeded: bool = False
    agents_seeded: bool = False
    git_initialized: bool = False
    logs: list[str] = field(default_factory=list)


def ensure_root_gitignore(dotbrain_home: Path) -> bool:
    """Seed the data-root gitignore without replacing operator-owned entries."""

    path = paths.confined_path(Path(dotbrain_home), ".gitignore")
    desired = resource_loader.resource("templates/gitignore").read_text(encoding="utf-8")
    if path.exists() or path.is_symlink():
        return False
    path.write_text(desired, encoding="utf-8", newline="\n")
    return True


def ensure_data_root(dotbrain_home: Path, *, run: Runner = _default_run) -> DataRootResult:
    """Create the data root and seed ``config.yaml`` from the packaged template.

    Idempotent — if ``config.yaml`` already exists it is left untouched.
    """
    root = Path(dotbrain_home)
    result = DataRootResult()
    # Check all owned receivers before seeding any of them.
    for relative in (".gitignore", "config.yaml", "skills/skills.yaml", "agents/agents.yaml",
                     *(f"agents/{directory}" for directory, _ in subagents.RUNTIME_SPEC.values()),
                     ".cache/agents"):
        paths.confined_path(root, relative)

    if not root.exists():
        root.mkdir(parents=True)
        result.created = True
        result.logs.append(f"created data root: {root}")

    # wire/refresh/unwire all require the data root to be a git checkout — Brain and
    # execution state are versioned there. Seeding the files without initializing the
    # repo left every fresh install failing on the first 'dotbrain wire'.
    if not (root / ".git").exists():
        try:
            run(["git", "init", "--quiet"], cwd=root)
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"git is required to initialize the dotbrain data root at {root}; install git"
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip() or "git init failed"
            raise RuntimeError(f"could not initialize {root} as a git checkout: {detail}") from exc
        result.git_initialized = True
        result.logs.append(f"initialized git checkout: {root}")

    if ensure_root_gitignore(root):
        result.logs.append(f"seeded .gitignore into {root}")

    config_dest = root / "config.yaml"
    if not config_dest.exists():
        src = resource_loader.resource("config.yaml")
        if src.is_file():
            config_dest.write_text(
                src.read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
            result.config_seeded = True
            result.logs.append(f"seeded config.yaml into {root}")

    # Seed the operator skill-link config so there's a clear home to manage
    # global skills. Rendered via the same function reconcile uses, so the
    # seeded file is already normalized.
    skills_dest = root / "skills" / "skills.yaml"
    if not skills_dest.exists():
        skills_dest.parent.mkdir(parents=True, exist_ok=True)
        skills_dest.write_text(
            skills.render_global_config(skills.DEFAULT_TARGETS, ()),
            encoding="utf-8",
            newline="\n",
        )
        result.skills_seeded = True
        result.logs.append(f"seeded skills/skills.yaml into {root}")

    agents_root = root / "agents"
    for subdir, _ext in subagents.RUNTIME_SPEC.values():
        (agents_root / subdir).mkdir(parents=True, exist_ok=True)
    agents_dest = agents_root / "agents.yaml"
    if not agents_dest.exists():
        agents_dest.write_text(
            subagents.render_global_subagents(),
            encoding="utf-8",
            newline="\n",
        )
        result.agents_seeded = True
        result.logs.append(f"seeded agents/agents.yaml into {root}")
    seeded_subagents = subagents.rehydrate_packaged_subagents(root)
    if seeded_subagents:
        result.agents_seeded = True
        result.logs += [
            f"rehydrated {path.relative_to(root).as_posix()} into {root}" for path in seeded_subagents
        ]

    return result


@dataclass
class GlobalSkillBootstrapResult:
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _global_assets(dotbrain_home: Path, target: str, kind: str, home: Path | None) -> GlobalSkillBootstrapResult:
    from dotbrain import assets
    runtime = "claude" if target == "claude-code" else target
    linked = assets.link_global(Path(dotbrain_home), kind, runtime, user_home=home)
    return GlobalSkillBootstrapResult(
        logs=[f"delivered global {name}" for name in linked.linked] + [f"pruned stale {name}" for name in linked.pruned],
        warnings=linked.warnings,
    )


def link_global_skills(dotbrain_home: Path, target: str = "all", *, home: Path | None = None) -> GlobalSkillBootstrapResult:
    return _global_assets(dotbrain_home, target, "skills", home)


def link_global_subagents(dotbrain_home: Path, target: str = "all", *, home: Path | None = None) -> GlobalSkillBootstrapResult:
    return _global_assets(dotbrain_home, target, "agents", home)
