"""Generator for ``docs/cli-reference.md``.

The committed page is a fixed-width (80-col) snapshot of ``dotbrain <cmd> --help`` for
every non-hidden command. ``test_cli_reference.py`` regenerates and diffs against the
committed file, failing when the CLI surface drifts. Regenerate with::

    uv run python -m dotbrain._cli_reference
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import typer

from .cli import app

_REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PATH = _REPO_ROOT / "docs" / "cli-reference.md"

_INTRO = "# CLI Reference\n\nReference for the public `dotbrain` CLI.\n\n"


def console_script() -> Path:
    """Locate the installed ``dotbrain`` entry point (next to the venv python)."""
    exe = Path(sys.executable).with_name("dotbrain")
    if exe.exists():
        return exe
    found = shutil.which("dotbrain")
    if found:
        return Path(found)
    raise FileNotFoundError("dotbrain console script not found; install the package first")


def command_paths() -> list[list[str]]:
    """Pre-order, alphabetically-sorted command paths, skipping hidden commands."""
    root = typer.main.get_command(app)

    def walk(cmd: object, path: list[str]) -> list[list[str]]:
        out = [path]
        subs = getattr(cmd, "commands", None)
        if subs:
            for name in sorted(subs):
                sub = subs[name]
                if getattr(sub, "hidden", False):
                    continue
                out += walk(sub, path + [name])
        return out

    return walk(root, [])


# Rich draws Typer's help panels with rounded corners, except where Console.legacy_windows
# is true — a captured pipe on Windows — where box.ROUNDED substitutes the square set. The
# committed doc would otherwise depend on which OS regenerated it, so normalize to square.
_SQUARE_CORNERS = str.maketrans("╭╮╰╯", "┌┐└┘")


def _help(exe: Path, path: list[str]) -> str:
    # PYTHONUTF8 matters beyond decoding: Rich's Console.ascii_only checks whether the captured
    # stdout's encoding starts with "utf" and falls back to ASCII box-drawing characters otherwise.
    # A captured pipe's default encoding on Windows is the legacy ANSI codepage, not UTF-8, unless
    # this is set — so without it, the reference doc's box borders differ only on Windows.
    env = {**os.environ, "COLUMNS": "80", "PYTHONUTF8": "1"}
    result = subprocess.run(
        [str(exe), *path, "--help"],
        capture_output=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    output = result.stdout.rstrip("\n")
    # Click derives its usage-line prog_name from argv[0]'s basename: the installed console
    # script's actual filename, which is "dotbrain" on POSIX but "dotbrain.exe"/"dotbrain.EXE" on
    # Windows. Normalize to the canonical name so the committed doc doesn't depend on platform or
    # installer casing. Match the exact invoked name (extension included), not a bare "dotbrain"
    # substring — the help text itself contains unrelated words like "$DOTBRAIN_HOME".
    if exe.name.lower() != "dotbrain":
        output = re.sub(re.escape(exe.name), "dotbrain", output, flags=re.IGNORECASE)
    output = output.translate(_SQUARE_CORNERS)
    return "\n".join(line.rstrip() for line in output.splitlines())


def render() -> str:
    exe = console_script()
    sections = []
    for path in command_paths():
        suffix = (" " + " ".join(path)) if path else ""
        sections.append(f"## `dotbrain{suffix}`\n\n```text\n{_help(exe, path)}\n```")
    return _INTRO + "\n\n".join(sections) + "\n"


def main() -> None:
    # Rich narrows its console by one column when legacy_windows is on, which it always is
    # for a captured subprocess pipe on Windows. The committed page is therefore the POSIX
    # rendering, and test_cli_reference.py skips on Windows for the same reason. Regenerating
    # here would write an 80-col page as 79 and break CI's ubuntu/macos legs, where the guard
    # actually runs — so refuse rather than write a page this platform cannot validate.
    if sys.platform == "win32":
        raise SystemExit(
            "refusing to regenerate docs/cli-reference.md on Windows: Rich renders panels one "
            "column narrower here, and the committed page is the POSIX rendering that CI "
            "validates. Regenerate under WSL, Linux, or macOS."
        )
    REFERENCE_PATH.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {REFERENCE_PATH}")


if __name__ == "__main__":
    main()
