"""Brainspace preparation: Brain seeding and agent workspaces.

A Brainspace is a project's private context store under ``brainspaces/<name>/``. This module owns
its whole lifecycle except the adopter-repo links (``adopter_repos``) and beads setup
(``wiring``/``beads``):

- Brain skeleton seeding from packaged ``templates/brain/`` resources;
- agent-workspace preparation for selected Claude/Codex assets;

Runtime selection shares the asset delivery resolver.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import tempfile

from dotbrain import assets, paths, resource_loader, runtimes, skills

# --------------------------------------------------------------------------- brain & gitignore


MANAGED_BRAIN_PATHS = {"DOTBRAIN.md", "adr/README.md", "designs/README.md", "docs/README.md"}


def seed_brain(brainspace: Path, dotbrain_home: Path, *, create_missing: bool = True,
               notices: list[str] | None = None) -> list[str]:
    """Seed a brain skeleton from packaged dotbrain resources.

    Designated conventions and scaffold README paths are dotbrain-owned and overwritten
    so package template changes propagate. All other files, including
    ``project.yaml``, are project-owned and are only written when missing.
    """

    brain = Path(brainspace) / ".brain"
    if not create_missing and not brain.is_dir():
        raise ValueError(f"{brain}: missing Brain; use dotbrain wire before refresh")
    files = []
    for rel, src in resource_loader.iter_resource_files("templates/brain"):
        relative = rel.as_posix()
        managed = relative in MANAGED_BRAIN_PATHS
        if not create_missing and not managed:
            continue
        dest = paths.confined_path(brain, relative)
        if managed:
            ancestor = dest
            while ancestor != brain:
                if ancestor.is_symlink() or skills._is_junction(ancestor):
                    raise ValueError(f"{ancestor}: managed convention path contains a symlink; restore a real path")
                ancestor = ancestor.parent
        if not managed and dest.exists():
            continue
        content = src.read_text(encoding="utf-8")
        files.append((relative, dest, content))
    changed = []
    brain.mkdir(parents=True, exist_ok=True)

    if not resource_loader.resource("templates/brain/DOTBRAIN.md").is_file():
        raise FileNotFoundError("package resource templates/brain/DOTBRAIN.md is missing")

    for relative, dest, content in files:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and dest.read_bytes() == content.encode("utf-8"):
            continue
        if relative in MANAGED_BRAIN_PATHS and dest.is_file():
            known = json.loads(resource_loader.resource("retired-templates.json").read_text(encoding="utf-8"))
            previous = dest.read_bytes()
            if hashlib.sha256(previous.replace(b"\r\n", b"\n")).hexdigest() != known.get(relative):
                directory = paths.confined_path(brain, ".dotbrain-preserved")
                if directory.is_symlink() or skills._is_junction(directory):
                    raise ValueError(f"{directory}: preservation directory must be a real directory")
                directory.mkdir(exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=directory, prefix=f"{dest.name}-", delete=False) as saved:
                    saved.write(previous)
                if notices is not None:
                    notices.append(f"{dest}: modified shared resource preserved at {saved.name}; inspect before removing")
        dest.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        changed.append(relative)

    return changed


# --------------------------------------------------------------------------- agent workspaces


def active_agent_workspaces(brainspace: Path, dotbrain_home: Path) -> tuple[str, ...]:
    """Return the declared, recognized workspace directory names for a project."""
    agents = assets.project_agents(dotbrain_home, Path(brainspace).name)
    return tuple(rt.workspace for rt in runtimes.recognized(agents))


def unknown_agent_warnings(brainspace: Path, dotbrain_home: Path) -> list[str]:
    """Warn on unrecognized agents: a typo in ``project.yaml`` should not be silent."""
    brainspace = Path(brainspace)
    return [f"ignored unknown agent workspace in {brainspace / '.brain' / 'project.yaml'}: {agent}"
            for agent in assets.project_agents(dotbrain_home, brainspace.name)
            if runtimes.find(agent) is None]
