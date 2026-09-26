from __future__ import annotations

import subprocess

import pytest

from dotbrain import updater


def _release(version: str = "0.4.0") -> dict[str, object]:
    return {"info": {"version": version}}


def _fetcher(responses: dict[str, dict[str, object]]):
    return lambda url: responses[url]


def test_update_installs_pinned_version(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)
    monkeypatch.setattr(updater, "_is_windows", lambda: False)
    calls: list[list[str]] = []

    result = updater.update_cli(
        "0.3.0",
        fetch=_fetcher({updater._PYPI_URL: _release()}),
        run=lambda argv, **kwargs: calls.append(argv) or subprocess.CompletedProcess(argv, 0),
    )

    assert result == "0.4.0"
    assert calls == [["uv", "tool", "install", "--force", "--refresh-package", "dotbrain", "dotbrain==0.4.0"]]


def test_update_is_a_noop_when_current(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)

    result = updater.update_cli("0.4.0", fetch=_fetcher({updater._PYPI_URL: _release()}))

    assert result is None


def test_update_refuses_editable_install(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: True)

    with pytest.raises(updater.UpdateError, match="editable"):
        updater.update_cli("0.3.0")


@pytest.mark.parametrize("release", [
    {"info": {"version": "0.4.0-rc.1"}},
    {"info": {"version": ""}},
    {},
])
def test_update_rejects_non_stable_release(monkeypatch: pytest.MonkeyPatch, release: dict[str, object]):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)

    with pytest.raises(updater.UpdateError, match="stable"):
        updater.update_cli("0.3.0", fetch=_fetcher({updater._PYPI_URL: release}))


def test_update_preserves_existing_cli_on_install_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)
    monkeypatch.setattr(updater, "_is_windows", lambda: False)

    with pytest.raises(updater.UpdateError, match="left unchanged"):
        updater.update_cli(
            "0.3.0",
            fetch=_fetcher({updater._PYPI_URL: _release()}),
            run=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1),
        )


def test_defer_install_detaches_from_the_console(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(
        updater.subprocess,
        "Popen",
        lambda argv, **kwargs: calls.append((argv, kwargs)),
    )

    updater._defer_install(["uv", "tool", "install", "--force", "dotbrain==0.4.0"])

    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[:2] == ["cmd", "/c"]
    assert "uv tool install --force dotbrain==0.4.0" in argv[2]
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["stdout"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.DEVNULL
    expected_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    assert kwargs["creationflags"] == expected_flags


def test_update_defers_install_on_windows(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(updater, "_is_editable_install", lambda: False)
    monkeypatch.setattr(updater, "_is_windows", lambda: True)
    calls: list[list[str]] = []
    monkeypatch.setattr(updater, "_defer_install", calls.append)

    result = updater.update_cli(
        "0.3.0",
        fetch=_fetcher({updater._PYPI_URL: _release()}),
    )

    assert result == "0.4.0"
    assert calls == [["uv", "tool", "install", "--force", "--refresh-package", "dotbrain", "dotbrain==0.4.0"]]
