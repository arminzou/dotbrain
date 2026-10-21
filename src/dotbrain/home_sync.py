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
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Container
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
_SSH_OPTIONS = "-o ConnectTimeout=3 -o BatchMode=yes -o ServerAliveInterval=5 -o ServerAliveCountMax=1"
_DRAIN_SECONDS = 2  # how long to wait for output once a timed-out process tree is killed
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
    collisions: list[str] = field(default_factory=list)  # overlapping nested paths or Git refusal diagnostics


def _kill_tree(proc: subprocess.Popen) -> None:
    if sys.platform == "win32":
        # ponytail: taskkill /T misses descendants whose parent already exited; a Job Object would catch them.
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        proc.kill()  # in case taskkill itself failed
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_bounded(args, *, timeout: float | None = None, **kwargs) -> "subprocess.CompletedProcess[str]":
    """``subprocess.run`` that, on timeout, kills the whole process tree before raising.

    ``subprocess.run`` kills only the direct child and then waits for its pipes, which children
    such as ssh still hold open on Windows, so a stalled fetch or push could block forever.
    """
    if timeout is None:
        return subprocess.run(args, **kwargs)
    input, check = kwargs.pop("input", None), kwargs.pop("check", False)
    if kwargs.pop("capture_output", False):
        kwargs["stdout"] = kwargs["stderr"] = subprocess.PIPE
    if input is not None:
        kwargs["stdin"] = subprocess.PIPE
    if sys.platform != "win32":
        kwargs["start_new_session"] = True  # its own process group, so killpg reaches ssh too
    proc = subprocess.Popen(args, **kwargs)
    try:
        stdout, stderr = proc.communicate(input, timeout=timeout)
    except subprocess.TimeoutExpired as stalled:
        stdout, stderr = stalled.output, stalled.stderr
        _kill_tree(proc)
        try:
            stdout, stderr = proc.communicate(timeout=_DRAIN_SECONDS)
        except subprocess.TimeoutExpired as drained:  # something outside the tree still holds the pipes
            stdout, stderr = drained.output or stdout, drained.stderr or stderr
        raise subprocess.TimeoutExpired(args, timeout, output=stdout, stderr=stderr) from None
    result = subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)
    if check:
        result.check_returncode()
    return result


def _git(run: Runner, home: Path, *args: str, input: str | None = None, check: bool = True,
         env: dict | None = None, timeout: float | None = None) -> "subprocess.CompletedProcess[str]":
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", **(env or {})}
    result = run(["git", "--literal-pathspecs", *args], cwd=home, env=env, input=input,
                 capture_output=True, encoding="utf-8", check=False, timeout=timeout)
    if check and result.returncode != 0:
        raise SyncError(f"git {args[0]} failed: {(result.stderr or result.stdout).strip()}")
    return result


@dataclass
class _State:
    """What one ``git status`` reports about the home before sync changes anything."""
    detached: bool = False
    upstream: str | None = None  # set only when the upstream branch has been fetched at least once
    ahead: int = 0  # local commits not on the upstream, as last fetched
    unmerged: bool = False
    staged: bool = False  # the index differs from HEAD
    changed: list[str] = field(default_factory=list)  # as _changed_paths lists them


def _state(run: Runner, home: Path) -> _State:
    """Branch, upstream, conflicts, staging and changed paths from a single Git call.

    Each Git process costs about 0.1 s on Windows, and sync runs on every session start.
    """
    out = _git(run, home, "status", "--porcelain=v2", "--branch", "-z", "--untracked-files=all").stdout
    state, upstream, counted = _State(), None, False
    changed: set[str] = set()
    entries = iter(out.split("\0"))
    for entry in entries:
        kind = entry[:1]
        if entry.startswith("# branch.head "):
            state.detached = entry.endswith(" (detached)")
        elif entry.startswith("# branch.upstream "):
            upstream = entry.split(" ", 2)[2]
        elif entry.startswith("# branch.ab "):
            counted, state.ahead = True, int(entry.split()[2].lstrip("+"))
        elif kind == "1":  # 1 XY sub mH mI mW hH hI path
            fields = entry.split(" ", 8)
            state.staged |= fields[1][0] != "."
            changed.add(fields[8])
        elif kind == "2":  # a rename or copy: ... X<score> path, then its source as the next entry
            state.staged = True
            changed.add(entry.split(" ", 9)[9])
            changed.add(next(entries, ""))
        elif kind == "u":
            state.unmerged = True
            changed.add(entry.split(" ", 10)[10])
        elif kind == "?":
            changed.add(entry[2:])
    # Without a fetched upstream branch there is nothing to compare or merge, as for no upstream.
    state.upstream = upstream if counted else None
    state.changed = sorted(changed - {""})
    return state


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
    except (FileNotFoundError, NotADirectoryError):  # deleted, or a parent became a file
        return False


