"""Tests for adopter_repos.py: Brainspace link reconciliation, repo path resolution, and the
repo attachment primitives (excludes, symlinks, pointers, wire_repo)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from dotbrain import adopter_repos, paths


def make_runner(calls: list[list[str]]):
    def run(argv, *, cwd=None, env=None, check=True):
        calls.append(list(argv))
        if argv[0] == "git":
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    return run


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


# --------------------------------------------------------------------------- Brainspace links


def test_reconcile_creates_repairs_skips_and_preserves_real_paths(tmp_path: Path) -> None:
    directory = tmp_path / "repo"
    directory.mkdir()
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    (brainspace / ".brain").mkdir()
    (brainspace / ".beads").mkdir()
    (brainspace / ".claude").mkdir()
    wrong = tmp_path / "wrong"
    wrong.mkdir()

    (directory / ".beads").symlink_to(wrong)
    (directory / ".codex").mkdir()

    targets = {
        ".brain": brainspace / ".brain",
        ".beads": brainspace / ".beads",
        ".claude": brainspace / ".claude",
        ".codex": brainspace / ".codex",
    }

    result = adopter_repos.reconcile(directory, targets)

    assert result.created == [".brain", ".claude"]
    assert result.repaired == [".beads"]
    assert result.skipped == [".codex"]
    assert result.collisions == []
    assert (directory / ".brain").resolve() == (brainspace / ".brain").resolve()
    assert (directory / ".beads").resolve() == (brainspace / ".beads").resolve()
    assert (directory / ".claude").resolve() == (brainspace / ".claude").resolve()


def test_reconcile_reports_real_path_collisions(tmp_path: Path) -> None:
    directory = tmp_path / "repo"
    directory.mkdir()
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    (brainspace / ".brain").mkdir()
    (directory / ".brain").mkdir()

    result = adopter_repos.reconcile(directory, {".brain": brainspace / ".brain"})

    assert result.created == []
    assert result.repaired == []
    assert result.skipped == []
    assert result.collisions == [".brain"]


def _windows_privilege_error() -> OSError:
    exc = OSError("A required privilege is not held by the client")
    exc.winerror = 1314  # type: ignore[attr-defined]
    return exc


def test_reconcile_translates_windows_privilege_error(tmp_path: Path, monkeypatch) -> None:
    directory = tmp_path / "repo"
    directory.mkdir()
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    (brainspace / ".brain").mkdir()

    def raising_symlink_to(self, target, target_is_directory=False):
        raise _windows_privilege_error()

    monkeypatch.setattr(Path, "symlink_to", raising_symlink_to)

    result = adopter_repos.reconcile(directory, {".brain": brainspace / ".brain"})

    assert result.created == []
    assert len(result.failed) == 1
    assert "Developer Mode" in result.failed[0]
    assert not (directory / ".brain").exists()


def test_reconcile_reraises_unrelated_oserror(tmp_path: Path, monkeypatch) -> None:
    directory = tmp_path / "repo"
    directory.mkdir()
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    (brainspace / ".brain").mkdir()

    def raising_symlink_to(self, target, target_is_directory=False):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "symlink_to", raising_symlink_to)

    try:
        adopter_repos.reconcile(directory, {".brain": brainspace / ".brain"})
        raised = False
    except OSError:
        raised = True
    assert raised


def test_reconcile_worktree_repairs_wrong_targets(tmp_path: Path) -> None:
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

    worktree = repo / ".codex" / "worktrees" / "slice"
    _git(repo, "worktree", "add", "-b", "slice", str(worktree))

    wrong = tmp_path / "wrong"
    wrong.mkdir()
    (worktree / ".brain").symlink_to(wrong)

    result = adopter_repos.reconcile_worktree(worktree)

    assert ".brain" in result.repaired
    assert set(result.created) == set(paths.BRAINSPACE_LINKS) - {".brain"}
    assert result.skipped == []
    assert result.collisions == []
    for name in paths.BRAINSPACE_LINKS:
        assert (worktree / name).resolve() == (repo / name).resolve()


# --------------------------------------------------------------------------- expand_path


def test_expand_path_tilde_alone(fake_home: Path):
    assert adopter_repos.expand_path("~", fake_home) == fake_home


def test_expand_path_tilde_prefix(fake_home: Path):
    assert adopter_repos.expand_path("~/dotbrain", fake_home) == fake_home / "dotbrain"


def test_expand_path_tilde_nested(fake_home: Path):
    assert adopter_repos.expand_path("~/repos/projects/myproj", fake_home) == \
        fake_home / "repos" / "projects" / "myproj"


def test_expand_path_absolute(fake_home: Path):
    assert adopter_repos.expand_path("/absolute/path", fake_home) == Path("/absolute/path")


def test_expand_path_no_tilde(fake_home: Path):
    assert adopter_repos.expand_path("relative/path", fake_home) == Path("relative/path")


# --------------------------------------------------------------------------- repo_for_brainspace


def test_repo_for_brainspace_reads_repo_file(tmp_path: Path, fake_home: Path):
    brainspace = tmp_path / "myproject"
    brainspace.mkdir()
    (brainspace / ".repo").write_text("~/repos/myproject\n")
    result = adopter_repos.repo_for_brainspace(brainspace, tmp_path, home=fake_home)
    assert result == fake_home / "repos" / "myproject"


def test_repo_for_brainspace_local_overrides_repo(tmp_path: Path, fake_home: Path):
    brainspace = tmp_path / "myproject"
    brainspace.mkdir()
    (brainspace / ".repo").write_text("~/repos/myproject\n")
    (brainspace / ".repo.local").write_text("~/local/myproject\n")
    result = adopter_repos.repo_for_brainspace(brainspace, tmp_path, home=fake_home)
    assert result == fake_home / "local" / "myproject"


def test_repo_for_brainspace_dotbrain_fallback(tmp_path: Path, fake_home: Path):
    brainspace = tmp_path / "dotbrain"
    brainspace.mkdir()
    result = adopter_repos.repo_for_brainspace(brainspace, tmp_path, home=fake_home)
    assert result == tmp_path


def test_repo_for_brainspace_repo_base_fallback(tmp_path: Path, fake_home: Path):
    brainspace = tmp_path / "myproj"
    brainspace.mkdir()
    repo_base = tmp_path / "repos"
    (repo_base / "myproj").mkdir(parents=True)
    result = adopter_repos.repo_for_brainspace(brainspace, tmp_path, repo_base=repo_base, home=fake_home)
    assert result == repo_base / "myproj"


def test_repo_for_brainspace_none_when_not_found(tmp_path: Path, fake_home: Path):
    brainspace = tmp_path / "ghost"
    brainspace.mkdir()
    result = adopter_repos.repo_for_brainspace(brainspace, tmp_path, home=fake_home)
    assert result is None


def test_repo_for_brainspace_skips_comments(tmp_path: Path, fake_home: Path):
    brainspace = tmp_path / "myproject"
    brainspace.mkdir()
    (brainspace / ".repo").write_text("# comment\n\n~/repos/myproject\n")
    result = adopter_repos.repo_for_brainspace(brainspace, tmp_path, home=fake_home)
    assert result == fake_home / "repos" / "myproject"


# --------------------------------------------------------------------------- pure helpers


def test_abbrev_home(fake_home: Path):
    assert adopter_repos.abbrev_home(fake_home, fake_home) == "~"
    assert adopter_repos.abbrev_home(fake_home / "repos" / "x", fake_home) == "~/repos/x"
    assert adopter_repos.abbrev_home(Path("/etc/hosts"), fake_home) == "/etc/hosts"


def test_is_dotbrain_repo(dotbrain_home: Path, tmp_path: Path):
    assert adopter_repos.is_dotbrain_repo(dotbrain_home, dotbrain_home)
    assert not adopter_repos.is_dotbrain_repo(tmp_path / "other", dotbrain_home)


def test_target_is_outside_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    link = repo / "link"
    link.symlink_to(outside)
    assert adopter_repos.target_is_outside_repo(repo, link)

    broken = repo / "broken"
    broken.symlink_to(tmp_path / "nope")
    assert not adopter_repos.target_is_outside_repo(repo, broken)  # unresolvable -> treated as inside


# --------------------------------------------------------------------------- excludes & symlinks


def test_ensure_exclude_line_idempotent(tmp_path: Path):
    exclude = tmp_path / "info" / "exclude"
    adopter_repos.ensure_exclude_line(exclude, "/.brain")
    adopter_repos.ensure_exclude_line(exclude, "/.brain")
    assert exclude.read_text().splitlines().count("/.brain") == 1


def test_ensure_symlink_create_repair_and_collision(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    good = tmp_path / "target"
    good.mkdir()

    assert adopter_repos.ensure_symlink(repo, ".brain", good) is None
    assert (repo / ".brain").resolve() == good.resolve()

    # repointing a wrong existing symlink
    (repo / ".beads").symlink_to(tmp_path / "stale")
    assert adopter_repos.ensure_symlink(repo, ".beads", good) is None
    assert (repo / ".beads").resolve() == good.resolve()

    # a real file in the way is left untouched, with a warning
    (repo / ".claude").write_text("real")
    warning = adopter_repos.ensure_symlink(repo, ".claude", good)
    assert warning and "not a symlink" in warning
    assert (repo / ".claude").read_text() == "real"


def test_ensure_symlink_translates_windows_privilege_error(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    good = tmp_path / "target"
    good.mkdir()

    def raising_symlink_to(self, target, target_is_directory=False):
        raise _windows_privilege_error()

    monkeypatch.setattr(Path, "symlink_to", raising_symlink_to)

    warning = adopter_repos.ensure_symlink(repo, ".brain", good)
    assert warning and "Developer Mode" in warning


def test_ensure_agent_context_pointer_creates_when_absent(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    assert adopter_repos.ensure_agent_context_pointer(repo) == []
    assert paths.ADOPTER_POINTER in (repo / "AGENTS.md").read_text()


def test_ensure_agent_context_pointer_dedupes_symlinked_claude(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# notes\n")
    (repo / "CLAUDE.md").symlink_to("AGENTS.md")
    adopter_repos.ensure_agent_context_pointer(repo)
    adopter_repos.ensure_agent_context_pointer(repo)  # idempotent
    text = (repo / "AGENTS.md").read_text()
    assert text.count(".brain/AGENTS.md") == 1  # CLAUDE->AGENTS resolves to one file, appended once


# --------------------------------------------------------------------------- attach


def test_wire_repo_excludes_external_symlinks(dotbrain_home: Path, brainspace: Path, tmp_path: Path):
    repo = tmp_path / "adopter"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    calls: list[list[str]] = []
    warnings = adopter_repos.wire_repo(repo, brainspace, dotbrain_home, run=make_runner(calls))
    assert warnings == []
    for name in paths.BRAINSPACE_LINKS:
        assert (repo / name).is_symlink()
    excludes = paths.exclude_entries(repo)
    assert {"/.brain", "/.beads", "/.claude", "/.codex"} <= excludes


def test_wire_repo_can_skip_beads_link(dotbrain_home: Path, brainspace: Path, tmp_path: Path):
    repo = tmp_path / "adopter"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    warnings = adopter_repos.wire_repo(
        repo,
        brainspace,
        dotbrain_home,
        run=make_runner([]),
        skip_beads_link=True,
    )

    assert warnings == []
    assert not (repo / ".beads").exists()
    assert (repo / ".brain").is_symlink()
    assert (repo / ".claude").is_symlink()
    assert (repo / ".codex").is_symlink()
    assert "/.beads" not in paths.exclude_entries(repo)


def test_legacy_projects_rename_repairs_links_via_reconcile(tmp_path: Path):
    """The documented migration `mv projects brainspaces && dotbrain wire --all`:
    after renaming the data dir, reconcile re-points the now-dangling repo links."""
    root = tmp_path / "dotbrain"
    legacy = root / "projects" / "example"
    for link in paths.BRAINSPACE_LINKS:
        (legacy / link).mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    for link in paths.BRAINSPACE_LINKS:
        (repo / link).symlink_to(legacy / link)

    # Legacy layout resolves to projects/.
    assert paths.data_dir(root) == root / "projects"

    # Migrate: rename the data dir. Links now dangle (point at the old projects/ path).
    (root / "projects").rename(root / "brainspaces")
    assert paths.data_dir(root) == root / "brainspaces"
    assert not (repo / ".brain").resolve().exists()

    # Reconcile (what `wire --all` does) re-points every link to the new Brainspace.
    result = adopter_repos.reconcile(repo, paths.brainspace_link_targets(root, "example"))
    assert set(result.repaired) == set(paths.BRAINSPACE_LINKS)
    assert os.readlink(repo / ".brain") == str(root / "brainspaces" / "example" / ".brain")
    assert (repo / ".brain").resolve().is_dir()
