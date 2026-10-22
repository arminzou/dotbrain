"""Brainspace preparation: Brain seeding and agent workspaces.

A Brainspace is a project's private context store under ``brainspaces/<name>/``. This module owns
its whole lifecycle except the adopter-repo links (``adopter_repos``) and beads setup
(``wiring``/``beads``):

- Brain skeleton seeding from packaged ``templates/brain/`` resources;
- agent-workspace preparation for selected Claude/Codex assets;

It depends only on ``paths``. It is intentionally not split into ``brain_seed.py`` /
``agent_workspaces.py`` yet.
"""

from __future__ import annotations

from pathlib import Path

from dotbrain import config, paths, resource_loader, runtimes

# --------------------------------------------------------------------------- brain & gitignore


MANAGED_BRAIN_PATHS = {"DOTBRAIN.md", "adr/README.md", "designs/README.md", "docs/README.md"}


def seed_brain(brainspace: Path, dotbrain_home: Path, *, create_missing: bool = True) -> list[str]:
    """Seed a brain skeleton from packaged dotbrain resources.

    Designated conventions and scaffold README paths are dotbrain-owned and overwritten
    so package template changes propagate. All other files, including
    ``project.yaml``, are project-owned and are only written when missing.
    ``site/`` is never seeded: having it opts a Brain into a Brain site, so only
    ``dotbrain site init`` writes it. In a Brain that has a site, the dotbrain-owned
    ``site/configure.md`` manual is refreshed like ``DOTBRAIN.md``.
    """

    brain = Path(brainspace) / ".brain"
    if not create_missing and not brain.is_dir():
        raise ValueError(f"{brain}: missing Brain; use dotbrain wire before refresh")
    files = []
    for rel, src in resource_loader.iter_resource_files("templates/brain"):
        relative = rel.as_posix()
        site_manual = relative == "site/configure.md"
        if rel.parts[0] == "site" and not (site_manual and (brain / "site").is_dir()):
            continue
        managed = relative in MANAGED_BRAIN_PATHS or site_manual
        if not create_missing and not managed:
            continue
        dest = paths.confined_path(brain, relative)
        if managed:
            ancestor = dest
            while ancestor != brain:
                if ancestor.is_symlink():
                    raise ValueError(f"{ancestor}: managed convention path contains a symlink; restore a real path")
                ancestor = ancestor.parent
        if not managed and dest.exists():
            continue
        files.append((relative, dest, src.read_text(encoding="utf-8")))
    if not (brain / "CLAUDE.md").is_symlink():
        paths.confined_path(brain, "CLAUDE.md")
    changed = []
    brain.mkdir(parents=True, exist_ok=True)

    if not resource_loader.resource("templates/brain/AGENTS.md").is_file():
        raise FileNotFoundError("package resource templates/brain/AGENTS.md is missing")

    for relative, dest, content in files:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and dest.read_bytes() == content.encode("utf-8"):
            continue
        dest.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        changed.append(relative)

    claude = brain / "CLAUDE.md"
    if not claude.exists() and not claude.is_symlink() and (brain / "AGENTS.md").is_file():
        claude.symlink_to("AGENTS.md")
        changed.append("CLAUDE.md")
    return changed


# --------------------------------------------------------------------------- agent workspaces


def active_agent_workspaces(brainspace: Path, dotbrain_home: Path) -> tuple[str, ...]:
    """Return the declared, recognized workspace directory names for a project."""
    agents = config.load_project_agents(dotbrain_home, Path(brainspace).name)
    return tuple(rt.workspace for rt in runtimes.recognized(agents))


def unknown_agent_warnings(brainspace: Path, dotbrain_home: Path) -> list[str]:
    """Warn on unrecognized agents: a typo in ``project.yaml`` should not be silent."""
    brainspace = Path(brainspace)
    return [f"ignored unknown agent workspace in {brainspace / '.brain' / 'project.yaml'}: {agent}"
            for agent in config.load_project_agents(dotbrain_home, brainspace.name)
            if runtimes.find(agent) is None]
