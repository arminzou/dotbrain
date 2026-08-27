"""Machine-readiness bootstrap.

This module owns machine-global setup: data-root seeding and global runtime links.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from dotbrain import adopter_repos, resource_loader, skills, subagents

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
    """Ensure the data-root gitignore matches the packaged template."""

    path = Path(dotbrain_home) / ".gitignore"
    desired = resource_loader.resource("templates/gitignore").read_text(encoding="utf-8")
    if path.is_file() and path.read_text(encoding="utf-8") == desired:
        return False
    path.write_text(desired, encoding="utf-8", newline="\n")
    return True


def ensure_data_root(dotbrain_home: Path, *, run: Runner = _default_run) -> DataRootResult:
    """Create the data root and seed ``config.yaml`` from the packaged template.

    Idempotent — if ``config.yaml`` already exists it is left untouched.
    """
    root = Path(dotbrain_home)
    result = DataRootResult()

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


def link_global_skills(
    dotbrain_home: Path, target: str = "all", *, home: Path | None = None
) -> GlobalSkillBootstrapResult:
    root = Path(dotbrain_home)
    h = Path(home) if home is not None else Path.home()
    config_path = root / "skills" / "skills.yaml"
    result = GlobalSkillBootstrapResult()
    config = skills.reconcile_global_config(config_path)
    skill_paths = config.global_extra
    if target == "all":
        keys = list(config.targets)
    elif target in config.targets:
        keys = [target]
    else:
        result.warnings.append(f"target '{target}' not configured; skipping")
        return result

    for key in keys:
        dest = adopter_repos.expand_path(config.targets[key], home=h)
        link_result = skills.link_into(root, dest, skill_paths, label=key, prune_owned_only=True)
        result.warnings += [f"{warning} (global {key})" for warning in link_result.warnings]
        result.logs += [f"stashed real path aside: {moved}" for moved in link_result.stashed]
        result.logs += [f"pruned stale {pruned}" for pruned in link_result.pruned]
        result.logs.append(f"global: linked {len(link_result.linked)} skill(s) into {dest}")
    return result


def link_global_subagents(
    dotbrain_home: Path, target: str = "all", *, home: Path | None = None
) -> GlobalSkillBootstrapResult:
    root = Path(dotbrain_home)
    h = Path(home) if home is not None else Path.home()
    result = GlobalSkillBootstrapResult()
    config = subagents.load_global_config(root)
    names = config.global_names
    resolved = {name: subagents._resolve_subagent_files(root, name) for name in names}
    missing = [name for name, runtime_files in resolved.items() if not runtime_files]
    result.warnings += [f"subagent not found: {name}" for name in missing]

    if target == "all":
        keys = list(config.targets)
    elif target in config.targets:
        keys = [target]
    else:
        result.warnings.append(f"target '{target}' not configured; skipping")
        return result

    for key in keys:
        dest = adopter_repos.expand_path(config.targets[key], home=h)
        files = [runtime_files[key] for name, runtime_files in resolved.items() if key in runtime_files]
        link_result = subagents.link_files_into(
            root,
            dest,
            files,
            label=key,
        )
        result.logs += [f"stashed real path aside: {moved}" for moved in link_result.stashed]
        result.logs += [f"pruned stale {pruned}" for pruned in link_result.pruned]
        result.logs.append(f"global: linked {len(files)} subagent file(s) into {dest}")
    return result
