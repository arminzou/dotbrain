"""Helpers for packaged dotbrain runtime resources."""

from __future__ import annotations

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
def plugin_tree() -> Iterator[Path]:
    """The shared plugin tree: packaged in a wheel, or the ``plugin/`` tree of a source checkout.

    Each runtime copies only its own files from this root: ``HERMES_PLUGIN_FILES`` or
    ``PI_EXTENSION_FILES``.
    """

    packaged = resource("plugin")
    if packaged.is_dir():
        with as_file(packaged) as resolved:
            yield resolved
        return
    source = Path(__file__).resolve().parents[2] / "plugin"
    if not (source / "plugin.yaml").is_file():
        raise FileNotFoundError("package resource plugin is missing")
    yield source


# The wheel force-includes these from the shared plugin tree; keep pyproject.toml in step.
HERMES_PLUGIN_FILES = ("plugin.yaml", "__init__.py", "skills")
PI_EXTENSION_FILES = ("index.js", "skills")


@contextmanager
def opencode_plugin() -> Iterator[Path]:
    """The OpenCode plugin file: packaged in a wheel, or in the shared ``plugin/`` tree of a source checkout."""

    packaged = resource("opencode/dotbrain.js")
    if packaged.is_file():
        with as_file(packaged) as resolved:
            yield resolved
        return
    source = Path(__file__).resolve().parents[2] / "plugin" / "opencode" / "dotbrain.js"
    if not source.is_file():
        raise FileNotFoundError("package resource opencode/dotbrain.js is missing")
    yield source


@contextmanager
def resource_file(path: str) -> Iterator[Path]:
    """Materialize a packaged resource as a real filesystem path if needed."""

    with as_file(resource(path)) as resolved:
        yield resolved
