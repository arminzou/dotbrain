from pathlib import Path

import pytest

from dotbrain import worktrees


def test_slugify_name_normalizes_human_task_names():
    assert worktrees.slugify_name(" scaffold blog! ") == "scaffold-blog"


def test_slugify_name_rejects_empty_values():
    with pytest.raises(ValueError):
        worktrees.slugify_name(" !!! ")


def test_codex_worktree_plan_uses_codex_workspace_directory(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    plan = worktrees.codex_worktree_plan(
        repo,
        "scaffold blog",
        base="develop",
        prompt="start here",
        codex_args=("--sandbox", "workspace-write"),
    )

    assert plan.name == "scaffold-blog"
    assert plan.worktree == repo.resolve() / ".codex" / "worktrees" / "scaffold-blog"
    assert plan.create_command == (
        "git",
        "worktree",
        "add",
        "-b",
        "scaffold-blog",
        str(plan.worktree),
        "develop",
    )
    assert plan.codex_command == (
        "codex",
        "-C",
        str(plan.worktree),
        "--sandbox",
        "workspace-write",
        "start here",
    )


def test_create_codex_worktree_reuses_existing_worktree(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    plan = worktrees.codex_worktree_plan(repo, "slice")
    plan.worktree.mkdir(parents=True)
    calls = []

    worktrees.create_codex_worktree(plan, run=lambda *args, **kwargs: calls.append(args))

    assert calls == []
