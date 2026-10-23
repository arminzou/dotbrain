"""Machine-readiness bootstrap.

This module owns machine-global setup: data-root seeding and global runtime links.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from dotbrain import assets, paths, resource_loader, runtimes, skills, subagents
from dotbrain.results import CommandResult, TargetResult

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _default_run(
    argv: Sequence[str], *, cwd: Path | None = None, check: bool = True,
    timeout: int | None = 60, env: dict | None = None,
) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(argv), cwd=cwd, check=check,
        capture_output=True, encoding="utf-8", stdin=subprocess.DEVNULL,
        timeout=timeout, env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
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


def ensure_data_root(dotbrain_home: Path, *, run: Runner = _default_run, user_home: Path | None = None) -> DataRootResult:
    """Create the data root and seed ``config.yaml`` from the packaged template.

    Idempotent — if ``config.yaml`` already exists it is left untouched.
    """
    root = Path(dotbrain_home)
    result = DataRootResult()
    # Check all owned receivers before seeding any of them.
    for relative in (".gitignore", "config.yaml", "skills/skills.yaml", "agents/agents.yaml",
                     *(f"agents/{directory}" for directory, _ in subagents.runtime_spec().values()),
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
            skills.render_global_config(()),
            encoding="utf-8",
            newline="\n",
        )
        result.skills_seeded = True
        result.logs.append(f"seeded skills/skills.yaml into {root}")

    agents_root = root / "agents"
    for subdir, _ext in subagents.runtime_spec().values():
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
    seeded_subagents = subagents.sync_packaged_subagents(root)
    if seeded_subagents:
        result.agents_seeded = True
        result.logs += [
            f"synced {path.relative_to(root).as_posix()} into {root}" for path in seeded_subagents
        ]

    return result


@dataclass
class GlobalSkillBootstrapResult:
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)  # non-fatal warnings


def _global_assets(dotbrain_home: Path, target: str, kind: str, home: Path | None, **kwargs) -> GlobalSkillBootstrapResult:
    from dotbrain import assets
    if kind == "agents" and target != "all" and not runtimes.select(target)[0].subagents:
        return GlobalSkillBootstrapResult()  # this runtime receives no native subagents
    linked = assets.link_global(Path(dotbrain_home), kind, target, user_home=home, **kwargs)
    return GlobalSkillBootstrapResult(
        logs=[f"delivered global {name}" for name in linked.linked] + [f"pruned stale {name}" for name in linked.pruned],
        warnings=linked.warnings,
        notices=linked.notices,
    )


def link_global_skills(dotbrain_home: Path, target: str = "all", *, home: Path | None = None, **kwargs) -> GlobalSkillBootstrapResult:
    return _global_assets(dotbrain_home, target, "skills", home, **kwargs)


def link_global_subagents(dotbrain_home: Path, target: str = "all", *, home: Path | None = None, **kwargs) -> GlobalSkillBootstrapResult:
    return _global_assets(dotbrain_home, target, "agents", home, **kwargs)


def mark_complete(dotbrain_home: Path) -> None:
    """Record that this machine has finished or explicitly declined automatic setup."""
    marker = paths.confined_path(dotbrain_home, ".cache/bootstrap-complete")
    if not marker.is_file():
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("First machine setup complete.\n", encoding="utf-8", newline="\n")


def prepare(dotbrain_home: Path, runtime: str = "all", *, home: Path | None = None,
            run: Runner = _default_run, confirm=None) -> CommandResult:
    """Seed this machine and reconcile its selected, runnable deliveries.

    ``confirm`` renders the discovery list and reads one answer when a person is at a terminal.
    """
    from dotbrain import cursor

    selected = runtimes.select(runtime)
    user = home or Path.home()
    owned = {name: (cursor.global_delivery(dotbrain_home) if name == "cursor" else
                   module.owned(runtimes.user_dir(runtimes.find(name), user)))
             for name, module in assets.HOME_DELIVERY.items()}
    marker = paths.confined_path(dotbrain_home, ".cache/bootstrap-complete")
    first = runtime == "all" and not marker.is_file() and not any(owned.values())
    report = CommandResult("bootstrap", targets=[TargetResult(scope="global")])
    target = report.targets[0]
    found = []
    ready = []
    probe_failed = False
    for rt in selected:
        if rt.name not in owned:
            continue
        present = runtimes.installed(rt)
        if not present and not owned[rt.name] and runtime == "all":
            continue
        status = "ready"
        try:
            if not present:
                raise OSError("command not on PATH")
            completed = run([runtimes.command(rt), "--version"], timeout=5)
            if completed.returncode:
                raise RuntimeError(f"exit {completed.returncode}")
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            probe_failed = True
            status = f"skipped ({exc})"
        found.append(f"{rt.label}: {status}")
        if status == "ready":
            ready.append(rt)
    target.findings += [{"severity": "info", "message": line} for line in found]
    approved = not (first and ready and confirm is not None) or confirm(
        found, f"Set up dotbrain for {', '.join(rt.label for rt in ready)}? [Y/n]"
    )
    chosen = [rt for rt in ready if runtime != "all" or owned[rt.name] or (first and approved)]
    for rt in ready:
        if rt not in chosen:
            target.findings.append({"severity": "info", "message":
                f"{rt.label} is installed; run `dotbrain bootstrap --runtime {rt.name}` to deliver dotbrain to it"})
    try:
        target.changes += ensure_data_root(dotbrain_home, run=run).logs
        deliveries = (["all"] if runtime == "all" else
                      [rt.name for rt in selected if rt.name not in owned]) + [rt.name for rt in chosen]
        for delivery in deliveries:
            errors_before = len(target.errors)
            for linker in (link_global_skills, link_global_subagents):
                linked = linker(dotbrain_home, delivery, home=user, run=run,
                                skip=tuple(owned) if delivery == "all" else ())
                target.changes.extend(line for line in linked.logs if "linked 0 " not in line)
                target.errors += linked.warnings
                target.findings += [{"severity": "warning", "message": m} for m in linked.notices]
            if delivery in owned and len(target.errors) == errors_before:
                target.changes.append(f"Set up dotbrain for {runtimes.find(delivery).label}; undo: dotbrain detach --runtime {delivery}")
        if not target.errors and not (first and probe_failed):
            mark_complete(dotbrain_home)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        # Delivery and configuration errors use the normal command report.
        target.errors.append(str(exc))
    if target.errors:
        target.status = "failure"
        report.status = "partial" if target.changes else "failure"
    return report
