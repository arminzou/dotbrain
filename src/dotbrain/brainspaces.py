"""Brainspace lifecycle: Brain seeding, agent-workspace preparation, and offboarding.

A Brainspace is a project's private context store under ``brainspaces/<name>/``. This module owns
its whole lifecycle except the adopter-repo links (``adopter_repos``) and beads setup
(``wiring``/``beads``):

- Brain skeleton seeding from packaged ``templates/brain/`` resources;
- agent-workspace preparation for selected Claude/Codex assets;
- offboarding: keep | archive | delete plus the byproduct cleanup that precedes git mv/rm.

It depends only on ``paths``. It is intentionally not split into ``brain_seed.py`` /
``agent_workspaces.py`` yet.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from dotbrain import config, paths, resource_loader

# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]

def _default_run(
    argv: Sequence[str], *, cwd: Path | None = None, check: bool = True
) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(argv), cwd=cwd, check=check, capture_output=True, encoding="utf-8"
    )


# --------------------------------------------------------------------------- pure helpers


# --------------------------------------------------------------------------- brain & gitignore


def seed_brain(brainspace: Path, dotbrain_home: Path) -> None:
    """Seed a brain skeleton from packaged dotbrain resources.

    ``DOTBRAIN.md`` and ``README.md`` files are dotbrain-owned and overwritten
    so package template changes propagate. All other files, including
    ``project.yaml``, are project-owned and are only written when missing.
    """

    brain = Path(brainspace) / ".brain"
    brain.mkdir(parents=True, exist_ok=True)

    if not resource_loader.resource("templates/brain/AGENTS.md").is_file():
        raise FileNotFoundError("package resource templates/brain/AGENTS.md is missing")

    for rel, src in resource_loader.iter_resource_files("templates/brain"):
        dest = brain / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.name not in ("DOTBRAIN.md", "README.md") and dest.exists():
            continue
        content = src.read_text(encoding="utf-8")
        if dest.is_file() and dest.read_bytes() == content.encode("utf-8"):
            continue
        dest.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )

    claude = brain / "CLAUDE.md"
    if not claude.exists():
        claude.symlink_to("AGENTS.md")


# --------------------------------------------------------------------------- agent workspaces


def _hook_command_present(entries: list, command: str) -> bool:
    for entry in entries:
        for hook in entry.get("hooks", []) if isinstance(entry, dict) else []:
            if isinstance(hook, dict) and hook.get("command") == command:
                return True
    return False


def ensure_json_hook(
    file: Path,
    event: str,
    command: str,
    matcher: str = "",
    status_message: str = "",
) -> None:
    """Idempotently merge a hook entry into an agent JSON config (Python port of the jq logic).

    Keyed on the command string anywhere under ``.hooks[event][].hooks[].command``.
    """
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    text = file.read_text(encoding="utf-8") if file.is_file() else ""
    data = json.loads(text) if text.strip() else {}
    if not isinstance(data, dict):
        data = {}

    hooks = data.setdefault("hooks", {})
    entries = hooks.setdefault(event, [])
    if _hook_command_present(entries, command):
        return

    hook: dict = {"type": "command", "command": command}
    if status_message:
        hook["statusMessage"] = status_message
    entry: dict = {"hooks": [hook]}
    if matcher:
        entry["matcher"] = matcher
    entries.append(entry)
    file.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


_KNOWN_AGENT_WORKSPACES = frozenset({"claude", "codex"})


def active_agent_workspaces(brainspace: Path, dotbrain_home: Path) -> tuple[str, ...]:
    """Return the declared, known workspace directory names for a project."""
    agents = config.load_project_agents(dotbrain_home, Path(brainspace).name)
    return tuple(f".{agent}" for agent in agents if agent in _KNOWN_AGENT_WORKSPACES)


def is_brain_only(brainspace: Path) -> bool:
    """True when the Brainspace declares no adopter repo."""

    repo_file = Path(brainspace) / ".repo"
    return (
        repo_file.is_file()
        and repo_file.read_text(encoding="utf-8").strip() == "(brain-only)"
    )


def seed_agent_workspaces(brainspace: Path, dotbrain_home: Path, home: Path | None = None) -> list[str]:
    """Create declared agent workspaces, but only for a brain-only Brainspace.

    A repo-backed Brainspace has its workspaces materialized in the code repo, and skill and
    subagent links point from there straight at the dotbrain home. Seeding one here too would
    leave directories nothing reads. A brain-only Brainspace has no repo, so it is the only
    place its links can live.

    Undeclared agents still warn either way: a typo in ``project.yaml`` should not be silent.
    """
    brainspace = Path(brainspace)
    warnings: list[str] = []
    brain_only = is_brain_only(brainspace)

    for agent in config.load_project_agents(dotbrain_home, brainspace.name):
        if agent not in _KNOWN_AGENT_WORKSPACES:
            warnings.append(f"ignored unknown agent workspace in {brainspace / '.brain' / 'project.yaml'}: {agent}")
            continue
        if brain_only:
            (brainspace / f".{agent}").mkdir(parents=True, exist_ok=True)

    return warnings


# --------------------------------------------------------------------------- offboarding


def _strip_brainspace_byproducts(dotbrain_home: Path, project: str, run: Runner) -> None:
    """Remove the Brainspace's gitignored runtime/wiring litter (beads runtime state,
    .claude/.codex skill symlinks). ``git rm``/``git mv`` only handle tracked files, so
    without this an offboard strands these byproducts on disk. ``-X`` removes *only* ignored
    files, so an uncommitted (untracked) brain is left intact; ``-ff`` clears nested git/dolt dirs."""
    rel = paths.data_dir(dotbrain_home).name
    run(["git", "-C", str(dotbrain_home), "clean", "-ffdXq", "--", f"{rel}/{project}"])


def _is_tracked(dotbrain_home: Path, project: str, run: Runner) -> bool:
    """True if the Brainspace has any git-tracked files (wire no longer commits, so a
    freshly-wired root is untracked and git rm/mv would fail)."""
    rel = paths.data_dir(dotbrain_home).name
    out = run(["git", "-C", str(dotbrain_home), "ls-files", "--", f"{rel}/{project}"], check=False)
    return bool((out.stdout or "").strip())


def offboard_brainspace(
    dotbrain_home: Path,
    project: str,
    mode: str,
    *,
    dry_run: bool = False,
    run: Runner = _default_run,
) -> list[str]:
    """keep | archive | delete the Brainspace. Returns log lines."""
    brainspace = paths.brainspace(dotbrain_home, project)
    rel = paths.data_dir(dotbrain_home).name
    if not brainspace.is_dir():
        return [f"warning: Brainspace {brainspace} not found; nothing to offboard"]

    if mode == "keep":
        return [f"kept Brainspace: {brainspace} (disconnected; re-wire later with dotbrain wire)"]

    if mode == "archive":
        if dry_run:
            return [f"would archive Brainspace {rel}/{project} -> {rel}/.archive/{project} "
                    "(stripping runtime byproducts first)"]
        _strip_brainspace_byproducts(dotbrain_home, project, run)
        archive_dir = paths.data_dir(dotbrain_home) / ".archive"
        archive_dir.mkdir(exist_ok=True)
        dest = archive_dir / project
        if _is_tracked(dotbrain_home, project, run):
            run(["git", "-C", str(dotbrain_home), "mv",
                 f"{rel}/{project}", f"{rel}/.archive/{project}"])
            staged = " (staged)"
        else:
            shutil.move(str(brainspace), str(dest))
            staged = " (uncommitted)"
        return [
            f"archived Brainspace -> {rel}/.archive/{project}{staged}",
            f"suggested commit: chore(brain): archive {project} Brainspace",
        ]

    if mode == "delete":
        if dry_run:
            return [f"would remove Brainspace {rel}/{project} (tracked files + runtime byproducts)"]
        _strip_brainspace_byproducts(dotbrain_home, project, run)
        # -f: delete is a deliberate full removal, so force past locally-modified tracked files
        # (e.g. beads backup-state). --ignore-unmatch: a freshly-wired root is untracked.
        run(["git", "-C", str(dotbrain_home), "rm", "-r", "-q", "-f", "--ignore-unmatch",
             f"{rel}/{project}"])
        if brainspace.exists():
            shutil.rmtree(brainspace)
        return [
            f"removed Brainspace {rel}/{project}",
            f"suggested commit: chore(brain): remove {project} Brainspace",
        ]

    raise ValueError(f"unknown offboard mode: {mode!r}")
