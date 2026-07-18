"""Helpers for packaged dotbrain runtime resources."""

from __future__ import annotations

import shutil
import subprocess
import sys
from contextlib import contextmanager
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path, PureWindowsPath
from typing import Iterator

RESOURCE_PACKAGE = "dotbrain.resources"


def resolve_bash() -> str:
    """Locate a real bash, preferring Git Bash over Windows' WSL-launcher ``bash.exe`` stub.

    Modern Windows ships a ``System32\\bash.exe`` that launches WSL, present even when no distro
    is installed (it just errors). If that shim resolves ahead of Git Bash on PATH, invoking
    ``bash`` blindly runs the wrong one. Git for Windows installs ``git.exe`` and ``bash.exe`` in
    the same ``bin`` directory, so a working ``git`` is a reliable anchor back to the real bash.

    Uses ``PureWindowsPath`` for the stub check (syntactic only, no filesystem access) so the
    logic is exercised the same way in tests regardless of the host OS running them.
    """
    if sys.platform != "win32":
        return "bash"

    found = shutil.which("bash")
    if found and PureWindowsPath(found).parent.name.lower() != "system32":
        return found

    git_exe = shutil.which("git")
    if git_exe:
        candidate = Path(git_exe).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.is_file():
            return str(candidate)

    return found or "bash"


def resource(path: str) -> Traversable:
    """Return a packaged resource path."""

    current = files(RESOURCE_PACKAGE)
    for part in path.split("/"):
        if part:
            current = current.joinpath(part)
    return current


def iter_resource_files(path: str) -> Iterator[tuple[Path, Traversable]]:
    """Yield ``(relative_path, file)`` entries below a packaged resource dir."""

    root = resource(path)
    if not root.is_dir():
        raise FileNotFoundError(f"package resource {path} is missing")

    def walk(node: Traversable, prefix: Path = Path()) -> Iterator[tuple[Path, Traversable]]:
        for child in sorted(node.iterdir(), key=lambda item: item.name):
            rel = prefix / child.name
            if child.is_dir():
                yield from walk(child, rel)
            elif child.is_file():
                yield rel, child

    yield from walk(root)


@contextmanager
def resource_file(path: str) -> Iterator[Path]:
    """Materialize a packaged resource as a real filesystem path if needed."""

    with as_file(resource(path)) as resolved:
        yield resolved


def run_script(path: str, args: tuple[str, ...] = ()) -> int:
    """Run a packaged shell script and return its exit code."""

    with resource_file(path) as script:
        completed = subprocess.run([resolve_bash(), str(script), *args], check=False)
    return completed.returncode
