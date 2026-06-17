"""Shared fixtures modeling the control-plane wiring scenarios.

All fixtures are tmp_path-based: tests never touch a real home directory or the
live dotbrain checkout.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from dotbrain import paths

# The repo root — resolved from this file's location so tests can find the real
# templates/brain/ that ships with dotbrain.
_REPO_ROOT = Path(__file__).resolve().parent.parent


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
def dotbrain_root(tmp_path: Path) -> Path:
    """A minimal dotbrain checkout skeleton: projects/, skills/, a git repo.

    Seeds the operating-baseline skill dirs plus one extra skill so the linker has real targets.
    """
    root = tmp_path / "dotbrain"
    for sub in ("projects", "skills"):
        (root / sub).mkdir(parents=True)
    for skill in (
        "brain/operate-beads",
        "brain/enter-main-agent",
        "brain/triage-public",
        "brain/build-context",
        "brain/review-architecture",
        "brain/grill-decisions",
        "brain/wire-brain",
        "misc/discovery-test",
    ):
        skill_dir = root / "skills" / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {Path(skill).name}\n")
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
def control_root(dotbrain_root: Path) -> Path:
    """An existing control root at projects/example/ with agent workspace dirs and a brain agents/ dir."""
    root = paths.control_root(dotbrain_root, "example")
    for link in paths.CONTROL_LINKS:
        (root / link).mkdir(parents=True)
    (root / ".brain" / "agents").mkdir(parents=True, exist_ok=True)
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
