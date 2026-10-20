"""Home sync: record uncommitted changes in the dotbrain home as sync commits, integrate, push.

The home is one Git repository holding every Brainspace. Sync first commits whatever nobody
committed, one commit per changed Brainspace and one ``home`` commit for the rest, so the working
tree is clean and one project's drafts never hold back another's. A full sync then fetches the
upstream of the current branch and replays the unpushed commits onto it; when that conflicts it
merges instead, keeping this machine's version of each contested file in place and the other
machine's beside it as a conflict copy, so no edit is lost. Then it pushes. Offline, rejected, and
remote-less homes are reported, not errors: the commits stay local until a later sync sends them.
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

from dotbrain import config, paths

# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]

LOCK_NAME = "dotbrain-sync.lock"
STALE_LOCK_SECONDS = 600
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
    merged: bool = False  # the replay conflicted, so the upstream was merged instead
    conflict_copies: list[str] = field(default_factory=list)  # home-relative, written beside the original
    attempts: int = 0  # fetch-integrate-push rounds run
    collisions: list[str] = field(default_factory=list)  # uncommitted paths the upstream changes; not integrated


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
        message = _message(name, [shown for _, shown in files])
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


def _remote_env(home: Path, run: Runner) -> dict:
    return {"GIT_SSH_COMMAND": _ssh_command(home, run)}


def _ahead(home: Path, run: Runner) -> int:
    return int(_git(run, home, "rev-list", "--count", "@{upstream}..HEAD").stdout.strip())


def _fetch(home: Path, run: Runner) -> bool:
    try:
        return _git(run, home, "fetch", "--quiet", check=False, env=_remote_env(home, run),
                    timeout=PUSH_TIMEOUT_SECONDS).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def _push(home: Path, report: SyncReport, run: Runner) -> None:
    ahead = _ahead(home, run)
    if ahead == 0:
        report.push, report.waiting = "up-to-date", 0
        return
    report.waiting = ahead
    try:
        pushed = _git(run, home, "-c", "push.default=upstream", "push", "--quiet", check=False,
                      env=_remote_env(home, run), timeout=PUSH_TIMEOUT_SECONDS)
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
    report.merged = True
    merged = _git(run, home, "merge", "--no-edit", "--quiet", "-m",
                  f"sync: merge on {host}, 0 conflict copies", upstream, check=False)
    if merged.returncode == 0:
        report.commits.append(f"sync: merge on {host}, 0 conflict copies")
        return
    stages = _unmerged(home, run)
    if not stages:
        raise SyncError(f"git merge failed: {(merged.stderr or merged.stdout).strip()}")
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
    listed = ", ".join(copies[:3]) + (f" and {len(copies) - 3} more" if len(copies) > 3 else "")
    message = f"sync: merge on {host}, {len(copies)} conflict copies" + (f" ({listed})" if copies else "")
    _git(run, home, "commit", "--quiet", "-m", message)
    report.commits.append(message)


def _collisions(home: Path, upstream: str, left: list[str], run: Runner) -> list[str]:
    """Paths left uncommitted here that the upstream changes or adds, so integrating would
    conflict with them or refuse to overwrite them."""
    if not left:
        return []
    incoming = [path for path in _git(run, home, "diff", "--name-only", "--no-renames", "-z",
                                      f"HEAD...{upstream}").stdout.split("\0") if path]
    return sorted(path for path in left if any(
        path == other or other.startswith(path + "/") or path.startswith(other + "/") for other in incoming))


def _undo_autostash_conflict(home: Path, stages: dict[str, set[str]], run: Runner) -> None:
    """Put this machine's uncommitted bytes back on each path the autostash re-apply conflicted on,
    clear the unmerged entries, and drop the autostash Git left in the stash list."""
    for path, present in stages.items():
        if "3" in present:  # stage 3 is the stashed, uncommitted version
            _git(run, home, "checkout", "--theirs", "--", path)
        else:
            (home / path).unlink(missing_ok=True)
    _git(run, home, "reset", "--quiet", "--", *stages)
    if _git(run, home, "stash", "list", "-1", "--format=%gs", check=False).stdout.strip() == "autostash":
        _git(run, home, "stash", "drop", "--quiet")


def _integrate(home: Path, git_dir: Path, upstream: str, report: SyncReport, run: Runner) -> None:
    """Bring the fetched upstream into the current branch; never leaves a rebase or merge open.

    Integration is skipped, with ``report.collisions`` set, when the upstream changes a path
    that sync left uncommitted here."""
    if _git(run, home, "merge-base", "--is-ancestor", upstream, "HEAD", check=False).returncode == 0:
        return  # nothing new upstream
    report.collisions = _collisions(home, upstream, report.skipped + report.nested, run)
    if report.collisions:
        return
    try:
        # Replaying only rewrites commits the upstream does not have; --autostash because files
        # skipped by the size limit leave the tree dirty.
        rebased = _git(run, home, "rebase", "--autostash", "--quiet", upstream, check=False)
        if rebased.returncode == 0:
            # The rebase can succeed while re-applying the autostash conflicts.
            stages = _unmerged(home, run)
            if stages:
                _undo_autostash_conflict(home, stages, run)
                report.collisions = sorted(stages)
            return
        conflicted = bool(_unmerged(home, run))
        _git(run, home, "rebase", "--abort", check=False)
        if not conflicted:
            raise SyncError(f"git rebase failed: {(rebased.stderr or rebased.stdout).strip()}")
        _merge(home, upstream, report, run)
    except BaseException:
        if (git_dir / "MERGE_HEAD").exists():
            _git(run, home, "merge", "--abort", check=False)
        if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
            _git(run, home, "rebase", "--abort", check=False)
        raise


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
    """Record sync commits, integrate the upstream unless ``push_only``, and push.

    Never force-pushes or rewrites commits already on the upstream: only unpushed commits are
    replayed, and a replay that conflicts becomes a merge.
    """
    settings = config.load_config(home).sync
    report = SyncReport()
    if not settings.enabled:
        report.status = "disabled"
        return report
    git_dir = _git_dir(home, run)
    report.blocked_by = _blockers(home, git_dir, run)
    if report.blocked_by:
        report.status = "blocked"
        return report
    lock = git_dir / LOCK_NAME
    if not _acquire(lock):
        report.status = "locked"
        return report
    try:
        report.commits, report.skipped, report.nested = record(home, settings.max_file_size, run)
        upstream = _git(run, home, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}",
                        check=False)
        if upstream.returncode != 0:
            report.push, report.waiting = "no-upstream", len(report.commits)
            return report
        report.upstream = upstream.stdout.strip()
        for attempt in range(1, 2 if push_only else 2 + PUSH_RETRIES):
            report.attempts = attempt
            if not push_only:
                if not _fetch(home, run):
                    report.push, report.waiting = "unreachable", _ahead(home, run)
                    break
                _integrate(home, git_dir, report.upstream, report, run)
                if report.collisions:
                    report.status, report.push, report.waiting = "collision", "none", _ahead(home, run)
                    break
            _push(home, report, run)
            if report.push != "rejected":
                break
    finally:
        lock.unlink(missing_ok=True)
    return report
