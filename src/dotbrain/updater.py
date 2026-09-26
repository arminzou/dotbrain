"""Update released dotbrain CLI installations from PyPI."""

from __future__ import annotations

import json
import os
import re
import subprocess
from importlib import metadata
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

PACKAGE = "dotbrain"
_PYPI_URL = f"https://pypi.org/pypi/{PACKAGE}/json"
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
Fetch = Callable[[str], dict[str, Any]]
Run = Callable[..., subprocess.CompletedProcess[str]]


class UpdateError(RuntimeError):
    """The CLI could not safely update itself."""


def update_cli(current_version: str, *, fetch: Fetch | None = None,
               run: Run = subprocess.run) -> str | None:
    """Install the latest stable release, returning its version or ``None`` when current."""
    if _is_editable_install():
        raise UpdateError("editable installs are updated from their checkout; use git pull there")

    fetch = fetch or _fetch_json
    target_version = _latest_version(fetch(_PYPI_URL))
    if _version_parts(target_version) <= _version_parts(current_version):
        return None

    # The version comes from PyPI directly; uv's cached index may not list it yet.
    command = ["uv", "tool", "install", "--force", "--refresh-package", PACKAGE,
               f"{PACKAGE}=={target_version}"]
    if _is_windows():
        _defer_install(command)
        return target_version
    try:
        result = run(command, check=False)
    except FileNotFoundError as exc:
        raise UpdateError("uv is not on PATH; install uv and retry") from exc
    if result.returncode:
        raise UpdateError(f"uv could not install {target_version}; the existing CLI was left unchanged")
    return target_version


def _is_windows() -> bool:
    return os.name == "nt"


def _defer_install(command: list[str]) -> None:
    """Run detached, after this Windows launcher releases its executable lock.

    The child must not share this process's console: otherwise its output and
    lifetime bleed into the caller's shell, and the prompt looks hung until the
    install finishes. It gets a hidden console rather than none: a console-less
    cmd makes Windows open a visible window for each console child it runs.
    """
    script = f"ping -n 2 127.0.0.1 >NUL & {subprocess.list2cmdline(command)}"
    subprocess.Popen(
        ["cmd", "/c", script],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def _is_editable_install() -> bool:
    try:
        distribution = metadata.distribution("dotbrain")
    except metadata.PackageNotFoundError:
        return False
    raw = next(
        (
            distribution.locate_file(path).read_text(encoding="utf-8")
            for path in distribution.files or ()
            if path.name == "direct_url.json"
        ),
        None,
    )
    if not raw:
        return False
    try:
        return bool(json.loads(raw).get("dir_info", {}).get("editable"))
    except (ValueError, AttributeError):
        return False


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "dotbrain"})
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed PyPI URL
            data = json.load(response)
    except (OSError, URLError, ValueError) as exc:
        raise UpdateError("could not reach PyPI to check for updates") from exc
    if not isinstance(data, dict):
        raise UpdateError("PyPI returned an invalid update response")
    return data


def _latest_version(release: dict[str, Any]) -> str:
    info = release.get("info", {}) if isinstance(release.get("info"), dict) else {}
    version = str(info.get("version", ""))
    if not _VERSION_RE.fullmatch(version):
        raise UpdateError("PyPI did not return a stable dotbrain release")
    return version


def _version_parts(version: str) -> tuple[int, int, int]:
    match = _VERSION_RE.fullmatch(version)
    if not match:
        raise UpdateError(f"unsupported installed version: {version}")
    return tuple(int(part) for part in match.groups())
