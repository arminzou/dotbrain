"""SessionStart hook: assemble a wired repo's Brain context.

Pure Python by design. This ran as a packaged bash script until the Windows chain
(PowerShell -> Python -> Git Bash) proved unreliable: locating a real ``bash`` behind
Windows' ``System32`` WSL launcher depends on how Git was installed, and when the
resolver picked the stub the script emitted nothing. Because the hook is fail-open,
that surfaced as a session with no Brain context and no error at all.

Only ``DOTBRAIN.md`` is injected. dotbrain owns that file, so its size is bounded and
guarded by a test. Project knowledge stays in its owning records rather than
in the startup payload.

Output is assembled as bytes and written to ``stdout.buffer`` so the payload is exactly
what ``cat`` produced: no newline translation on Windows, no re-encoding of Brain files.

Beads context is not injected here, and dotbrain installs no hook that does. Agents run
``bd prime`` themselves; an operator who wants it injected adds Beads' own hook with
``bd setup``. This hook therefore does not set ``BEADS_DIR``.

The session hooks also run home sync, in a child process so nothing it prints can reach
stdout. The child is detached (own process group, no inherited stdio) so it outlives the
hook: a headless run tears the hook down as soon as it returns, and a sync killed mid-merge
leaves state every later sync refuses.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from time import monotonic
from pathlib import Path
from typing import BinaryIO, Callable, TextIO

from dotbrain import config, paths

Runner = Callable[..., subprocess.CompletedProcess[str]]
ANTIGRAVITY_GIT_SECONDS = 3.0
CONVENTION_HEADING = "## dotbrain convention"

# Hook stdout over this many bytes is spilled to a file and never reaches the model.
# Measured on Claude Code: 9,961 bytes delivered, 10,010 did not.
PAYLOAD_LIMIT = 10_000

# Session start waits this long for the full sync before falling back to local state.
SESSION_START_SYNC_SECONDS = 10


def repo_root(cwd: Path | None = None, *, timeout: float | None = None,
              run: Runner = subprocess.run) -> Path | None:
    """Return the enclosing git repo root, or None outside one (and with no git)."""

    try:
        completed = run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            check=False,
            encoding="utf-8",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    top = (completed.stdout or "").strip()
    return Path(top) if top else None


def brain_context(cwd: Path | None = None) -> bytes:
    """Build the SessionStart payload for a wired repo; empty bytes when there is no Brain."""

    root = repo_root(cwd)
    if root is None:
        return b""
    return _brain_context_at(root)


def _brain_context_at(root: Path, *, confined: bool = False) -> bytes:
    brain = root / ".brain"
    convention = paths.confined_path(brain, "DOTBRAIN.md") if confined else brain / "DOTBRAIN.md"
    if (confined and convention.is_symlink()) or not convention.is_file():
        return b""

    heading = (CONVENTION_HEADING + "\n\n").encode("utf-8")
    return heading + convention.read_bytes() + b"\n\n"


def emit_brain_context(stream: BinaryIO | None = None, cwd: Path | None = None, output: str = "text") -> None:
    """Write the payload to a binary stream, raw or as JSON ``additional_context``. Fail-open."""

    target = stream if stream is not None else sys.stdout.buffer
    try:
        payload = brain_context(cwd)
    except OSError:
        return
    if not payload:
        return
    if output == "json":
        # Cursor parses hook stdout as JSON and ignores raw text.
        payload = json.dumps({"additional_context": payload.decode("utf-8", "replace")}).encode("utf-8")
    try:
        target.write(payload)
        target.flush()
    except (OSError, ValueError):
        # stdout closed or EPIPE at hook exit must not surface as a hook failure.
        return


def payload_field(key: str, stream: TextIO | None = None) -> str | None:
    """A string field of the hook payload on stdin: SessionStart ``source``, SessionEnd ``reason``."""

    stream = stream if stream is not None else sys.stdin
    try:
        if stream is None or stream.isatty():
            return None
        value = json.loads(stream.read() or "{}").get(key)
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def _sync_argv(home: Path, push_only: bool) -> list[str]:
    # -I keeps the checkout's directory off sys.path, so a stray typer.py there cannot shadow imports.
    argv = [sys.executable, "-I", "-c", "from dotbrain.cli import app; app()", "sync", "--home", str(home)]
    return argv + ["--push-only"] if push_only else argv


def _launch_detached(argv: list[str], cwd: Path) -> subprocess.Popen:
    # CREATE_NO_WINDOW gives the child a hidden console of its own; without any console
    # (DETACHED_PROCESS) every git it runs would open a visible console window.
    detach: dict = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
                    if sys.platform == "win32" else {"start_new_session": True})
    return subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, **detach)


def sync_home(checkout: Path | None = None) -> Path | None:
    """The home to sync: the checkout's ``.brain`` links into it or the checkout is it, and sync is on."""

    home = paths.resolve_dotbrain_home().expanduser().resolve()
    root = repo_root(checkout)
    if root is None:
        return None
    brain = root / ".brain"
    linked = brain.is_symlink() and brain.resolve().is_relative_to(home)
    if not (linked or root.resolve() == home):
        return None
    return home if config.load_config(home).sync.enabled else None


