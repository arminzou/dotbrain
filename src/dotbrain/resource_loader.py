"""Helpers for packaged dotbrain runtime resources."""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Iterator

RESOURCE_PACKAGE = "dotbrain.resources"


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
        completed = subprocess.run(["bash", str(script), *args], check=False)
    return completed.returncode
