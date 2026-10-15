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

from dotbrain import config, paths, resource_loader

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
