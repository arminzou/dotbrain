"""Pure path and contract helpers for the dotbrain control-plane convention.

These encode the compatibility contracts of the control-plane convention as data
and side-effect-free functions. No filesystem mutation happens here; the wiring
mutators build on top of these.
"""

from __future__ import annotations

import os
from pathlib import Path

# The four Brainspace links an adopter repo symlinks into its root, in convention order.
BRAINSPACE_LINKS: tuple[str, ...] = (".brain", ".beads", ".claude", ".codex")

# Matching anchored entries written to an adopter repo's .git/info/exclude.
EXCLUDE_ENTRIES: tuple[str, ...] = ("/.brain", "/.beads", "/.claude", "/.codex")

# Breadcrumb appended to an adopter repo's real AGENTS.md / CLAUDE.md.
ADOPTER_POINTER: str = (
    "@.brain/CLAUDE.md\n"
    "Dotbrain: private project context lives at `.brain/AGENTS.md`; "
    "read it before substantial agent work."
)

# Disabled for now: brain context (DOTBRAIN.md + .brain/AGENTS.md) is injected at
# session start via the SessionStart hook, so the adopter pointer is
# redundant. Flip to True to re-enable wire/doctor pointer management.
INJECT_ADOPTER_POINTER: bool = False


def resolve_dotbrain_root() -> Path:
    """The dotbrain checkout root: ``$DOTBRAIN_ROOT`` if set, else inferred from this file.

    Mirrors the ``DOTBRAIN_ROOT`` override the shell scripts honor. Pure helpers still take an
    explicit root so tests never depend on this.
    """
    env = os.environ.get("DOTBRAIN_ROOT")
    if env:
        return Path(env)
    inferred = Path(__file__).resolve().parents[2]
    if (inferred / ".git").exists() and (inferred / "projects").is_dir():
        return inferred
    return Path.home() / "dotbrain"


def brainspace(dotbrain_root: Path, name: str) -> Path:
    """Return the Brainspace path for a project: ``<dotbrain_root>/projects/<name>``."""
    return Path(dotbrain_root) / "projects" / name


def brainspaces(dotbrain_root: Path) -> list[Path]:
    """Sorted project Brainspaces under ``<dotbrain_root>/projects/``.

    Excludes ``.archive/`` and any other dot-prefixed directories.
    """
    projects = Path(dotbrain_root) / "projects"
    if not projects.is_dir():
        return []
    return sorted(p for p in projects.iterdir() if p.is_dir() and not p.name.startswith("."))


def control_link_targets(dotbrain_root: Path, name: str) -> dict[str, Path]:
    """Map each Brainspace link name to its target inside the project's Brainspace."""
    root = brainspace(dotbrain_root, name)
    return {link: root / link for link in BRAINSPACE_LINKS}


def is_wired(repo: Path) -> bool:
    """True when ``repo`` has all four Brainspace links present as symlinks."""
    repo = Path(repo)
    return all((repo / link).is_symlink() for link in BRAINSPACE_LINKS)


def exclude_entries(repo: Path) -> set[str]:
    """Return the exclude lines present in ``repo``'s .git/info/exclude (empty if absent)."""
    exclude_file = Path(repo) / ".git" / "info" / "exclude"
    if not exclude_file.is_file():
        return set()
    return {
        line.strip()
        for line in exclude_file.read_text().splitlines()
        if line.strip()
    }
