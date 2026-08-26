"""SessionStart hook: assemble a wired repo's Brain context.

Pure Python by design. This ran as a packaged bash script until the Windows chain
(PowerShell -> Python -> Git Bash) proved unreliable: locating a real ``bash`` behind
Windows' ``System32`` WSL launcher depends on how Git was installed, and when the
resolver picked the stub the script emitted nothing. Because the hook is fail-open,
that surfaced as a session with no Brain context and no error at all.

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
PROJECT_HEADING = "## Project brain"


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
    brain = root / ".brain"
    if not brain.is_dir():
        return b""

    parts: list[bytes] = []
    convention = brain / "DOTBRAIN.md"
    if convention.is_file():
        parts.append(f"{CONVENTION_HEADING}\n\n".encode("utf-8"))
        parts.append(convention.read_bytes())
        parts.append(b"\n\n")

    agents = brain / "AGENTS.md"
    if agents.is_file():
        parts.append(f"{PROJECT_HEADING} \u2014 {root.name}\n\n".encode("utf-8"))
        parts.append(agents.read_bytes())
        parts.append(b"\n\n")

    return b"".join(parts)


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