def _is_nested_repo(home: Path, path: str) -> bool:
    """A nested repository, submodule, or a file inside one."""
    return _nested_repo_path(home, path) is not None


def _nested_repo_path(home: Path, path: str) -> str | None:
    """Find the repository root even when Git lists its files individually."""
    parts = PurePosixPath(path).parts
    for count in range(1, len(parts) + 1):
        directory = home.joinpath(*parts[:count])
        if os.path.lexists(directory / ".git"):
            return directory.relative_to(home).as_posix()
    full = home / path
    if path.endswith("/") or (full.is_dir() and not full.is_symlink()):
        return path.rstrip("/")  # Git can also list a submodule without a .git entry
    return None


def record(home: Path, max_file_size: int, run: Runner = subprocess.run,
           unstaged: list[str] | None = None) -> tuple[list[str], list[str], list[str]]:
    """Commit uncommitted changes as sync commits. Returns (messages, over-limit paths, nested repos).

    ``unstaged`` is the changed-path list when the caller already knows nothing is staged.
    """
    if unstaged is None:
        # Unstage everything first, so each commit holds exactly the files staged for it. Committing
        # with a pathspec would take working-tree content and could bring back an over-limit file.
        _git(run, home, "reset", "--quiet")
        unstaged = _changed_paths(run, home)
    data_dir = paths.data_dir(home).name
    groups: dict[str, list[tuple[str, str]]] = {}
    skipped: list[str] = []
    nested: list[str] = []
    for path in unstaged:
        repository = _nested_repo_path(home, path)
        if repository is not None:
            if repository not in nested:
                nested.append(repository)
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
        message = _message(f"{name}: sync from {platform.node()}", [shown for _, shown in files])
        committed = _git(run, home, "commit", "--quiet", "-m", message, check=False)
        if committed.returncode != 0:
            if _git(run, home, "diff", "--cached", "--quiet", check=False).returncode == 0:
                continue  # nothing ended up staged for this group
            raise SyncError(f"git commit failed: {(committed.stderr or committed.stdout).strip()}")
        messages.append(message)
    return messages, skipped, nested


def _blockers(git_dir: Path, state: _State) -> list[str]:
    """States in which recording would commit conflict markers or commit onto no branch."""
    blockers = [name for name in _IN_PROGRESS if (git_dir / name).exists()]
    if state.unmerged:
        blockers.append("unmerged paths")
    if state.detached:
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


def _counts(home: Path, run: Runner, upstream: str) -> tuple[int, int]:
    """(behind, ahead): upstream commits HEAD lacks, and local commits the upstream lacks."""
    behind, ahead = _git(run, home, "rev-list", "--left-right", "--count", f"{upstream}...HEAD").stdout.split()
    return int(behind), int(ahead)


def _push(home: Path, report: SyncReport, run: Runner, env: dict, ahead: int | None = None) -> None:
    if ahead is None:
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


def _copy_name(home: Path, path: str, tracked: Container[str] = ()) -> str:
    """``dir/NAME.sync-conflict-YYYY-MM-DD-<host>[-n].ext``, split on the file name only, free in
    the working tree and, casefolded, not in ``tracked``."""
    pure = PurePosixPath(path)
    base = f"{pure.stem}.sync-conflict-{date.today().isoformat()}-{platform.node()}"
    n = 1
    while True:
        suffix = "" if n == 1 else f"-{n}"
        name = str(pure.with_name(f"{base}{suffix}{pure.suffix}"))
        if not os.path.lexists(home / name) and name.casefold() not in tracked:
            return name
        n += 1


def _head_paths(home: Path, run: Runner) -> set[str]:
    """HEAD's files, casefolded: on a case-insensitive file system names differing in case collide."""
    return {path.casefold() for path in _git(run, home, "ls-tree", "-r", "--name-only", "-z", "HEAD").stdout.split("\0")}


def _unmerged(home: Path, run: Runner) -> dict[str, set[str]]:
    """Each conflicted path with the index stages it holds (1 base, 2 ours, 3 theirs)."""
    stages: dict[str, set[str]] = {}
    for entry in _git(run, home, "ls-files", "--unmerged", "-z").stdout.split("\0"):
        if "\t" in entry:
            info, path = entry.split("\t", 1)
            stages.setdefault(path, set()).add(info.split()[2])
    return stages


