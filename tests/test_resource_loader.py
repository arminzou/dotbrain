"""Tests for resource_loader.py's bash resolution (Git Bash vs. Windows' WSL-launcher stub)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotbrain import resource_loader


def test_resolve_bash_passes_through_on_posix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(resource_loader.sys, "platform", "linux")
    assert resource_loader.resolve_bash() == "bash"


def test_resolve_bash_prefers_non_system32_bash_on_windows(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(resource_loader.sys, "platform", "win32")
    monkeypatch.setattr(
        resource_loader.shutil, "which",
        lambda name: r"C:\Program Files\Git\bin\bash.exe" if name == "bash" else None,
    )
    assert resource_loader.resolve_bash() == r"C:\Program Files\Git\bin\bash.exe"


def test_resolve_bash_skips_system32_stub_and_derives_from_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    git_root = tmp_path / "Git"
    (git_root / "bin").mkdir(parents=True)
    (git_root / "bin" / "bash.exe").write_text("")
    (git_root / "cmd").mkdir(parents=True)
    git_exe = git_root / "cmd" / "git.exe"
    git_exe.write_text("")

    monkeypatch.setattr(resource_loader.sys, "platform", "win32")

    def fake_which(name: str):
        if name == "bash":
            return r"C:\Windows\System32\bash.exe"
        if name == "git":
            return str(git_exe)
        return None

    monkeypatch.setattr(resource_loader.shutil, "which", fake_which)
    assert resource_loader.resolve_bash() == str(git_root / "bin" / "bash.exe")


def test_resolve_bash_falls_back_to_system32_stub_when_git_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(resource_loader.sys, "platform", "win32")
    monkeypatch.setattr(
        resource_loader.shutil, "which",
        lambda name: r"C:\Windows\System32\bash.exe" if name == "bash" else None,
    )
    assert resource_loader.resolve_bash() == r"C:\Windows\System32\bash.exe"
