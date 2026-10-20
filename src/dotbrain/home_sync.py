"""Home sync: record uncommitted changes in the dotbrain home as sync commits, then push them.

The home is one Git repository holding every Brainspace. Sync first commits whatever nobody
committed, one commit per changed Brainspace and one ``home`` commit for the rest, so the working
tree is clean and one project's drafts never hold back another's. It then pushes to the upstream
of the current branch. Offline, rejected, and remote-less homes are reported, not errors: the
commits stay local until a later sync sends them.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from dotbrain import config, paths

# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]

LOCK_NAME = "dotbrain-sync.lock"
STALE_LOCK_SECONDS = 600
PUSH_TIMEOUT_SECONDS = 20
_SSH_OPTIONS = "-o ConnectTimeout=3 -o BatchMode=yes"
_IN_PROGRESS = ("MERGE_HEAD", "rebase-merge", "rebase-apply")


class SyncError(RuntimeError):
    """Git failed in a way sync cannot report as a normal outcome."""


@dataclass
class SyncReport:
    status: str = "synced"  # synced | disabled | locked | blocked
    commits: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # home-relative paths over the size limit
    push: str = "none"  # pushed | up-to-date | rejected | unreachable | no-upstream | none
    upstream: str | None = None
    pushed: int = 0
    waiting: int = 0  # local commits not on the upstream after the run
    blocked_by: list[str] = field(default_factory=list)  # merge or rebase state left in the home


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


def _message(name: str, files: list[str]) -> str:
    listed = ", ".join(files[:3])
    if len(files) > 3:
        listed += f" and {len(files) - 3} more"
    return f"{name}: sync from {platform.node()} ({listed})"


def _too_large(home: Path, path: str, limit: int) -> bool:
    try:
        return os.lstat(home / path).st_size > limit
    except FileNotFoundError:  # deleted: nothing to measure
        return False


def record(home: Path, max_file_size: int, run: Runner = subprocess.run) -> tuple[list[str], list[str]]:
    """Commit uncommitted changes as sync commits. Returns (commit messages, skipped paths)."""
    # Unstage everything first, so each commit holds exactly the files staged for it. Committing
    # with a pathspec would take working-tree content and could bring back an over-limit file.
    _git(run, home, "reset", "--quiet")
    data_dir = paths.data_dir(home).name
    groups: dict[str, list[tuple[str, str]]] = {}
    skipped: list[str] = []
    for path in _changed_paths(run, home):
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
        message = _message(name, [shown for _, shown in files])
        _git(run, home, "commit", "--quiet", "-m", message)
        messages.append(message)
    return messages, skipped


def _ssh_command(home: Path, run: Runner) -> str:
    """The SSH command Git would use, with options that fail fast instead of hanging."""
    base = os.environ.get("GIT_SSH_COMMAND") or _git(
        run, home, "config", "core.sshCommand", check=False).stdout.strip() or "ssh"
    return f"{base} {_SSH_OPTIONS}"


def _push(home: Path, report: SyncReport, run: Runner) -> None:
    upstream = _git(run, home, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}",
                    check=False)
    if upstream.returncode != 0:
        report.push = "no-upstream"
        report.waiting = len(report.commits)
        return
    report.upstream = upstream.stdout.strip()
    ahead = int(_git(run, home, "rev-list", "--count", "@{upstream}..HEAD").stdout.strip())
    if ahead == 0:
        report.push = "up-to-date"
        return
    report.waiting = ahead
    try:
        pushed = _git(run, home, "-c", "push.default=upstream", "push", "--quiet", check=False,
                      env={"GIT_SSH_COMMAND": _ssh_command(home, run)}, timeout=PUSH_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        report.push = "unreachable"
        return
    if pushed.returncode == 0:
        report.push, report.pushed, report.waiting = "pushed", ahead, 0
    else:
        report.push = "rejected" if "rejected]" in pushed.stderr else "unreachable"


def _git_dir(home: Path, run: Runner) -> Path:
    result = _git(run, home, "rev-parse", "--show-toplevel", "--absolute-git-dir", check=False)
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) != 2 or Path(lines[0]).resolve() != home.resolve():
        raise SyncError(f"{home} is not the root of a Git repository")
    return Path(lines[1])


def _process_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _lock_is_stale(lock: Path) -> bool:
    """A lock is stale when its owner is gone or it is older than ``STALE_LOCK_SECONDS``."""
    try:
        pid, started = lock.read_text(encoding="utf-8").split()
        return time.time() - float(started) > STALE_LOCK_SECONDS or not _process_alive(int(pid))
    except FileNotFoundError:
        return False
    except ValueError:  # unreadable or half-written: fall back to the file's age
        try:
            return time.time() - lock.stat().st_mtime > STALE_LOCK_SECONDS
        except FileNotFoundError:
            return False


def _acquire(lock: Path) -> bool:
    if _lock_is_stale(lock):
        lock.unlink(missing_ok=True)
    try:
        with open(lock, "x", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{os.getpid()} {time.time()}\n")
    except FileExistsError:
        return False
    return True


def sync(home: Path, *, push_only: bool = False, run: Runner = subprocess.run) -> SyncReport:
    """Record sync commits and push them; never fetches, rewrites, or force-pushes.

    ``push_only`` is the form that never fetches; today both forms record and push only.
    """
    settings = config.load_config(home).sync
    report = SyncReport()
    if not settings.enabled:
        report.status = "disabled"
        return report
    git_dir = _git_dir(home, run)
    report.blocked_by = [name for name in _IN_PROGRESS if (git_dir / name).exists()]
    if report.blocked_by:
        report.status = "blocked"
        return report
    lock = git_dir / LOCK_NAME
    if not _acquire(lock):
        report.status = "locked"
        return report
    try:
        report.commits, report.skipped = record(home, settings.max_file_size, run)
        _push(home, report, run)
    finally:
        lock.unlink(missing_ok=True)
    return report
