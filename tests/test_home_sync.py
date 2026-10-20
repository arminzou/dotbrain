"""Home sync against real Git: a bare remote stands in for the home's private remote."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import home_sync
from dotbrain.cli import app

runner = CliRunner()
HOST = platform.node()


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          encoding="utf-8").stdout.strip()


def write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "core.autocrlf", "false")
    return path


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    return bare


@pytest.fixture
def home(tmp_path: Path, remote: Path) -> Path:
    root = make_repo(tmp_path / "home")
    write(root / ".gitignore", "*.tmp\n")
    write(root / "brainspaces" / "alpha" / ".brain" / "CONTEXT.md")
    write(root / "brainspaces" / "beta" / ".brain" / "CONTEXT.md")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "initial")
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "-u", "origin", "main")
    return root


def subjects(repo: Path, rev: str = "HEAD") -> list[str]:
    return git(repo, "log", "--format=%s", rev).splitlines()


def test_one_commit_per_brainspace_then_home(home: Path, remote: Path):
    write(home / "brainspaces" / "alpha" / ".brain" / "CONTEXT.md", "changed\n")
    for name in ("a.md", "b.md", "c.md", "d.md"):
        write(home / "brainspaces" / "beta" / ".brain" / "designs" / name)
    write(home / "config.yaml", "version: 3\n")
    write(home / "brainspaces" / "alpha" / "scratch.tmp")  # ignored

    report = home_sync.sync(home)

    assert report.commits == [
        f"alpha: sync from {HOST} (CONTEXT.md)",
        f"beta: sync from {HOST} (designs/a.md, designs/b.md, designs/c.md and 1 more)",
        f"home: sync from {HOST} (config.yaml)",
    ]
    assert subjects(home)[:3] == report.commits[::-1]
    assert git(home, "show", "--name-only", "--format=", "HEAD~2") == "brainspaces/alpha/.brain/CONTEXT.md"
    assert report.push == "pushed"
    assert git(remote, "rev-parse", "main") == git(home, "rev-parse", "HEAD")
    assert git(home, "status", "--porcelain") == ""
    assert (home / "brainspaces" / "alpha" / "scratch.tmp").exists()


def test_staged_changes_outside_a_group_stay_out_of_its_commit(home: Path):
    write(home / "config.yaml", "version: 3\n")
    git(home, "add", "config.yaml")
    write(home / "brainspaces" / "alpha" / ".brain" / "new.md")

    home_sync.sync(home)

    assert git(home, "show", "--name-only", "--format=", "HEAD~1") == "brainspaces/alpha/.brain/new.md"
    assert git(home, "show", "--name-only", "--format=", "HEAD") == "config.yaml"


def test_deletions_and_paths_with_spaces_are_recorded(home: Path):
    (home / "brainspaces" / "beta" / ".brain" / "CONTEXT.md").unlink()
    write(home / "brainspaces" / "alpha" / ".brain" / "my notes [1].md")

    report = home_sync.sync(home)

    assert report.commits == [f"alpha: sync from {HOST} (my notes [1].md)",
                              f"beta: sync from {HOST} (CONTEXT.md)"]
    assert git(home, "status", "--porcelain") == ""


def test_files_over_the_size_limit_stay_uncommitted(home: Path):
    write(home / "config.yaml", "sync:\n  max-file-size: 100\n")
    write(home / "brainspaces" / "alpha" / ".brain" / "big.bin", "x" * 200)
    write(home / "brainspaces" / "alpha" / ".brain" / "CONTEXT.md", "y" * 200)  # tracked, now large
    write(home / "brainspaces" / "alpha" / ".brain" / "small.md")

    report = home_sync.sync(home)

    assert report.skipped == ["brainspaces/alpha/.brain/CONTEXT.md", "brainspaces/alpha/.brain/big.bin"]
    assert report.commits == [f"alpha: sync from {HOST} (small.md)", f"home: sync from {HOST} (config.yaml)"]
    status = git(home, "status", "--porcelain")
    assert "big.bin" in status and "CONTEXT.md" in status


def test_nothing_uncommitted_creates_no_commit(home: Path):
    before = git(home, "rev-parse", "HEAD")
    report = home_sync.sync(home)
    assert report.commits == [] and report.push == "up-to-date"
    assert git(home, "rev-parse", "HEAD") == before


def test_rejected_push_keeps_commits(home: Path, remote: Path, tmp_path: Path):
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(remote), str(other))
    git(other, "config", "user.name", "Other")
    git(other, "config", "user.email", "other@example.com")
    write(other / "brainspaces" / "beta" / ".brain" / "other.md")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "other machine")
    git(other, "push", "-q")
    remote_head = git(remote, "rev-parse", "main")
    write(home / "brainspaces" / "alpha" / ".brain" / "CONTEXT.md", "local\n")

    result = runner.invoke(app, ["sync", "--push-only", "--home", str(home), "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "success"
    assert payload["targets"][0]["data"]["push"] == "rejected"
    assert payload["targets"][0]["data"]["waiting"] == 1
    assert subjects(home)[0] == f"alpha: sync from {HOST} (CONTEXT.md)"
    assert git(remote, "rev-parse", "main") == remote_head


def test_unreachable_remote_reports_waiting_commits(home: Path, tmp_path: Path):
    git(home, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    write(home / "brainspaces" / "alpha" / ".brain" / "a.md")
    write(home / "brainspaces" / "beta" / ".brain" / "b.md")

    result = runner.invoke(app, ["sync", "--home", str(home)])

    assert result.exit_code == 0, result.output
    assert "remote unreachable; 2 commits waiting to be pushed" in result.output
    assert git(home, "status", "--porcelain") == ""


def test_home_without_remote_gets_commits_only(tmp_path: Path):
    root = make_repo(tmp_path / "home")
    write(root / "config.yaml", "version: 3\n")

    result = runner.invoke(app, ["sync", "--home", str(root)])

    assert result.exit_code == 0, result.output
    assert f"home: sync from {HOST} (config.yaml)" in result.output
    assert "no remote" in result.output
    assert subjects(root) == [f"home: sync from {HOST} (config.yaml)"]


def test_disabled_sync_does_nothing_with_a_notice(home: Path):
    write(home / "config.yaml", "sync:\n  enabled: false\n")
    before = git(home, "rev-parse", "HEAD")

    result = runner.invoke(app, ["sync", "--home", str(home)])

    assert result.exit_code == 0, result.output
    assert "home sync is disabled" in result.output
    assert git(home, "rev-parse", "HEAD") == before


def test_second_concurrent_run_exits_without_changes(home: Path):
    lock = Path(git(home, "rev-parse", "--absolute-git-dir")) / home_sync.LOCK_NAME
    lock.touch()
    write(home / "config.yaml", "version: 3\n")
    before = git(home, "rev-parse", "HEAD")

    result = runner.invoke(app, ["sync", "--home", str(home), "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["targets"][0]["data"]["status"] == "locked"
    assert git(home, "rev-parse", "HEAD") == before
    assert lock.exists()


def test_stale_lock_is_taken_over(home: Path):
    lock = Path(git(home, "rev-parse", "--absolute-git-dir")) / home_sync.LOCK_NAME
    lock.touch()
    old = lock.stat().st_mtime - home_sync.STALE_LOCK_SECONDS - 10
    os.utime(lock, (old, old))
    write(home / "config.yaml", "version: 3\n")

    assert home_sync.sync(home).status == "synced"
    assert not lock.exists()


def test_human_output_lists_commits_and_push(home: Path):
    write(home / "brainspaces" / "alpha" / ".brain" / "CONTEXT.md", "changed\n")
    result = runner.invoke(app, ["sync", "--home", str(home)])
    assert result.exit_code == 0, result.output
    assert f"alpha: sync from {HOST} (CONTEXT.md)" in result.output
    assert "pushed 1 commit to origin/main" in result.output


def test_non_repository_home_fails(tmp_path: Path):
    result = runner.invoke(app, ["sync", "--home", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert "not the root of a Git repository" in json.loads(result.output)["errors"][0]


def test_staged_over_limit_file_is_never_committed(home: Path):
    write(home / "config.yaml", "sync:\n  max-file-size: 100\n")
    big = home / "brainspaces" / "alpha" / ".brain" / "big.bin"
    write(big, "x" * 200)
    git(home, "add", str(big))
    write(home / "brainspaces" / "alpha" / ".brain" / "small.md")

    report = home_sync.sync(home)

    assert report.skipped == ["brainspaces/alpha/.brain/big.bin"]
    assert "big.bin" not in git(home, "log", "--all", "--name-only", "--format=")
    assert git(home, "status", "--porcelain", "--", str(big)) == "?? brainspaces/alpha/.brain/big.bin"


def test_archive_paths_go_to_home_and_names_may_contain_spaces(home: Path):
    write(home / "brainspaces" / ".archive" / "old" / ".brain" / "CONTEXT.md")
    write(home / "brainspaces" / "my project" / ".brain" / "CONTEXT.md")

    report = home_sync.sync(home)

    assert report.commits == [f"my project: sync from {HOST} (CONTEXT.md)",
                              f"home: sync from {HOST} (brainspaces/.archive/old/.brain/CONTEXT.md)"]


@pytest.mark.parametrize("state", ["MERGE_HEAD", "rebase-merge", "rebase-apply"])
def test_merge_or_rebase_in_progress_records_nothing(home: Path, state: str):
    marker = Path(git(home, "rev-parse", "--absolute-git-dir")) / state
    if state.startswith("rebase"):
        marker.mkdir()
    else:
        marker.write_text("0" * 40, encoding="utf-8")
    write(home / "brainspaces" / "alpha" / ".brain" / "new.md")
    before = git(home, "rev-parse", "HEAD")

    plain = runner.invoke(app, ["sync", "--home", str(home)])
    push_only = runner.invoke(app, ["sync", "--push-only", "--home", str(home), "--json"])

    assert plain.exit_code == 1 and f"cannot record while the home has {state}" in plain.output
    assert push_only.exit_code == 0, push_only.output
    assert json.loads(push_only.output)["targets"][0]["data"]["status"] == "blocked"
    assert git(home, "rev-parse", "HEAD") == before
    assert (home / "brainspaces" / "alpha" / ".brain" / "new.md").exists()


def conflict_on_alpha(home: Path) -> Path:
    """Commit two edits to one line on separate branches; return the contested file."""
    contested = home / "brainspaces" / "alpha" / ".brain" / "CONTEXT.md"
    git(home, "switch", "-q", "-c", "side")
    write(contested, "side\n")
    git(home, "commit", "-q", "-am", "side edit")
    git(home, "switch", "-q", "main")
    write(contested, "main\n")
    git(home, "commit", "-q", "-am", "main edit")
    return contested


def assert_refused(home: Path, reason: str) -> None:
    before = git(home, "rev-parse", "HEAD")
    write(home / "brainspaces" / "beta" / ".brain" / "new.md")
    result = runner.invoke(app, ["sync", "--home", str(home), "--json"])
    assert result.exit_code == 1, result.output
    assert reason in json.loads(result.output)["targets"][0]["data"]["blocked_by"]
    assert git(home, "rev-parse", "HEAD") == before
    assert "?? brainspaces/beta/.brain/new.md" in git(home, "status", "--porcelain")


def test_conflicted_cherry_pick_records_nothing(home: Path):
    conflict_on_alpha(home)
    assert subprocess.run(["git", "cherry-pick", "side"], cwd=home, capture_output=True).returncode != 0
    assert_refused(home, "CHERRY_PICK_HEAD")
    assert git(home, "ls-files", "--unmerged")  # the conflict is still there to resolve


def test_unmerged_paths_from_a_stash_pop_record_nothing(home: Path):
    contested = conflict_on_alpha(home)
    git(home, "switch", "-q", "side")
    write(contested, "stashed\n")
    git(home, "stash", "-q")
    git(home, "switch", "-q", "main")
    assert subprocess.run(["git", "stash", "pop"], cwd=home, capture_output=True).returncode != 0
    assert_refused(home, "unmerged paths")


def test_detached_head_records_nothing(home: Path):
    git(home, "switch", "-q", "--detach")
    assert_refused(home, "detached HEAD")


def test_nested_repository_is_reported_not_recorded(home: Path):
    nested = home / "brainspaces" / "alpha" / ".brain" / "vendor"
    make_repo(nested)
    write(nested / "file.md")
    write(home / "brainspaces" / "alpha" / ".brain" / "notes.md")

    result = runner.invoke(app, ["sync", "--home", str(home), "--json"])

    assert result.exit_code == 0, result.output
    target = json.loads(result.output)["targets"][0]
    assert target["data"]["nested"] == ["brainspaces/alpha/.brain/vendor"]
    assert {"severity": "warning",
            "message": "not committed, a nested Git repository: brainspaces/alpha/.brain/vendor"} in target["findings"]
    assert subjects(home)[0] == f"alpha: sync from {HOST} (notes.md)"
    assert "vendor" not in git(home, "ls-files")


def test_group_with_nothing_staged_is_skipped(home: Path):
    write(home / "brainspaces" / "alpha" / ".brain" / "a.md")
    write(home / "brainspaces" / "beta" / ".brain" / "b.md")

    def run(argv, **kwargs):
        if "add" in argv and "beta" in kwargs.get("input", ""):
            return subprocess.CompletedProcess(argv, 0, "", "")  # stage nothing for beta
        return subprocess.run(argv, **kwargs)

    report = home_sync.sync(home, run=run)

    assert report.commits == [f"alpha: sync from {HOST} (a.md)"]


def test_lock_held_by_a_dead_process_is_broken(home: Path):
    lock = Path(git(home, "rev-parse", "--absolute-git-dir")) / home_sync.LOCK_NAME
    dead = subprocess.Popen(["git", "--version"], stdout=subprocess.DEVNULL)
    dead.wait()
    lock.write_text(f"{dead.pid} {time.time()}\n", encoding="utf-8")
    write(home / "config.yaml", "version: 3\n")

    assert home_sync.sync(home).status == "synced"


def test_lock_held_by_a_live_process_is_respected_until_stale(home: Path):
    lock = Path(git(home, "rev-parse", "--absolute-git-dir")) / home_sync.LOCK_NAME
    lock.write_text(f"{os.getpid()} {time.time()}\n", encoding="utf-8")
    assert home_sync.sync(home).status == "locked"
    lock.write_text(f"{os.getpid()} {time.time() - home_sync.STALE_LOCK_SECONDS - 1}\n", encoding="utf-8")
    assert home_sync.sync(home).status == "synced"


def test_push_fails_fast_and_times_out_as_unreachable(home: Path, monkeypatch):
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -i key")
    write(home / "config.yaml", "version: 3\n")
    calls: list[dict] = []

    def run(argv, **kwargs):
        if "push" in argv:
            calls.append(kwargs)
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        return subprocess.run(argv, **kwargs)

    report = home_sync.sync(home, push_only=True, run=run)

    assert report.push == "unreachable" and report.waiting == 1
    assert calls[0]["timeout"] == home_sync.PUSH_TIMEOUT_SECONDS
    assert calls[0]["env"]["GIT_SSH_COMMAND"] == "ssh -i key -o ConnectTimeout=3 -o BatchMode=yes"
