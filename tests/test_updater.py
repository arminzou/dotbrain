from __future__ import annotations

import subprocess

import pytest

from dotbrain import updater


def _release(tag: str = "v0.4.0") -> dict[str, object]:
    return {"tag_name": tag, "draft": False, "prerelease": False}


def _fetcher(responses: dict[str, dict[str, object]]):
    return lambda url: responses[url]


def test_update_installs_release_commit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)
    monkeypatch.setattr(updater, "_is_windows", lambda: False)
    sha = "a" * 40
    calls: list[list[str]] = []

    result = updater.update_cli(
        "0.3.0",
        fetch=_fetcher({
            updater._RELEASE_URL: _release(),
            f"https://api.github.com/repos/{updater.REPOSITORY}/git/ref/tags/v0.4.0": {
                "object": {"type": "commit", "sha": sha},
            },
        }),
        run=lambda argv, **kwargs: calls.append(argv) or subprocess.CompletedProcess(argv, 0),
    )

    assert result == "0.4.0"
    assert calls == [["uv", "tool", "install", "--force", f"git+https://github.com/{updater.REPOSITORY}@{sha}"]]


def test_update_peels_annotated_tag(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)
    monkeypatch.setattr(updater, "_is_windows", lambda: False)
    tag_sha, commit_sha = "b" * 40, "c" * 40

    result = updater.update_cli(
        "0.3.0",
        fetch=_fetcher({
            updater._RELEASE_URL: _release(),
            f"https://api.github.com/repos/{updater.REPOSITORY}/git/ref/tags/v0.4.0": {
                "object": {"type": "tag", "sha": tag_sha},
            },
            f"https://api.github.com/repos/{updater.REPOSITORY}/git/tags/{tag_sha}": {
                "object": {"type": "commit", "sha": commit_sha},
            },
        }),
        run=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0),
    )

    assert result == "0.4.0"


def test_update_is_a_noop_when_current(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)

    result = updater.update_cli("0.4.0", fetch=_fetcher({updater._RELEASE_URL: _release()}))

    assert result is None


def test_update_refuses_editable_install(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: True)

    with pytest.raises(updater.UpdateError, match="editable"):
        updater.update_cli("0.3.0")


@pytest.mark.parametrize("release", [
    {"tag_name": "v0.4.0", "draft": True, "prerelease": False},
    {"tag_name": "v0.4.0-rc.1", "draft": False, "prerelease": True},
    {"tag_name": "main", "draft": False, "prerelease": False},
])
def test_update_rejects_non_stable_release(monkeypatch: pytest.MonkeyPatch, release: dict[str, object]):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)

    with pytest.raises(updater.UpdateError, match="stable"):
        updater.update_cli("0.3.0", fetch=_fetcher({updater._RELEASE_URL: release}))


def test_update_preserves_existing_cli_on_install_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)
    monkeypatch.setattr(updater, "_is_windows", lambda: False)
    sha = "d" * 40

    with pytest.raises(updater.UpdateError, match="left unchanged"):
        updater.update_cli(
            "0.3.0",
            fetch=_fetcher({
                updater._RELEASE_URL: _release(),
                f"https://api.github.com/repos/{updater.REPOSITORY}/git/ref/tags/v0.4.0": {
                    "object": {"type": "commit", "sha": sha},
                },
            }),
            run=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1),
        )


def test_update_defers_install_on_windows(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)
    monkeypatch.setattr(updater, "_is_windows", lambda: True)
    sha = "e" * 40
    calls: list[list[str]] = []
    monkeypatch.setattr(updater, "_defer_install", calls.append)

    result = updater.update_cli(
        "0.3.0",
        fetch=_fetcher({
            updater._RELEASE_URL: _release(),
            f"https://api.github.com/repos/{updater.REPOSITORY}/git/ref/tags/v0.4.0": {
                "object": {"type": "commit", "sha": sha},
            },
        }),
    )

    assert result == "0.4.0"
    assert calls == [["uv", "tool", "install", "--force", f"git+https://github.com/{updater.REPOSITORY}@{sha}"]]
