"""SessionStart hook: assemble a wired repo's Brain context.

Pure Python by design. This ran as a packaged bash script until the Windows chain
(PowerShell -> Python -> Git Bash) proved unreliable: locating a real ``bash`` behind
Windows' ``System32`` WSL launcher depends on how Git was installed, and when the
resolver picked the stub the script emitted nothing. Because the hook is fail-open,
that surfaced as a session with no Brain context and no error at all.

Only ``DOTBRAIN.md`` is injected. dotbrain owns that file, so its size is bounded and
guarded by a test. Private AGENTS.md, repository rules and the retrospective are retrieved
for the task, never injected. The shared convention assigns private retrieval to the
lead or sole agent, which passes relevant findings through existing assignments.

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
from pathlib import Path
from typing import BinaryIO, TextIO

from dotbrain import config, paths

CONVENTION_HEADING = "## dotbrain convention"

# Hook stdout over this many bytes is spilled to a file and never reaches the model.
# Measured on Claude Code: 9,961 bytes delivered, 10,010 did not.
PAYLOAD_LIMIT = 10_000

# Session start waits this long for the full sync before falling back to local state.
SESSION_START_SYNC_SECONDS = 10


def repo_root(cwd: Path | None = None) -> Path | None:
    """Return the enclosing git repo root, or None outside one (and with no git)."""

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            check=False,
            encoding="utf-8",
        )
    except OSError:
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
    convention = root / ".brain" / "DOTBRAIN.md"
    if not convention.is_file():
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
        argv = _sync_argv(home, push_only)
        if wait:
            argv += ["--wait-for-lock", str(wait)]
        child = _launch_detached(argv, home)
        if wait:
            child.wait(timeout=wait)
    except subprocess.TimeoutExpired:
        return  # still running: it finishes detached; killing it could strand a merge
    except Exception:  # noqa: BLE001 - a hook must never break the session
        return


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
