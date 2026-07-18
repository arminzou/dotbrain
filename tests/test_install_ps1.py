"""Static contracts for the native-Windows installer."""

from pathlib import Path


INSTALLER = Path(__file__).resolve().parent.parent / "install.ps1"


def test_beads_path_detection_covers_release_and_go_fallbacks() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    assert "LastInstallPath" in text
    assert 'Join-Path $env:LOCALAPPDATA "Programs\\bd"' in text
    assert "go env GOBIN" in text
    assert "go env GOPATH" in text
    assert 'Test-Path (Join-Path $bdBin "bd.exe")' in text