def start_sync(*, push_only: bool = False, wait: float = 0, checkout: Path | None = None) -> None:
    """Start a detached sync, waiting at most ``wait`` seconds for it. Fail-open: never raises."""

    try:
        home = sync_home(checkout)
        if home is None:
            return
        _start_home_sync(home, push_only=push_only, wait=wait)
    except Exception:
        return


def _start_home_sync(home: Path, *, push_only: bool, wait: float) -> None:
    argv = _sync_argv(home, push_only)
    if wait:
        argv += ["--wait-for-lock", str(wait)]
    child = _launch_detached(argv, home)
    if wait:
        child.wait(timeout=wait)


def _antigravity_checkout(payload: object, home: Path, *, run: Runner = subprocess.run) -> Path | None:
    if not isinstance(payload, dict):
        return None
    workspaces = payload.get("workspacePaths")
    candidates = workspaces if isinstance(workspaces, list) else []
    deadline = monotonic() + ANTIGRAVITY_GIT_SECONDS
    seen = set()
    for value in (payload.get("cwd"), *candidates):
        if not isinstance(value, str) or not value or "\0" in value:
            continue
        try:
            directory = Path(value)
            if not directory.is_absolute() or not directory.is_dir():
                continue
            directory = directory.resolve()
            if directory in seen:
                continue
            seen.add(directory)
            remaining = deadline - monotonic()
            if remaining <= 0:
                return None
            root = repo_root(directory, timeout=remaining, run=run)
            if root is None:
                continue
            if monotonic() >= deadline:
                return None
            root = root.resolve()
            if root == home:
                return root
            brain = root / ".brain"
            if not brain.is_symlink() or not brain.is_dir():
                continue
            resolved = brain.resolve()
            project, marker = resolved.relative_to(paths.data_dir(home)).parts
            if marker == ".brain" and resolved == paths.brainspace(home, project) / ".brain":
                return root
        except (OSError, ValueError, RuntimeError):
            continue
    return None


def handle_antigravity_event(event: str, *, stream: BinaryIO | None = None,
                             output: BinaryIO | None = None, run: Runner = subprocess.run) -> int:
    response = {}
    try:
        source = stream if stream is not None else sys.stdin.buffer
        payload = {} if source.isatty() else json.loads(source.read().decode("utf-8") or "{}")
        home = paths.resolve_dotbrain_home().expanduser().resolve()
        root = _antigravity_checkout(payload, home, run=run)
        if root is not None:
            startup = event == "startup"
            try:
                if config.load_config(home).sync.enabled:
                    _start_home_sync(home, push_only=not startup, wait=SESSION_START_SYNC_SECONDS if startup else 0)
            except Exception:
                pass
            if startup and root != home:
                context = _brain_context_at(root, confined=True)
                if context:
                    response = {"injectSteps": [{"systemMessage": {"systemMessage": context.decode("utf-8", "replace")}}]}
    except Exception:
        pass
    try:
        target = output if output is not None else sys.stdout.buffer
        target.write((json.dumps(response) + "\n").encode("utf-8"))
        target.flush()
    except (OSError, ValueError, AttributeError):
        pass
    return 0


EVENTS = ("startup", "resume", "clear", "compaction", "turn-end", "session-end")


def handle_claude_event(event: str) -> None:
    """Handle the Claude protocol, except when Cursor also imports the plugin hooks."""
    if "CURSOR_VERSION" in os.environ:
        return
    if event == "startup" and payload_field("source") == "compact":
        event = "compaction"
    if event == "session-end" and payload_field("reason") == "clear":
        return
    handle_event(event)


def handle_event(event: str, checkout: Path | None = None, output: str = "text") -> None:
    """Run one session event's home sync, then emit the convention when a session (re)starts.

    Session starts (``startup``, ``resume``, ``clear``) wait briefly for a full sync.
    ``compaction`` and ``turn-end`` fire mid-session, so they only record and push: files never
    change under a running agent. ``session-end`` schedules a full sync; a cleared session sends
    ``clear`` instead, whose start sync covers it. Fail-open: never raises.
    """

    if event in ("compaction", "turn-end"):
        start_sync(push_only=True, checkout=checkout)
    elif event == "session-end":
        start_sync(checkout=checkout)
    else:
        start_sync(wait=SESSION_START_SYNC_SECONDS, checkout=checkout)
    if event not in ("turn-end", "session-end"):
        emit_brain_context(cwd=checkout, output=output)
