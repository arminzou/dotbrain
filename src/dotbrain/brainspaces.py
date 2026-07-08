"""Brainspace lifecycle: Brain seeding, agent-workspace seeding, and offboarding.

A Brainspace is a project's private context store under ``brainspaces/<name>/``. This module owns
its whole lifecycle except the adopter-repo links (``adopter_repos``) and beads setup
(``wiring``/``beads``):

- Brain skeleton seeding from packaged ``templates/brain/`` resources;
- agent-workspace seeding: the Claude/Codex SessionStart + beads hooks;
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
    return subprocess.run(list(argv), cwd=cwd, check=check, capture_output=True, text=True)


# --------------------------------------------------------------------------- pure helpers


# --------------------------------------------------------------------------- brain & gitignore


def seed_brain(brainspace: Path, dotbrain_home: Path) -> None:
    """Seed a brain skeleton from packaged dotbrain resources.

    ``DOTBRAIN.md`` and ``README.md`` files are dotbrain-owned and overwritten
    so package template changes propagate. All other files are project-owned and
    are only written when missing.
    """

    brain = Path(brainspace) / ".brain"
    brain.mkdir(parents=True, exist_ok=True)

    if not resource_loader.resource("templates/brain/AGENTS.md").is_file():
        raise FileNotFoundError("package resource templates/brain/AGENTS.md is missing")

    for rel, src in resource_loader.iter_resource_files("templates/brain"):
        if src.name == "project.yaml":
            # Brainspace-level, not inside .brain/; project-owned, seed once.
            dest = brainspace / "project.yaml"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_text(src.read_text())
            continue
        dest = brain / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.name in ("DOTBRAIN.md", "README.md"):
            pass
        elif dest.exists():
            continue
        dest.write_text(src.read_text())

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
    data = json.loads(file.read_text()) if file.is_file() and file.read_text().strip() else {}
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
    file.write_text(json.dumps(data, indent=2) + "\n")


def ensure_codex_config(file: Path) -> str | None:
    """Ensure codex config enables hooks; returns a warning if it exists but does not."""
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    if not file.exists():
        file.write_text("[features]\nhooks = true\n")
        return None
    for line in file.read_text().splitlines():
        if line.strip().replace(" ", "") == "hooks=true":
            return None
    return f"{file} exists but does not explicitly enable hooks"


def _merge_hooks_from_template(template_resource: str, dest: Path) -> None:
    """Merge hook entries from a packaged JSON template into an existing or new file.

    Reads ``templates/<template_resource>``, iterates its ``hooks`` block, and calls
    ``ensure_json_hook`` for each entry.  User-owned keys outside ``hooks`` are preserved.
    """
    import json as _json

    src = resource_loader.resource(f"templates/{template_resource}")
    template = _json.loads(src.read_text())
    for event, entries in template.get("hooks", {}).items():
        for entry in entries if isinstance(entries, list) else [entries]:
            matcher = entry.get("matcher", "") if isinstance(entry, dict) else ""
            for hook in entry.get("hooks", []) if isinstance(entry, dict) else []:
                if isinstance(hook, dict) and hook.get("type") == "command":
                    ensure_json_hook(
                        dest, event, hook["command"],
                        matcher=matcher,
                        status_message=hook.get("statusMessage", ""),
                    )


_AGENT_WORKSPACE_TEMPLATES: dict[str, str] = {
    "claude": "claude/settings.json",
    "codex": "codex/hooks.json",
}


def active_agent_workspaces(brainspace: Path, dotbrain_home: Path) -> tuple[str, ...]:
    """Return the declared, known workspace directory names for a project."""
    agents = config.load_project_agents(dotbrain_home, Path(brainspace).name)
    return tuple(f".{agent}" for agent in agents if agent in _AGENT_WORKSPACE_TEMPLATES)


def seed_agent_workspaces(brainspace: Path, dotbrain_home: Path, home: Path | None = None) -> list[str]:
    """Seed declared agent workspaces from packaged templates.

    Only listed workspaces are created or repaired. Existing undeclared
    workspaces are left in place.
    """
    brainspace = Path(brainspace)
    warnings: list[str] = []

    for agent in config.load_project_agents(dotbrain_home, brainspace.name):
        template = _AGENT_WORKSPACE_TEMPLATES.get(agent)
        if template is None:
            warnings.append(f"ignored unknown agent workspace in {brainspace / 'project.yaml'}: {agent}")
            continue

        workspace = brainspace / f".{agent}"
        config_file = "settings.json" if agent == "claude" else "hooks.json"
        _merge_hooks_from_template(template, workspace / config_file)

        if agent == "codex":
            warning = ensure_codex_config(workspace / "config.toml")
            if warning:
                warnings.append(warning)

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
