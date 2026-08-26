"""Pure path and contract helpers for the dotbrain wiring convention.

These encode the compatibility contracts of the wiring convention as data
and side-effect-free functions. No filesystem mutation happens here; the wiring
mutators build on top of these.
"""

from __future__ import annotations

import os
from pathlib import Path

# The Brainspace links an adopter repo symlinks into its root, in convention order.
BRAINSPACE_LINKS: tuple[str, ...] = (".brain", ".beads")

# Data-root directory holding the project Brainspaces, in preference order. ``brainspaces`` is
# the current name; ``projects`` is the legacy name still accepted for back-compat.
DATA_DIRS: tuple[str, ...] = ("brainspaces", "projects")

# Matching anchored entries written to an adopter repo's .git/info/exclude.
EXCLUDE_ENTRIES: tuple[str, ...] = ("/.brain", "/.beads")

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

# Windows WinError raised when creating a directory symlink without Developer Mode or elevation.
_WIN_PRIVILEGE_NOT_HELD = 1314

DEVELOPER_MODE_MESSAGE: str = (
    "creating a directory symlink requires Windows Developer Mode (or Administrator "
    "privileges); enable Developer Mode in Settings > Privacy & security > For developers, "
    "then retry"
)


def symlink_privilege_message(exc: OSError) -> str | None:
    """Translate a Windows directory-symlink privilege ``OSError`` into a dotbrain message.

    Returns ``None`` when ``exc`` isn't that specific failure, so callers re-raise everything
    else unchanged.
    """
    if getattr(exc, "winerror", None) == _WIN_PRIVILEGE_NOT_HELD:
        return DEVELOPER_MODE_MESSAGE
    return None


# Windows extended-length path prefix. os.readlink() can surface it on a symlink's stored target
# even when the string originally passed to symlink_to() didn't have it, so exact-string comparisons
# against a freshly computed target must strip it on both sides first.
_WIN_EXTENDED_PREFIX = "\\\\?\\"


def _strip_extended_prefix(path_str: str) -> str:
    if path_str.startswith(_WIN_EXTENDED_PREFIX):
        return path_str[len(_WIN_EXTENDED_PREFIX):]
    return path_str


def symlink_target_matches(existing: str, expected: str) -> bool:
    """True when a symlink's ``os.readlink()`` target already matches the expected target string."""
    return _strip_extended_prefix(existing) == _strip_extended_prefix(expected)


def resolve_dotbrain_home() -> Path:
    """The dotbrain home: ``$DOTBRAIN_HOME`` if set, else inferred from this file.

    ``$DOTBRAIN_HOME`` overrides the data home only; it does not point the installer at a tool
    checkout (install.sh derives that from its own location). Pure helpers still take an explicit
    home so tests never depend on this.
    """
    env = os.environ.get("DOTBRAIN_HOME")
    if env:
        return Path(env)
    inferred = Path(__file__).resolve().parents[2]
    if (inferred / ".git").exists() and any((inferred / d).is_dir() for d in DATA_DIRS):
        return inferred
    return Path.home() / "dotbrain"


def data_dir(dotbrain_home: Path) -> Path:
    """The data-root directory holding Brainspaces.

    Prefers ``brainspaces/`` and falls back to a legacy ``projects/`` when only that exists; a
    fresh root with neither defaults to ``brainspaces/``.
    """
    root = Path(dotbrain_home)
    for name in DATA_DIRS:
        if (root / name).is_dir():
            return root / name
    return root / DATA_DIRS[0]


def brainspace(dotbrain_home: Path, name: str) -> Path:
    """Return the Brainspace path for a project: ``<dotbrain_home>/<data-dir>/<name>``."""
    return data_dir(dotbrain_home) / name


def brainspaces(dotbrain_home: Path) -> list[Path]:
    """Sorted project Brainspaces under the data-root directory.

    Excludes ``.archive/`` and any other dot-prefixed directories.
    """
    base = data_dir(dotbrain_home)
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("."))


def brainspace_link_targets(dotbrain_home: Path, name: str) -> dict[str, Path]:
    """Map each Brainspace link name to its target inside the project's Brainspace."""
    root = brainspace(dotbrain_home, name)
    return {link: root / link for link in BRAINSPACE_LINKS}


def is_wired(repo: Path) -> bool:
    """True when ``repo`` has all Brainspace links present as symlinks."""
    repo = Path(repo)
    return all((repo / link).is_symlink() for link in BRAINSPACE_LINKS)


def exclude_entries(repo: Path) -> set[str]:
    """Return the exclude lines present in ``repo``'s .git/info/exclude (empty if absent)."""
    exclude_file = Path(repo) / ".git" / "info" / "exclude"
    if not exclude_file.is_file():
        return set()
    return {
        line.strip()
        for line in exclude_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
