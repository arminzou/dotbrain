"""SessionStart hook: assemble a wired repo's Brain context.

Pure Python by design. This ran as a packaged bash script until the Windows chain
(PowerShell -> Python -> Git Bash) proved unreliable: locating a real ``bash`` behind
Windows' ``System32`` WSL launcher depends on how Git was installed, and when the
resolver picked the stub the script emitted nothing. Because the hook is fail-open,
that surfaced as a session with no Brain context and no error at all.

Only ``DOTBRAIN.md`` is injected. dotbrain owns that file, so its size is bounded and
guarded by a test. The project's own ``.brain/AGENTS.md`` is deliberately left out: it
grows with the project and would eventually cross the payload limit, at which point the
runtime spills stdout to a file and the model receives none of it — including the
convention. ``DOTBRAIN.md`` carries a rule telling the agent to read it instead.

Output is assembled as bytes and written to ``stdout.buffer`` so the payload is exactly
what ``cat`` produced: no newline translation on Windows, no re-encoding of Brain files.

Beads context lives in project hooks (``bd prime --hook-json`` on Claude Code,
``bd codex-hook SessionStart`` on Codex), so this hook does not set ``BEADS_DIR``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import BinaryIO

CONVENTION_HEADING = "## dotbrain convention"

# Hook stdout over this many bytes is spilled to a file and never reaches the model.
# Measured on Claude Code: 9,961 bytes delivered, 10,010 did not.
PAYLOAD_LIMIT = 10_000


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


def emit_brain_context(stream: BinaryIO | None = None, cwd: Path | None = None) -> None:
    """Write the payload to a binary stream. Fail-open: never raises, never exits nonzero."""

    target = stream if stream is not None else sys.stdout.buffer
    try:
        payload = brain_context(cwd)
    except OSError:
        return
    if not payload:
        return
    try:
        target.write(payload)
        target.flush()
    except (OSError, ValueError):
        # stdout closed or EPIPE at hook exit must not surface as a hook failure.
        return
