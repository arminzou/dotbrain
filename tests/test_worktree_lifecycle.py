"""End-to-end worktree lifecycle tests (scenario 7)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from dotbrain import adopter_repos, paths


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _make_wired_repo(tmp_path: Path) -> Path:
    """Create a git repo whose root has the real Brainspace link directories."""
    repo = tmp_path / "main-repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    for name in paths.BRAINSPACE_LINKS:
        (repo / name).mkdir()
    (repo / "README.md").write_text("# main\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "initial commit")
    return repo


def _create_worktree(repo: Path, name: str) -> Path:
    worktree = repo / ".claude" / name
    _git(repo, "worktree", "add", "-b", name, str(worktree))
    return worktree


def test_reconcile_worktree_creates_control_links(tmp_path: Path) -> None:
    repo = _make_wired_repo(tmp_path)
    worktree = _create_worktree(repo, "feature-x")

    result = adopter_repos.reconcile_worktree(worktree)

    assert set(result.created) == set(paths.BRAINSPACE_LINKS)
    assert result.repaired == []
    assert result.skipped == []
    assert result.collisions == []
    for name in paths.BRAINSPACE_LINKS:
        assert (worktree / name).is_symlink()
        assert (worktree / name).resolve() == (repo / name).resolve()


def test_reconcile_worktree_idempotent(tmp_path: Path) -> None:
    repo = _make_wired_repo(tmp_path)
    worktree = _create_worktree(repo, "feature-y")

    adopter_repos.reconcile_worktree(worktree)
    result = adopter_repos.reconcile_worktree(worktree)

    assert result.created == []
    assert result.repaired == []
    assert result.skipped == []
    assert result.collisions == []


def test_reconcile_worktree_noop_in_main_checkout(tmp_path: Path) -> None:
    repo = _make_wired_repo(tmp_path)

    result = adopter_repos.reconcile_worktree(repo)

    assert result.created == []
    assert result.repaired == []
    assert result.skipped == []
    assert result.collisions == []


def test_worktree_shares_beads_with_main_checkout(tmp_path: Path) -> None:
    repo = _make_wired_repo(tmp_path)
    worktree = _create_worktree(repo, "beads-slice")

    adopter_repos.reconcile_worktree(worktree)

    assert (worktree / ".beads").resolve() == (repo / ".beads").resolve()


def test_worktree_commit_merge_remove(tmp_path: Path) -> None:
    repo = _make_wired_repo(tmp_path)
    worktree = _create_worktree(repo, "my-slice")
    adopter_repos.reconcile_worktree(worktree)

    (worktree / "feature.txt").write_text("hello from worktree\n")
    _git(worktree, "add", "feature.txt")
    _git(worktree, "commit", "-q", "-m", "feat: add feature")

    _git(repo, "merge", "--ff-only", "my-slice")
    log = _git(repo, "log", "--oneline", "-3")
    assert "feat: add feature" in log

    subprocess.run(
        ["git", "worktree", "remove", str(worktree), "--force"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    _git(repo, "branch", "-d", "my-slice")
    assert not worktree.exists()
