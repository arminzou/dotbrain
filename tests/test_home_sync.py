"""Home sync against real Git: a bare remote stands in for the home's private remote."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import home_sync
from dotbrain.cli import app

runner = CliRunner()
HOST = "testhost"


@pytest.fixture(autouse=True)
def short_hostname(monkeypatch):
    """A fixed short host name, so human output never wraps on runners with long host names."""
    monkeypatch.setattr(platform, "node", lambda: HOST)


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


def lock_path(home: Path) -> Path:
    return Path(git(home, "rev-parse", "--absolute-git-dir")) / home_sync.LOCK_NAME


HOLD_LOCK = """
import sys
from pathlib import Path
from dotbrain import home_sync
held = home_sync._acquire(Path(sys.argv[1]))
assert held is not None
print("held", flush=True)
sys.stdin.read()
"""


def test_lock_held_by_another_process_blocks_until_it_exits(home: Path):
    lock = lock_path(home)
    holder = subprocess.Popen([sys.executable, "-c", HOLD_LOCK, str(lock)], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, encoding="utf-8")
    try:
        assert holder.stdout.readline().strip() == "held"
        write(home / "config.yaml", "version: 3\n")
        before = git(home, "rev-parse", "HEAD")

        result = runner.invoke(app, ["sync", "--home", str(home), "--json"])

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["targets"][0]["data"]["status"] == "locked"
        assert git(home, "rev-parse", "HEAD") == before
    finally:
        holder.kill()  # dies without releasing: the OS drops its lock
        holder.wait()
        holder.stdin.close()
        holder.stdout.close()

    assert lock.exists()
    assert home_sync.sync(home).status == "synced"
    assert lock.exists()  # the lock file stays; only the OS lock comes and goes


def test_lock_held_on_another_descriptor_blocks_a_second_sync(home: Path):
    fd = home_sync._acquire(lock_path(home))
    assert fd is not None
    try:
        assert home_sync._acquire(lock_path(home)) is None
        assert home_sync.sync(home).status == "locked"
    finally:
        home_sync._release(fd)
    assert home_sync.sync(home).status == "synced"


def test_leftover_lock_file_does_not_block(home: Path):
    lock_path(home).write_text("12345 0\n", encoding="utf-8")  # a dead owner's file, no OS lock
    write(home / "config.yaml", "version: 3\n")

    assert home_sync.sync(home).status == "synced"


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
    assert calls[0]["env"]["GIT_SSH_COMMAND"] == ("ssh -i key -o ConnectTimeout=3 -o BatchMode=yes"
                                                  " -o ServerAliveInterval=5 -o ServerAliveCountMax=1")
    assert home_sync.sync(home, push_only=True, run=run).status != "locked"  # the lock was released


def test_timeout_kills_the_whole_process_tree(tmp_path: Path):
    """A stalled child that started its own child holding the pipes, as git does with ssh."""
    started, alive = tmp_path / "started", tmp_path / "alive"
    grandchild = (f"import pathlib, time; pathlib.Path({str(started)!r}).touch(); time.sleep(3); "
                  f"pathlib.Path({str(alive)!r}).touch()")
    child = ("import subprocess, sys, time; print('partial', flush=True); "
             f"subprocess.Popen([sys.executable, '-c', {grandchild!r}], "
             "stdout=sys.stdout, stderr=sys.stderr); time.sleep(30)")
    begin = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as stalled:
        home_sync.run_bounded([sys.executable, "-c", child], capture_output=True, encoding="utf-8",
                              timeout=1.5)
    elapsed = time.monotonic() - begin
    time.sleep(max(0, 4.5 - elapsed))  # past the moment a surviving grandchild would write ``alive``

    assert elapsed < 1.5 + home_sync._DRAIN_SECONDS
    assert started.exists() and not alive.exists()
    assert "partial" in stalled.value.stdout  # output collected before the kill is kept, as subprocess.run does


# Full sync between two machines: ``home`` is machine W, ``other`` (a second clone) is machine V.

ALPHA = Path("brainspaces") / "alpha" / ".brain"
TODAY = date.today().isoformat()


@pytest.fixture
def other(tmp_path: Path, remote: Path, home: Path) -> Path:
    clone = tmp_path / "other"
    git(tmp_path, "clone", "-q", "-c", "core.autocrlf=false", str(remote), str(clone))
    git(clone, "config", "user.name", "Other")
    git(clone, "config", "user.email", "other@example.com")
    return clone


def tree(repo: Path) -> dict[str, bytes]:
    return {path.relative_to(repo).as_posix(): path.read_bytes() for path in repo.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(repo).parts}


def no_operation_in_progress(repo: Path) -> bool:
    git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir"))
    return not any((git_dir / name).exists() for name in home_sync._IN_PROGRESS) and git(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("gitfile", [False, True])
def test_nested_repository_files_listed_individually_are_never_recorded(home: Path, remote: Path,
                                                                      tmp_path: Path, gitfile: bool):
    relative = ALPHA / "vendor"
    nested = home / relative
    write(nested / "tracked.md", "initial\n")
    home_sync.sync(home)
    tip = git(home, "rev-parse", "HEAD")
    args = ["--separate-git-dir", str(tmp_path / "nested.git")] if gitfile else []
    git(nested, "init", "-q", "-b", "main", *args)
    write(nested / "tracked.md", "local edit\n")
    write(nested / "local.md", "local\n")
    write(nested / "subdir" / "another.md", "another\n")
    before = tree(home)
    assert (relative / "local.md").as_posix() in home_sync._changed_paths(subprocess.run, home)

    for push_only in (False, True):
        report = home_sync.sync(home, push_only=push_only)
        assert report.nested == [relative.as_posix()]
        assert report.commits == [] and report.push == "up-to-date"
        assert git(home, "rev-parse", "HEAD") == tip
        assert git(remote, "rev-parse", "main") == tip
        assert (relative / "local.md").as_posix() not in git(home, "ls-files")
        assert tree(home) == before


@pytest.mark.parametrize("change", ["added", "edited", "root"])
def test_incoming_paths_in_nested_repository_block_merge_and_push(home: Path, other: Path,
                                                                remote: Path, change: str):
    relative = ALPHA / "vendor"
    incoming = relative if change == "root" else relative / "upstream.md"
    if change == "edited":
        write(other / incoming, "initial\n")
        home_sync.sync(other)
        home_sync.sync(home)
    nested = home / relative
    nested.mkdir(parents=True, exist_ok=True)
    git(nested, "init", "-q", "-b", "main")
    write(nested / "local.md", "local\n")
    write(other / incoming, "upstream\n")
    home_sync.sync(other)
    remote_tip = git(remote, "rev-parse", "main")
    write(home / ALPHA / "notes.md", "local notes\n")  # a commit waiting to be pushed
    before = tree(home)
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.run(argv, **kwargs)

    for _ in range(2):
        report = home_sync.sync(home, run=run)
        assert report.status == "collision" and report.push == "none"
        assert report.collisions == [incoming.as_posix()]
        assert report.nested == [relative.as_posix()]
        assert not report.merged and report.waiting == 1
        assert git(remote, "rev-parse", "main") == remote_tip
        assert tree(home) == before
        assert git(home, "ls-files", "--unmerged") == ""
        assert not (home / ".git" / "MERGE_HEAD").exists()
    assert not any("merge" in call or "push" in call for call in calls)


def test_nested_repository_does_not_block_incoming_sibling(home: Path, other: Path):
    make_repo(home / ALPHA / "vendor")
    write(home / ALPHA / "vendor" / "local.md")
    write(other / ALPHA / "vendor-notes.md", "upstream\n")
    home_sync.sync(other)

    report = home_sync.sync(home)

    assert report.status == "synced" and report.merged and not report.collisions
    assert (home / ALPHA / "vendor-notes.md").read_text(encoding="utf-8") == "upstream\n"
    assert "vendor/local.md" not in git(home, "ls-files")


def both_sync(first: Path, second: Path) -> None:
    for repo in (first, second, first):
        assert home_sync.sync(repo).push in ("pushed", "up-to-date")
    assert tree(first) == tree(second)
    assert no_operation_in_progress(first) and no_operation_in_progress(second)


def test_uncommitted_project_does_not_block_receiving_another(home: Path, other: Path):
    (other / "brainspaces" / "beta" / ".brain" / "b.md").write_bytes(b"from V\n")
    assert home_sync.sync(other).push == "pushed"
    (home / "brainspaces" / "alpha" / ".brain" / "a.md").write_bytes(b"from W\n")

    both_sync(home, other)

    for repo in (home, other):
        assert (repo / "brainspaces" / "alpha" / ".brain" / "a.md").read_bytes() == b"from W\n"
        assert (repo / "brainspaces" / "beta" / ".brain" / "b.md").read_bytes() == b"from V\n"
    assert not home_sync.sync(home).merged  # nothing new upstream


def test_edits_to_different_paragraphs_merge_without_copies(home: Path, other: Path):
    write(home / ALPHA / "CONTEXT.md", "one\n\ntwo\n\nthree\n")
    home_sync.sync(home)
    home_sync.sync(other)
    write(other / ALPHA / "CONTEXT.md", "one by V\n\ntwo\n\nthree\n")
    home_sync.sync(other)
    write(home / ALPHA / "CONTEXT.md", "one\n\ntwo\n\nthree by W\n")

    report = home_sync.sync(home)

    assert report.merged and report.conflict_copies == []
    both_sync(home, other)
    assert (other / ALPHA / "CONTEXT.md").read_text(encoding="utf-8") == "one by V\n\ntwo\n\nthree by W\n"
    assert not list((home / ALPHA).glob("*.sync-conflict-*"))


def test_diverged_sync_overrides_merge_ff_only(home: Path, other: Path, remote: Path):
    write(other / ALPHA / "upstream.md", "upstream\n")
    home_sync.sync(other)
    write(home / ALPHA / "local.md", "local\n")
    git(home, "config", "merge.ff", "only")

    report = home_sync.sync(home)

    assert report.status == "synced" and report.merged and report.push == "pushed"
    assert len(git(home, "rev-list", "--parents", "-n", "1", "HEAD").split()) == 3
    assert git(remote, "rev-parse", "main") == git(home, "rev-parse", "HEAD")
    assert (home / ALPHA / "local.md").read_text(encoding="utf-8") == "local\n"
    assert (home / ALPHA / "upstream.md").read_text(encoding="utf-8") == "upstream\n"
    assert no_operation_in_progress(home)


def test_same_paragraph_edits_keep_both_versions(home: Path, other: Path):
    write(other / ALPHA / "CONTEXT.md", "V's line\n")
    home_sync.sync(other)
    write(home / ALPHA / "CONTEXT.md", "W's line\n")

    result = runner.invoke(app, ["sync", "--home", str(home), "--json"])

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["targets"][0]["data"]
    copy = f"brainspaces/alpha/.brain/CONTEXT.sync-conflict-{TODAY}-{HOST}.md"
    message = f"sync: merge on {HOST}, 1 conflict copies ({copy})"
    assert data["merged"] is True and data["conflict_copies"] == [copy] and data["attempts"] == 1
    assert data["push"] == "pushed"
    assert subjects(home)[0] == message
    both_sync(home, other)
    for repo in (home, other):
        assert (repo / ALPHA / "CONTEXT.md").read_text(encoding="utf-8") == "W's line\n"
        assert (repo / copy).read_text(encoding="utf-8") == "V's line\n"


def test_binary_conflict_copy_keeps_exact_bytes(home: Path, other: Path):
    mine, theirs = b"\x00\xffW\r\n\x89", b"\x00\xfeV\n\x01"
    (other / ALPHA / "image.bin").write_bytes(theirs)
    home_sync.sync(other)
    (home / ALPHA / "image.bin").write_bytes(mine)

    report = home_sync.sync(home)

    assert report.conflict_copies == [f"brainspaces/alpha/.brain/image.sync-conflict-{TODAY}-{HOST}.bin"]
    assert (home / ALPHA / "image.bin").read_bytes() == mine
    assert (home / report.conflict_copies[0]).read_bytes() == theirs


@pytest.mark.parametrize("deleter", ["home", "other"])
def test_an_edit_wins_over_a_delete(home: Path, other: Path, deleter: str):
    machines = {"home": home, "other": other}
    editor = "other" if deleter == "home" else "home"
    (machines[deleter] / ALPHA / "CONTEXT.md").unlink()
    write(machines[editor] / ALPHA / "CONTEXT.md", "edited\n")
    home_sync.sync(other)

    report = home_sync.sync(home)

    assert report.merged and report.conflict_copies == []
    assert subjects(home)[0] == f"sync: merge on {HOST}, 0 conflict copies"
    both_sync(home, other)
    assert (home / ALPHA / "CONTEXT.md").read_text(encoding="utf-8") == "edited\n"


def test_conflict_copy_names_split_on_the_file_name_and_stay_unique(tmp_path: Path):
    base = f"notes.v2/archive.tar.sync-conflict-{TODAY}-{HOST}"
    assert home_sync._copy_name(tmp_path, "notes.v2/archive.tar.gz") == f"{base}.gz"
    write(tmp_path / f"{base}.gz")
    assert home_sync._copy_name(tmp_path, "notes.v2/archive.tar.gz") == f"{base}-2.gz"
    assert home_sync._copy_name(tmp_path, "Makefile") == f"Makefile.sync-conflict-{TODAY}-{HOST}"


def test_files_skipped_by_the_size_limit_survive_the_merge(home: Path, other: Path):
    write(home / "config.yaml", "sync:\n  max-file-size: 100\n")
    home_sync.sync(home)
    home_sync.sync(other)
    write(other / "brainspaces" / "beta" / ".brain" / "b.md")
    home_sync.sync(other)
    write(home / ALPHA / "CONTEXT.md", "y" * 200)  # tracked, now over the limit
    write(home / ALPHA / "small.md")

    report = home_sync.sync(home)

    assert report.push == "pushed" and report.merged
    assert (home / ALPHA / "CONTEXT.md").read_text(encoding="utf-8") == "y" * 200
    assert (home / "brainspaces" / "beta" / ".brain" / "b.md").exists()
    assert git(home, "status", "--porcelain") == "M brainspaces/alpha/.brain/CONTEXT.md"


def moving_remote(other: Path, moves: int):
    """A runner where the other machine pushes just before each of the first ``moves`` pushes."""
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(argv)
        if "push" in argv and sum("push" in call for call in calls) <= moves:
            write(other / "brainspaces" / "beta" / ".brain" / f"move{len(calls)}.md")
            home_sync.sync(other)
        return subprocess.run(argv, **kwargs)

    return run, calls


def test_rejected_full_sync_push_is_retried_at_most_three_times(home: Path, other: Path, monkeypatch):
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)
    write(home / ALPHA / "a.md")
    run, calls = moving_remote(other, moves=10)

    result = home_sync.sync(home, run=run)

    pushes = [call for call in calls if "push" in call]
    assert len(pushes) == 1 + home_sync.PUSH_RETRIES and result.attempts == 4
    assert result.push == "rejected" and result.waiting >= 1
    assert not any(flag in call for call in pushes for flag in ("--force", "-f", "--force-with-lease"))
    assert not any("rebase" in call for call in calls)
    merges = [call for call in calls if "merge" in call]
    assert merges and all("--no-autostash" in call and "--no-overwrite-ignore" in call for call in merges)
    assert sum("core.sshCommand" in call for call in calls) == 1
    assert no_operation_in_progress(home)


def test_rejected_full_sync_push_integrates_again_and_pushes(home: Path, other: Path, remote: Path):
    write(home / ALPHA / "a.md")
    run, _ = moving_remote(other, moves=1)

    result = home_sync.sync(home, run=run)

    assert result.push == "pushed" and result.attempts == 2
    assert git(remote, "rev-parse", "main") == git(home, "rev-parse", "HEAD")


def test_push_only_never_fetches(home: Path):
    write(home / ALPHA / "a.md")
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.run(argv, **kwargs)

    assert home_sync.sync(home, push_only=True, run=run).push == "pushed"
    assert not any("fetch" in call or "rebase" in call or "merge" in call for call in calls)


def test_offline_full_sync_later_pushes_waiting_commits(home: Path, remote: Path, tmp_path: Path):
    git(home, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    write(home / ALPHA / "a.md")
    assert home_sync.sync(home).push == "unreachable"
    git(home, "remote", "set-url", "origin", str(remote))

    report = home_sync.sync(home)

    assert report.push == "pushed" and report.pushed == 1
    assert git(remote, "rev-parse", "main") == git(home, "rev-parse", "HEAD")


def test_failure_while_merging_leaves_no_merge_in_progress(home: Path, other: Path):
    write(other / ALPHA / "CONTEXT.md", "V\n")
    home_sync.sync(other)
    write(home / ALPHA / "CONTEXT.md", "W\n")
    head = git(home, "rev-parse", "HEAD")

    def run(argv, **kwargs):
        if "commit" in argv and any("merge on" in arg for arg in argv):
            raise OSError("disk full")
        return subprocess.run(argv, **kwargs)

    with pytest.raises(OSError):
        home_sync.sync(home, run=run)

    assert no_operation_in_progress(home)
    assert git(home, "rev-parse", "HEAD") != head  # the sync commit stays, unpushed
    assert (home / ALPHA / "CONTEXT.md").read_text(encoding="utf-8") == "W\n"
    assert not list((home / ALPHA).glob("*.sync-conflict-*"))


@pytest.mark.parametrize("abort_fails", [False, True])
def test_failure_after_writing_a_conflict_copy_removes_it(home: Path, other: Path, abort_fails: bool):
    for name in ("a.md", "b.md"):
        write(other / ALPHA / name, "V\n")
        write(home / ALPHA / name, "W\n")
    home_sync.sync(other)
    home_sync.sync(home, push_only=True)  # record the local edits; the push is rejected
    before = tree(home)

    def run(argv, **kwargs):
        if "add" in argv or (abort_fails and "--abort" in argv):  # the first copy is already written
            raise OSError("disk full")
        return subprocess.run(argv, **kwargs)

    with pytest.raises(OSError):
        home_sync.sync(home, run=run)

    assert not list(home.rglob("*.sync-conflict-*"))
    if not abort_fails:
        assert tree(home) == before
        assert no_operation_in_progress(home)


@pytest.mark.parametrize("stem", ["CONTEXT", "context"])
def test_failed_merge_keeps_a_tracked_file_whose_name_a_copy_reused(home: Path, other: Path, stem: str):
    if stem == "context" and not (home / ALPHA / "context.md").exists():
        pytest.skip("names differing only in case collide only on a case-insensitive file system")
    taken = ALPHA / f"{stem}.sync-conflict-{TODAY}-{HOST}.md"
    write(home / taken, "committed\n")
    home_sync.sync(home)
    home_sync.sync(other)
    (other / taken).unlink()  # the upstream frees the name the next copy will take
    write(other / ALPHA / "CONTEXT.md", "V\n")
    home_sync.sync(other)
    write(home / ALPHA / "CONTEXT.md", "W\n")
    home_sync.sync(home, push_only=True)
    before = tree(home)

    def run(argv, **kwargs):
        if "add" in argv:
            raise OSError("disk full")
        return subprocess.run(argv, **kwargs)

    with pytest.raises(OSError):
        home_sync.sync(home, run=run)

    assert (home / taken).read_text(encoding="utf-8") == "committed\n"
    assert tree(home) == before
    assert no_operation_in_progress(home)


def test_gitignored_conflict_copy_name_is_still_committed_and_pushed(home: Path, other: Path, remote: Path):
    write(home / ".gitignore", "*.sync-conflict-*\n")
    home_sync.sync(home)
    home_sync.sync(other)
    write(other / ALPHA / "CONTEXT.md", "V's line\n")
    home_sync.sync(other)
    write(home / ALPHA / "CONTEXT.md", "W's line\n")

    report = home_sync.sync(home)

    copy = f"brainspaces/alpha/.brain/CONTEXT.sync-conflict-{TODAY}-{HOST}.md"
    assert report.status == "synced" and report.conflict_copies == [copy] and report.push == "pushed"
    assert copy in git(remote, "ls-tree", "-r", "--name-only", "main").splitlines()
    assert git(remote, "rev-parse", "main") == git(home, "rev-parse", "HEAD")
    assert no_operation_in_progress(home)
    assert home_sync.sync(home).status == "synced"


@pytest.mark.parametrize("hook_name",["pre-merge-commit", "commit-msg"])
def test_failing_merge_commit_hook_aborts_merge(home: Path, other: Path, remote: Path, hook_name: str):
    write(other / ALPHA / "upstream.md", "upstream\n")
    home_sync.sync(other)
    write(home / ALPHA / "local.md", "local\n")
    git(home, "add", "-A")
    git(home, "commit", "-q", "-m", "local edit")
    tip = git(home, "rev-parse", "HEAD")
    remote_tip = git(remote, "rev-parse", "main")
    before = tree(home)
    git_dir = Path(git(home, "rev-parse", "--absolute-git-dir"))
    hook = git_dir / "hooks" / hook_name
    hook.write_bytes(b"#!/bin/sh\necho 'merge hook failed' >&2\nexit 1\n")
    hook.chmod(0o755)

    with pytest.raises(home_sync.SyncError, match="merge hook failed"):
        home_sync.sync(home)

    assert not (git_dir / "MERGE_HEAD").exists()
    assert no_operation_in_progress(home)
    assert git(home, "rev-parse", "HEAD") == tip
    assert git(remote, "rev-parse", "main") == remote_tip
    assert tree(home) == before


def test_unrelated_upstream_history_is_an_error(home: Path, remote: Path):
    git(home, "switch", "-q", "--orphan", "unrelated")
    write(home / "unrelated.md")
    git(home, "add", "-A")
    git(home, "commit", "-q", "-m", "unrelated root")
    git(home, "branch", "--set-upstream-to", "origin/main")
    before = tree(home)
    tip = git(home, "rev-parse", "HEAD")
    remote_tip = git(remote, "rev-parse", "main")

    with pytest.raises(home_sync.SyncError, match="unrelated histories"):
        home_sync.sync(home)

    assert no_operation_in_progress(home)
    assert git(home, "rev-parse", "HEAD") == tip
    assert git(remote, "rev-parse", "main") == remote_tip
    assert tree(home) == before


def test_only_merge_uses_c_locale_and_preserves_inherited_environment(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LC_ALL", "fr_FR.UTF-8")
    monkeypatch.setenv("LANGUAGE", "fr")
    monkeypatch.setenv("DOTBRAIN_TEST_ENV", "inherited")
    calls = []

    def run(argv, **kwargs):
        args = argv[2:]
        calls.append((args, kwargs["env"]))
        return subprocess.CompletedProcess(argv, 1 if args[0] == "merge-base" else 0, "", "")

    report = home_sync.SyncReport()
    home_sync._integrate(tmp_path, tmp_path / ".git", "origin/main", report, run)

    assert report.merged
    assert [args[0] for args, _ in calls] == ["merge-base", "merge"]
    for args, env in calls:
        assert env["LC_ALL"] == ("C" if args[0] == "merge" else "fr_FR.UTF-8")
        assert env["LANGUAGE"] == ("C" if args[0] == "merge" else "fr")
        assert env["DOTBRAIN_TEST_ENV"] == "inherited"
        assert env["GIT_TERMINAL_PROMPT"] == "0"


@pytest.mark.parametrize("diagnostic,merge_started", [
    ("error: unknown option", False),
    ("fatal: refusing to merge unrelated histories", False),
    ("merge hook failed", True),
])
def test_merge_errors_raise_and_abort_only_a_started_merge(tmp_path: Path, diagnostic: str, merge_started: bool):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    calls = []

    def run(argv, **kwargs):
        args = argv[2:]
        calls.append(args)
        if args[0] == "merge-base":
            return subprocess.CompletedProcess(argv, 1, "", "")
        if args[:2] == ["merge", "--abort"]:
            (git_dir / "MERGE_HEAD").unlink()
        elif args[0] == "merge":
            if merge_started:
                write(git_dir / "MERGE_HEAD", "incoming\n")
            return subprocess.CompletedProcess(argv, 1, "", diagnostic)
        return subprocess.CompletedProcess(argv, 0, "", "")

    report = home_sync.SyncReport()
    with pytest.raises(home_sync.SyncError, match=diagnostic):
        home_sync._integrate(tmp_path, git_dir, "origin/main", report, run)
    assert not report.collisions
    assert not (git_dir / "MERGE_HEAD").exists()
    assert (["merge", "--abort"] in calls) == merge_started


def over_limit_edit_against_upstream(home: Path, other: Path, name: str = "CONTEXT.md",
                                     conflict_elsewhere: bool = False) -> bytes:
    """The upstream changes or adds ``name``; this machine holds an over-limit copy of it."""
    write(home / "config.yaml", "sync:\n  max-file-size: 100\n")
    home_sync.sync(home)
    home_sync.sync(other)
    write(other / ALPHA / name, "V\n")
    if conflict_elsewhere:
        write(other / "brainspaces" / "beta" / ".brain" / "CONTEXT.md", "V's line\n")
        write(home / "brainspaces" / "beta" / ".brain" / "CONTEXT.md", "W's line\n")
    home_sync.sync(other)
    local = b"y" * 200
    (home / ALPHA / name).write_bytes(local)
    return local


def assert_left_clean(home: Path, name: str, local: bytes) -> None:
    assert (home / ALPHA / name).read_bytes() == local
    assert git(home, "ls-files", "--unmerged") == ""
    assert git(home, "stash", "list") == ""
    git_dir = Path(git(home, "rev-parse", "--absolute-git-dir"))
    assert not any((git_dir / state).exists() for state in home_sync._IN_PROGRESS)


@pytest.mark.parametrize("case", ["edited", "edited-and-conflict-elsewhere", "untracked-at-added-path"])
def test_uncommitted_over_limit_file_colliding_with_upstream_is_reported(home: Path, other: Path, case: str):
    name = "big.bin" if case == "untracked-at-added-path" else "CONTEXT.md"
    local = over_limit_edit_against_upstream(home, other, name, case == "edited-and-conflict-elsewhere")

    result = runner.invoke(app, ["sync", "--home", str(home), "--json"])

    assert result.exit_code == 1, result.output
    target = json.loads(result.output)["targets"][0]
    assert target["data"]["status"] == "collision"
    assert len(target["data"]["collisions"]) == 1
    assert f"brainspaces/alpha/.brain/{name}" in target["data"]["collisions"][0]
    assert f"brainspaces/alpha/.brain/{name}" in target["errors"][0]
    assert_left_clean(home, name, local)
    assert subprocess.run(["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"], cwd=home).returncode == 1


def test_upstream_file_replacing_directory_with_untracked_file_is_a_collision(home: Path, other: Path,
                                                                           remote: Path):
    directory = ALPHA / "notes"
    write(home / "config.yaml", "sync:\n  max-file-size: 100\n")
    write(home / directory / "tracked.md", "original\n")
    home_sync.sync(home)
    home_sync.sync(other)
    git(other, "rm", "-r", "--", directory.as_posix())
    write(other / directory, "upstream file\n")
    assert home_sync.sync(other).push == "pushed"
    local_path = directory / "local.bin"
    write(home / local_path, "y" * 200)
    before = tree(home)
    tip = git(home, "rev-parse", "HEAD")
    remote_tip = git(remote, "rev-parse", "main")
    status = git(home, "status", "--porcelain")
    diagnostics = []
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        result = subprocess.run(argv, **kwargs)
        if "merge" in argv:
            diagnostics.append(result.stderr or result.stdout)
        return result

    report = home_sync.sync(home, run=run)

    assert report.status == "collision" and report.push == "none"
    assert not report.merged and report.commits == []
    assert report.skipped == [local_path.as_posix()]
    assert report.collisions == diagnostics and len(diagnostics) == 1
    assert "would lose untracked files" in diagnostics[0]
    assert directory.as_posix() in diagnostics[0]
    assert tree(home) == before
    assert git(home, "status", "--porcelain") == status
    assert git(home, "rev-parse", "HEAD") == tip
    assert git(remote, "rev-parse", "main") == remote_tip
    assert not any("push" in call for call in calls)
    assert_left_clean(home, local_path.relative_to(ALPHA).as_posix(), b"y" * 200)


def test_configured_merge_autostash_is_not_used(home: Path, other: Path):
    local = over_limit_edit_against_upstream(home, other)
    git(home, "config", "merge.autoStash", "true")
    tip = git(home, "rev-parse", "HEAD")
    report = home_sync.sync(home)
    assert report.status == "collision" and report.collisions
    assert report.push == "none"
    assert git(home, "rev-parse", "HEAD") == tip
    assert_left_clean(home, "CONTEXT.md", local)


def test_ignored_file_at_upstream_added_path_is_preserved(home: Path, other: Path):
    name = "local.tmp"
    write(other / ALPHA / name, "upstream")
    git(other, "add", "-f", "--", (ALPHA / name).as_posix())
    git(other, "commit", "-q", "-m", "add file")
    git(other, "push", "-q")
    local = b"local ignored bytes"
    (home / ALPHA / name).write_bytes(local)
    tip = git(home, "rev-parse", "HEAD")
    diagnostics = []

    def run(argv, **kwargs):
        result = subprocess.run(argv, **kwargs)
        if "merge" in argv:
            diagnostics.append(result.stderr or result.stdout)
        return result

    report = home_sync.sync(home, run=run)

    assert report.status == "collision" and report.push == "none"
    assert report.collisions == diagnostics
    assert name in report.collisions[0]
    assert git(home, "rev-parse", "HEAD") == tip
    assert_left_clean(home, name, local)


def test_manual_merge_is_blocked_and_not_aborted(home: Path):
    conflict_on_alpha(home)
    assert subprocess.run(["git", "merge", "side"], cwd=home, capture_output=True).returncode != 0
    git_dir = Path(git(home, "rev-parse", "--absolute-git-dir"))
    merge_head = (git_dir / "MERGE_HEAD").read_bytes()
    before = git(home, "ls-files", "--unmerged")

    report = home_sync.sync(home)

    assert report.status == "blocked" and "MERGE_HEAD" in report.blocked_by
    assert (git_dir / "MERGE_HEAD").read_bytes() == merge_head
    assert git(home, "ls-files", "--unmerged") == before


def test_blockers_are_checked_only_after_acquiring_lock(home: Path, monkeypatch):
    holder = home_sync._acquire(lock_path(home))
    assert holder is not None
    monkeypatch.setattr(home_sync, "_blockers", lambda *_: pytest.fail("checked without lock"))
    try:
        assert home_sync.sync(home).status == "locked"
    finally:
        home_sync._release(holder)