def _merge(home: Path, git_dir: Path, upstream: str, report: SyncReport, run: Runner, copies: list[str]) -> None:
    """Merge the upstream, settling every conflict without losing either side's content.
    Each conflict copy is added to ``copies`` as soon as it is written."""
    host = platform.node()
    clean_message = f"sync: merge on {host}, 0 conflict copies"
    merged = _git(run, home, "merge", "--ff", "--no-edit", "--no-autostash", "--no-overwrite-ignore", "--quiet", "-m",
                  clean_message, upstream, check=False, env={"LC_ALL": "C", "LANGUAGE": "C"})
    if merged.returncode == 0:
        report.merged = True
        report.commits.append(clean_message)
        return
    stages = _unmerged(home, run)
    if not stages:
        diagnostic = merged.stderr or merged.stdout
        if ((git_dir / "MERGE_HEAD").exists()
                or not any(text in diagnostic for text in ("would be overwritten by merge", "would be removed by merge",
                                                          "would lose untracked files"))):
            raise SyncError(f"git merge failed: {diagnostic.strip()}")
        report.status = "collision"
        report.collisions.append(diagnostic)
        return
    report.merged = True
    # a name HEAD tracks but the upstream deleted is free in the tree, yet an abort must restore it
    tracked = _head_paths(home, run)
    for path, present in sorted(stages.items()):
        if {"2", "3"} <= present:  # both changed it: this machine's in place, the other's beside it
            copy = _copy_name(home, path, tracked)
            _git(run, home, "checkout", "--theirs", "--", path)
            os.replace(home / path, home / copy)
            copies.append(copy)
            report.conflict_copies.append(copy)
            _git(run, home, "checkout", "--ours", "--", path)
            _git(run, home, "add", "-f", "--", path, copy)  # a .gitignore match must not refuse the copy
        elif present & {"2", "3"}:  # deleted on one side, edited on the other: keep the edit
            _git(run, home, "checkout", "--ours" if "2" in present else "--theirs", "--", path)
            _git(run, home, "add", "--", path)
        else:  # deleted on both sides
            _git(run, home, "rm", "--quiet", "--cached", "--", path)
    message = _message(f"sync: merge on {host}, {len(copies)} conflict copies", copies)
    _git(run, home, "commit", "--quiet", "-m", message)
    report.commits.append(message)


def _integrate(home: Path, git_dir: Path, upstream: str, report: SyncReport, run: Runner) -> None:
    """Merge the fetched upstream, which has commits HEAD lacks, aborting only a merge started by this sync."""
    if (git_dir / "MERGE_HEAD").exists():
        report.status, report.blocked_by = "blocked", ["MERGE_HEAD"]
        return
    if report.nested:
        incoming = _git(run, home, "diff", "--name-only", "--no-renames", "-z", f"HEAD...{upstream}").stdout
        report.collisions.extend(path for path in incoming.split("\0") if path and any(
            path == nested or path.startswith(nested + "/") for nested in report.nested))
        if report.collisions:
            report.status = "collision"
            return
    copies: list[str] = []
    try:
        _merge(home, git_dir, upstream, report, run, copies)
    except BaseException:
        if (git_dir / "MERGE_HEAD").exists():
            try:
                _git(run, home, "merge", "--abort", check=False)
            finally:
                # left untracked, the next sync would record and push them; copy names avoid
                # HEAD's files, but still never delete a file HEAD tracks
                tracked = _head_paths(home, run) if copies else set()
                for copy in copies:
                    if copy.casefold() not in tracked:
                        (home / copy).unlink(missing_ok=True)
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
         run: Runner = run_bounded) -> SyncReport:
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
        state = _state(run, home)
        report.blocked_by = _blockers(git_dir, state)
        if report.blocked_by:
            report.status = "blocked"
            return report
        report.commits, report.skipped, report.nested = record(
            home, settings.max_file_size, run, None if state.staged else state.changed)
        if state.upstream is None:
            report.push, report.waiting = "no-upstream", len(report.commits)
            return report
        report.upstream = state.upstream
        remote_env = {"GIT_SSH_COMMAND": _ssh_command(home, run)}
        for attempt in range(1, 2 if push_only else 2 + PUSH_RETRIES):
            report.attempts = attempt
            ahead = None
            if not push_only:
                if not _fetch(home, run, remote_env):
                    report.push, report.waiting = "unreachable", _ahead(home, run)
                    break
                behind, ahead = _counts(home, run, report.upstream)
                if behind:
                    ahead = None  # integrating changes it
                    _integrate(home, git_dir, report.upstream, report, run)
                if report.status == "blocked":
                    break
                if report.collisions:
                    report.status, report.push, report.waiting = "collision", "none", _ahead(home, run)
                    break
            _push(home, report, run, remote_env, ahead)
            if report.push != "rejected":
                break
    finally:
        _release(lock)
    return report
