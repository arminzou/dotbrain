"""Tests for ``dotbrain beads load``: pull-only tracker materialization.

The load surface hydrates declared beads state and pulls, never mutating repo wiring or hooks.
The central guarantee under test is that ``--dry-run`` reaches no filesystem or ``bd`` write by
construction (unwire-dry-run lesson, 9cfc44f).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import beads as beads_mod
from dotbrain.cli import app

runner = CliRunner()


def _brainspace(dotbrain_home: Path, name: str) -> Path:
    brainspace = dotbrain_home / "brainspaces" / name
    brainspace.mkdir(parents=True, exist_ok=True)
    return brainspace


def _write_server_yaml(dotbrain_home: Path) -> None:
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\nbeads:\n  server:\n    host: 10.0.0.9\n    port: 3308\n"
    )


def _invoke(dotbrain_home: Path, *args: str):
    return runner.invoke(app, list(args), env={"DOTBRAIN_HOME": str(dotbrain_home)})


def test_load_all_dry_run_makes_no_mutation(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_server_yaml(dotbrain_home)
    _brainspace(dotbrain_home, "alpha")
    _brainspace(dotbrain_home, "beta")

    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    def forbidden(*_a, **_k):  # injected Runner: must never fire in dry-run
        raise AssertionError("Runner invoked during dry-run")

    sub_calls: list = []
    monkeypatch.setattr(
        beads_mod.subprocess, "run",
        lambda *a, **k: sub_calls.append((a, k)),
    )

    result = runner.invoke(
        app, ["beads", "load", "--all", "--dry-run"],
        env={"DOTBRAIN_HOME": str(dotbrain_home)},
    )

    assert result.exit_code == 0, result.output
    assert "would pull beads for alpha" in result.output
    assert "would pull beads for beta" in result.output
    # No .beads dir created anywhere, and the pull subprocess never ran.
    assert not (dotbrain_home / "brainspaces" / "alpha" / ".beads").exists()
    assert not (dotbrain_home / "brainspaces" / "beta" / ".beads").exists()
    assert sub_calls == []
    # The injected Runner default would explode if reached; prove it wasn't by re-running engine.
    res = beads_mod.pull_beads_for_all(dotbrain_home, run=forbidden, dry_run=True)
    assert any("would pull beads for alpha" in line for line in res.logs)


def test_load_name_dry_run_previews_only_target(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_server_yaml(dotbrain_home)
    _brainspace(dotbrain_home, "alpha")
    _brainspace(dotbrain_home, "beta")
    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    result = _invoke(dotbrain_home, "beads", "load", "--name", "alpha", "--dry-run")

    assert result.exit_code == 0, result.output
    assert "would pull beads for alpha" in result.output
    assert "beta" not in result.output


def test_engine_projects_filter_pulls_only_target(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    # Already-hydrated embedded stores -> no init, just pulls. Keeps the assertion about pull scope clean.
    (_brainspace(dotbrain_home, "alpha") / ".beads").mkdir()
    (_brainspace(dotbrain_home, "beta") / ".beads").mkdir()
    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    pulled_dirs: list[str] = []

    def fake_run(argv, **_k):
        pulled_dirs.append(argv[2])  # ["bd", "-C", <dir>, "dolt", "pull"]
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(beads_mod.subprocess, "run", fake_run)

    result = beads_mod.pull_beads_for_all(dotbrain_home, projects=["alpha"])

    alpha = str(dotbrain_home / "brainspaces" / "alpha")
    assert pulled_dirs == [alpha]
    assert result.pulled == [alpha]


def test_server_mode_hydrates_without_dolt_pull(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_server_yaml(dotbrain_home)
    brainspace = _brainspace(dotbrain_home, "alpha")
    (brainspace / ".beads").mkdir()
    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    calls: list[list[str]] = []

    def fake_run(argv, **_k):
        calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, stdout="", stderr="")

    monkeypatch.setattr(beads_mod.subprocess, "run", fake_run)

    result = beads_mod.pull_beads_for_all(dotbrain_home, projects=["alpha"])

    assert calls == [["bd", "-C", str(brainspace), "dolt", "test"]]
    assert result.pulled == []
    assert not result.warnings


def test_load_name_unknown_warns(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    _brainspace(dotbrain_home, "alpha")
    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    result = _invoke(dotbrain_home, "beads", "load", "--name", "ghost", "--dry-run")

    assert result.exit_code == 0, result.output
    assert "no Brainspace: brainspaces/ghost" in result.output


def test_load_all_with_name_is_rejected(dotbrain_home: Path):
    result = _invoke(dotbrain_home, "beads", "load", "--all", "--name", "alpha")
    assert result.exit_code == 2
