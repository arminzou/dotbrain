"""Shared fixtures modeling the dotbrain wiring scenarios.

All fixtures are tmp_path-based: tests never touch a real home directory or the
live dotbrain checkout.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
from pathlib import Path

import pytest

from dotbrain import paths

# The repo root — resolved from this file's location so tests can find the real
# templates/brain/ that ships with dotbrain.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Test fixtures across the suite create symlinks via bare `path.symlink_to(target)`, correct on
# POSIX (target_is_directory is a no-op there) but wrong on Windows when the target is a directory:
# without it, Windows creates a file-type reparse point pointing at a directory, which behaves
# incorrectly for later directory operations. Rather than touch every fixture call site, patch
# Path.symlink_to for the whole test session to infer target_is_directory from whether the target
# actually is a directory (resolved relative to the link's own parent for relative targets) — the
# same inference production call sites make explicitly, applied once here for every test fixture.
_original_symlink_to = pathlib.Path.symlink_to


def _symlink_to_auto(self: pathlib.Path, target, target_is_directory: bool = False) -> None:
    if not target_is_directory:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = self.parent / target_path
        target_is_directory = target_path.is_dir()
    _original_symlink_to(self, target, target_is_directory=target_is_directory)


pathlib.Path.symlink_to = _symlink_to_auto


def set_fake_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """Sandbox the home directory for Path.home()/expanduser() across platforms.

    HOME alone isn't enough: os.path.expanduser() on Windows checks USERPROFILE first and never
    reads HOME at all, so a test that only sets HOME silently keeps resolving `~` to the real
    Windows user profile instead of the sandboxed tmp_path.
    """
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _git_init(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    # Local identity so git mv/rm in archive/offboard flows work without a global git config.
    subprocess.run(["git", "config", "user.email", "test@dotbrain"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "dotbrain test"], cwd=repo, check=True)


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    """A throwaway $HOME for code that resolves the home directory."""
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def dotbrain_home(tmp_path: Path) -> Path:
    """A minimal dotbrain checkout skeleton: brainspaces/, skills/, a git repo.

    Seeds packaged skill text plus one operator-owned skill for linking tests.
    """
    root = tmp_path / "dotbrain"
    for sub in ("brainspaces", "skills"):
        (root / sub).mkdir(parents=True)
    plugin_skills_root = _REPO_ROOT / "plugin" / "skills"
    for skill in (
        "brain/iterate-design",
        "brain/operate-execution",
        "brain/find-unknowns",
        "brain/to-design",
        "brain/close-design",
        "brain/to-issues",
        "brain/triage-public",
        "brain/build-context",
        "brain/review-architecture",
        "brain/grill-decisions",
        "brain/wire-brain",
        "brain/write-skills",
    ):
        name = Path(skill).name
        shutil.copytree(plugin_skills_root / name, root / "skills" / skill)
    skill_dir = root / "skills" / "misc" / "discovery-test"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# discovery-test\n")
    # Keep a legacy data-root templates dir around for migration-oriented tests.
    shutil.copytree(
        _REPO_ROOT / "src" / "dotbrain" / "resources" / "templates" / "brain",
        root / "templates" / ".brain",
    )
    # Stub bootstrap for tests that exercise machine reconciliation paths.
    bootstrap = root / "scripts" / "bootstrap.sh"
    bootstrap.parent.mkdir(parents=True, exist_ok=True)
    bootstrap.write_text("#!/usr/bin/env bash\nexit 0\n")
    bootstrap.chmod(0o755)
    _git_init(root)
    return root


@pytest.fixture
def brainspace(dotbrain_home: Path) -> Path:
    """An existing Brainspace at brainspaces/example/ with agent workspace dirs."""
    root = paths.brainspace(dotbrain_home, "example")
    for link in paths.BRAINSPACE_LINKS:
        (root / link).mkdir(parents=True)
    return root


@pytest.fixture
def disconnected_adopter_repo(tmp_path: Path) -> Path:
    """An adopter repo in the post-unwire state characterized on example.

    Real AGENTS.md without the pointer, CLAUDE.md -> AGENTS.md symlink, an
    exclude file lacking the dotbrain entries, and no agent workspace symlinks.
    """
    repo = tmp_path / "adopter"
    repo.mkdir()
    _git_init(repo)
    (repo / "AGENTS.md").write_text("# Agent Context\n\nProject notes.\n")
    (repo / "CLAUDE.md").symlink_to("AGENTS.md")
    (repo / ".git" / "info" / "exclude").write_text("# git ls-files --others exclude\n")
    return repo
