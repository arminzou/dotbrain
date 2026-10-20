"""Home sync: record uncommitted changes in the dotbrain home as sync commits, integrate, push.

The home is one Git repository holding every Brainspace. Sync first commits whatever nobody
committed, one commit per changed Brainspace and one ``home`` commit for the rest, so the working
tree is clean and one project's drafts never hold back another's. A full sync then fetches the
upstream of the current branch and merges it, keeping this machine's version of each contested
file in place and the other machine's beside it as a conflict copy, so no edit is lost. Then it
pushes. Offline, rejected, and remote-less homes are reported, not errors: the commits stay local
until a later sync sends them.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from dotbrain import config, paths

# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]

LOCK_NAME = "dotbrain-sync.lock"
PUSH_TIMEOUT_SECONDS = 20
PUSH_RETRIES = 3  # a full sync re-fetches and re-integrates at most this often after a rejected push
_SSH_OPTIONS = "-o ConnectTimeout=3 -o BatchMode=yes"
_IN_PROGRESS = ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD", "sequencer")


class SyncError(RuntimeError):
    """Git failed in a way sync cannot report as a normal outcome."""


@dataclass
class SyncReport:
    status: str = "synced"  # synced | disabled | locked | blocked | collision
    commits: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # home-relative paths over the size limit
    nested: list[str] = field(default_factory=list)  # nested Git repositories and submodules, never recorded
    push: str = "none"  # pushed | up-to-date | rejected | unreachable | no-upstream | none
    upstream: str | None = None
    pushed: int = 0
    waiting: int = 0  # local commits not on the upstream after the run
    blocked_by: list[str] = field(default_factory=list)  # why recording was refused
    merged: bool = False  # the fetched upstream was integrated by merge (including fast-forward)
    conflict_copies: list[str] = field(default_factory=list)  # home-relative, written beside the original
    attempts: int = 0  # fetch-integrate-push rounds run
    collisions: list[str] = field(default_factory=list)  # raw Git diagnostics for a refused merge; not integrated


def _git(run: Runner, home: Path, *args: str, input: str | None = None, check: bool = True,
         env: dict | None = None, timeout: float | None = None) -> "subprocess.CompletedProcess[str]":
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", **(env or {})}
    result = run(["git", "--literal-pathspecs", *args], cwd=home, env=env, input=input,
                 capture_output=True, encoding="utf-8", check=False, timeout=timeout)
    if check and result.returncode != 0:
        raise SyncError(f"git {args[0]} failed: {(result.stderr or result.stdout).strip()}")
    return result


def _changed_paths(run: Runner, home: Path) -> list[str]:
    """Every uncommitted path the home's ignore rules allow, relative to the home."""
    out = _git(run, home, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    entries = out.split("\0")
    changed: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        changed.append(entry[3:])
        if entry[0] in "RC" and i < len(entries):  # a rename's next entry is its source path
            changed.append(entries[i])
            i += 1
    return sorted(set(changed))


def _group(path: str, data_dir: str) -> tuple[str, str]:
    """(group name, path shown in the message): a Brainspace name or ``home``."""
    parts = path.split("/")
    if len(parts) >= 3 and parts[0] == data_dir and not parts[1].startswith("."):
        inner = parts[2:]
        return parts[1], "/".join(inner[1:] if inner[0] == ".brain" and len(inner) > 1 else inner)
    return "home", path


def _message(prefix: str, files: list[str]) -> str:
    listed = ", ".join(files[:3])
    if len(files) > 3:
        listed += f" and {len(files) - 3} more"
    return prefix + (f" ({listed})" if files else "")


def _too_large(home: Path, path: str, limit: int) -> bool:
    try:
        return os.lstat(home / path).st_size > limit
    except FileNotFoundError:  # deleted: nothing to measure
        return False


def _is_nested_repo(home: Path, path: str) -> bool:
    """An untracked nested repository (listed with a trailing slash) or a submodule's gitlink."""
    full = home / path
    return path.endswith("/") or (full.is_dir() and not full.is_symlink())


def record(home: Path, max_file_size: int,
           run: Runner = subprocess.run) -> tuple[list[str], list[str], list[str]]:
    """Commit uncommitted changes as sync commits. Returns (messages, over-limit paths, nested repos)."""
    # Unstage everything first, so each commit holds exactly the files staged for it. Committing
    # with a pathspec would take working-tree content and could bring back an over-limit file.
    _git(run, home, "reset", "--quiet")
    data_dir = paths.data_dir(home).name
    groups: dict[str, list[tuple[str, str]]] = {}
    skipped: list[str] = []
    nested: list[str] = []
    for path in _changed_paths(run, home):
        if _is_nested_repo(home, path):
            nested.append(path.rstrip("/"))
            continue
        if _too_large(home, path, max_file_size):
            skipped.append(path)
            continue
        name, shown = _group(path, data_dir)
        groups.setdefault(name, []).append((path, shown))
    order = sorted(name for name in groups if name != "home") + (["home"] if "home" in groups else [])
    messages: list[str] = []
    for name in order:
        files = groups[name]
        _git(run, home, "add", "--all", "--pathspec-from-file=-", "--pathspec-file-nul",
             input="\0".join(path for path, _ in files))
        if _git(run, home, "diff", "--cached", "--quiet", check=False).returncode == 0:
            continue  # nothing ended up staged for this group
        message = _message(f"{name}: sync from {platform.node()}", [shown for _, shown in files])
        _git(run, home, "commit", "--quiet", "-m", message)
        messages.append(message)
    return messages, skipped, nested


def _blockers(home: Path, git_dir: Path, run: Runner) -> list[str]:
    """States in which recording would commit conflict markers or commit onto no branch."""
    blockers = [name for name in _IN_PROGRESS if (git_dir / name).exists()]
    if _git(run, home, "ls-files", "--unmerged").stdout.strip():
        blockers.append("unmerged paths")
    if _git(run, home, "symbolic-ref", "--quiet", "HEAD", check=False).returncode != 0:
        blockers.append("detached HEAD")
    return blockers


def _ssh_command(home: Path, run: Runner) -> str:
    """The SSH command Git would use, with options that fail fast instead of hanging."""
    base = os.environ.get("GIT_SSH_COMMAND") or _git(
        run, home, "config", "core.sshCommand", check=False).stdout.strip() or "ssh"
    return f"{base} {_SSH_OPTIONS}"


def _ahead(home: Path, run: Runner) -> int:
    return int(_git(run, home, "rev-list", "--count", "@{upstream}..HEAD").stdout.strip())


def _fetch(home: Path, run: Runner, env: dict) -> bool:
    try:
        return _git(run, home, "fetch", "--quiet", check=False, env=env,
                    timeout=PUSH_TIMEOUT_SECONDS).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _push(home: Path, report: SyncReport, run: Runner, env: dict) -> None:
    ahead = _ahead(home, run)
    if ahead == 0:
        report.push, report.waiting = "up-to-date", 0
        return
    report.waiting = ahead
    try:
        pushed = _git(run, home, "-c", "push.default=upstream", "push", "--quiet", check=False,
                      env=env, timeout=PUSH_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        report.push = "unreachable"
        return
    if pushed.returncode == 0:
        report.push, report.pushed, report.waiting = "pushed", ahead, 0
    else:
        report.push = "rejected" if "rejected]" in pushed.stderr else "unreachable"


def _copy_name(home: Path, path: str) -> str:
    """``dir/NAME.sync-conflict-YYYY-MM-DD-<host>[-n].ext``, split on the file name only."""
    pure = PurePosixPath(path)
    base = f"{pure.stem}.sync-conflict-{date.today().isoformat()}-{platform.node()}"
    n = 1
    while True:
        suffix = "" if n == 1 else f"-{n}"
        name = str(pure.with_name(f"{base}{suffix}{pure.suffix}"))
        if not os.path.lexists(home / name):
            return name
        n += 1


def _unmerged(home: Path, run: Runner) -> dict[str, set[str]]:
    """Each conflicted path with the index stages it holds (1 base, 2 ours, 3 theirs)."""
    stages: dict[str, set[str]] = {}
    for entry in _git(run, home, "ls-files", "--unmerged", "-z").stdout.split("\0"):
        if "\t" in entry:
            info, path = entry.split("\t", 1)
            stages.setdefault(path, set()).add(info.split()[2])
    return stages


def _merge(home: Path, upstream: str, report: SyncReport, run: Runner) -> None:
    """Merge the upstream, settling every conflict without losing either side's content."""
    host = platform.node()
    clean_message = f"sync: merge on {host}, 0 conflict copies"
    merged = _git(run, home, "merge", "--no-edit", "--no-autostash", "--no-overwrite-ignore", "--quiet", "-m",
                  clean_message, upstream, check=False)
    if merged.returncode == 0:
        report.merged = True
        report.commits.append(clean_message)
        return
    stages = _unmerged(home, run)
    if not stages:
        report.status = "collision"
        report.collisions.append(merged.stderr or merged.stdout)
        return
    report.merged = True
    copies: list[str] = []
    for path, present in sorted(stages.items()):
        if {"2", "3"} <= present:  # both changed it: this machine's in place, the other's beside it
            copy = _copy_name(home, path)
            _git(run, home, "checkout", "--theirs", "--", path)
            os.replace(home / path, home / copy)
            _git(run, home, "checkout", "--ours", "--", path)
            _git(run, home, "add", "--", path, copy)
            copies.append(copy)
            report.conflict_copies.append(copy)
        elif present & {"2", "3"}:  # deleted on one side, edited on the other: keep the edit
            _git(run, home, "checkout", "--ours" if "2" in present else "--theirs", "--", path)
            _git(run, home, "add", "--", path)
        else:  # deleted on both sides
            _git(run, home, "rm", "--quiet", "--cached", "--", path)
    message = _message(f"sync: merge on {host}, {len(copies)} conflict copies", copies)
    _git(run, home, "commit", "--quiet", "-m", message)
    report.commits.append(message)


def _integrate(home: Path, git_dir: Path, upstream: str, report: SyncReport, run: Runner) -> None:
    """Merge the fetched upstream, aborting only a merge started by this sync."""
    if _git(run, home, "merge-base", "--is-ancestor", upstream, "HEAD", check=False).returncode == 0:
        return  # nothing new upstream
    if (git_dir / "MERGE_HEAD").exists():
        report.status, report.blocked_by = "blocked", ["MERGE_HEAD"]
        return
    try:
        _merge(home, upstream, report, run)
    except BaseException:
        if (git_dir / "MERGE_HEAD").exists():
            _git(run, home, "merge", "--abort", check=False)
        raise


def _git_dir(home: Path, run: Runner) -> Path:
    result = _git(run, home, "rev-parse", "--show-toplevel", "--absolute-git-dir", check=False)
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) != 2 or Path(lines[0]).resolve() != home.resolve():
        raise SyncError(f"{home} is not the root of a Git repository")
    return Path(lines[1])


def _acquire(lock: Path) -> BinaryIO | None:
    """Take the OS lock on ``lock`` without waiting; return the open file, or None if another
    sync holds it. The file stays in place; the OS drops the lock when its holder exits, however
    it exits, so a dead sync never blocks a later one."""
    handle = open(lock, "ab", buffering=0)
    try:
        handle.seek(0)  # every sync locks the same first byte
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def _release(handle: BinaryIO) -> None:
    if sys.platform == "win32":
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    handle.close()  # closing releases a flock


def sync(home: Path, *, push_only: bool = False, wait_for_lock: float = 0,
         run: Runner = subprocess.run) -> SyncReport:
    """Record sync commits, integrate the upstream unless ``push_only``, and push.

    Never force-pushes or rewrites commits. Only waits for the lock when requested.
    """
    settings = config.load_config(home).sync
    report = SyncReport()
    if not settings.enabled:
        report.status = "disabled"
        return report
    git_dir = _git_dir(home, run)
    deadline = time.monotonic() + wait_for_lock
    lock = _acquire(git_dir / LOCK_NAME)
    while lock is None and time.monotonic() < deadline:
        time.sleep(min(0.1, max(0, deadline - time.monotonic())))
        lock = _acquire(git_dir / LOCK_NAME)
    if lock is None:
        report.status = "locked"
        return report
    try:
        report.blocked_by = _blockers(home, git_dir, run)
        if report.blocked_by:
            report.status = "blocked"
            return report
        report.commits, report.skipped, report.nested = record(home, settings.max_file_size, run)
        upstream = _git(run, home, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}",
                        check=False)
        if upstream.returncode != 0:
            report.push, report.waiting = "no-upstream", len(report.commits)
            return report
        report.upstream = upstream.stdout.strip()
        remote_env = {"GIT_SSH_COMMAND": _ssh_command(home, run)}
        for attempt in range(1, 2 if push_only else 2 + PUSH_RETRIES):
            report.attempts = attempt
            if not push_only:
                if not _fetch(home, run, remote_env):
                    report.push, report.waiting = "unreachable", _ahead(home, run)
                    break
                _integrate(home, git_dir, report.upstream, report, run)
                if report.status == "blocked":
                    break
                if report.collisions:
                    report.status, report.push, report.waiting = "collision", "none", _ahead(home, run)
                    break
            _push(home, report, run, remote_env)
            if report.push != "rejected":
                break
    finally:
        _release(lock)
    return report
