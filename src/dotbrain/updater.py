"""Update released dotbrain CLI installations from GitHub."""

from __future__ import annotations

import json
import os
import re
import subprocess
from importlib import metadata
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

REPOSITORY = "arminzou/dotbrain"
_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
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
    tag = _release_tag(fetch(_RELEASE_URL))
    target_version = tag[1:]
    if _version_parts(target_version) <= _version_parts(current_version):
        return None

    sha = _tag_sha(tag, fetch)
    command = ["uv", "tool", "install", "--force", f"git+https://github.com/{REPOSITORY}@{sha}"]
    if _is_windows():
        _defer_install(command)
        return target_version
    try:
        result = run(command, check=False)
    except FileNotFoundError as exc:
        raise UpdateError("uv is not on PATH; install uv and retry") from exc
    if result.returncode:
        raise UpdateError(f"uv could not install {tag}; the existing CLI was left unchanged")
    return target_version


def _is_windows() -> bool:
    return os.name == "nt"


def _defer_install(command: list[str]) -> None:
    """Run after this Windows launcher releases its executable lock."""
    subprocess.Popen(
        ["cmd", "/c", f"ping -n 2 127.0.0.1 >NUL & {subprocess.list2cmdline(command)}"],
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
    request = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "dotbrain"})
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed GitHub API URL
            data = json.load(response)
    except (OSError, URLError, ValueError) as exc:
        raise UpdateError("could not reach GitHub to check for updates") from exc
    if not isinstance(data, dict):
        raise UpdateError("GitHub returned an invalid update response")
    return data


def _release_tag(release: dict[str, Any]) -> str:
    tag = str(release.get("tag_name", ""))
    if release.get("draft") or release.get("prerelease") or not _TAG_RE.fullmatch(tag):
        raise UpdateError("GitHub did not return a stable dotbrain release")
    return tag


def _tag_sha(tag: str, fetch: Fetch) -> str:
    ref = fetch(f"https://api.github.com/repos/{REPOSITORY}/git/ref/tags/{tag}")
    target = ref.get("object", {}) if isinstance(ref, dict) else {}
    if target.get("type") == "tag":
        tag_object = fetch(f"https://api.github.com/repos/{REPOSITORY}/git/tags/{target.get('sha', '')}")
        target = tag_object.get("object", {}) if isinstance(tag_object, dict) else {}
    sha = str(target.get("sha", ""))
    if target.get("type") != "commit" or not _SHA_RE.fullmatch(sha):
        raise UpdateError(f"could not resolve {tag} to a commit")
    return sha


def _version_parts(version: str) -> tuple[int, int, int]:
    match = _TAG_RE.fullmatch(f"v{version}")
    if not match:
        raise UpdateError(f"unsupported installed version: {version}")
    return tuple(int(part) for part in match.groups())
