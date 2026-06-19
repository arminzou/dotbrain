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


def _control(dotbrain_root: Path, name: str) -> Path:
    control = dotbrain_root / "projects" / name
    control.mkdir(parents=True, exist_ok=True)
    return control


def _write_server_yaml(dotbrain_root: Path) -> None:
    (dotbrain_root / "dotbrain.yaml").write_text(
        "version: 2\nbeads:\n  server:\n    host: 10.0.0.9\n    port: 3308\n"
    )


def _invoke(dotbrain_root: Path, *args: str):
    return runner.invoke(app, list(args), env={"DOTBRAIN_ROOT": str(dotbrain_root)})


def test_load_all_dry_run_makes_no_mutation(
    dotbrain_root: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_server_yaml(dotbrain_root)
    _control(dotbrain_root, "alpha")
    _control(dotbrain_root, "beta")

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
        env={"DOTBRAIN_ROOT": str(dotbrain_root)},
    )

    assert result.exit_code == 0, result.output
    assert "would pull beads for alpha" in result.output
    assert "would pull beads for beta" in result.output
    # No .beads dir created anywhere, and the pull subprocess never ran.
    assert not (dotbrain_root / "projects" / "alpha" / ".beads").exists()
    assert not (dotbrain_root / "projects" / "beta" / ".beads").exists()
    assert sub_calls == []
    # The injected Runner default would explode if reached; prove it wasn't by re-running engine.
    res = beads_mod.pull_beads_for_all(dotbrain_root, run=forbidden, dry_run=True)
    assert any("would pull beads for alpha" in line for line in res.logs)


def test_load_name_dry_run_previews_only_target(
    dotbrain_root: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_server_yaml(dotbrain_root)
    _control(dotbrain_root, "alpha")
    _control(dotbrain_root, "beta")
    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    result = _invoke(dotbrain_root, "beads", "load", "--name", "alpha", "--dry-run")

    assert result.exit_code == 0, result.output
    assert "would pull beads for alpha" in result.output
    assert "beta" not in result.output


def test_engine_projects_filter_pulls_only_target(
    dotbrain_root: Path, monkeypatch: pytest.MonkeyPatch
):
    # Already-hydrated embedded stores -> no init, just pulls. Keeps the assertion about pull scope clean.
    (_control(dotbrain_root, "alpha") / ".beads").mkdir()
    (_control(dotbrain_root, "beta") / ".beads").mkdir()
    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    pulled_dirs: list[str] = []

    def fake_run(argv, **_k):
        pulled_dirs.append(argv[2])  # ["bd", "-C", <dir>, "dolt", "pull"]
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(beads_mod.subprocess, "run", fake_run)

    result = beads_mod.pull_beads_for_all(dotbrain_root, projects=["alpha"])

    alpha = str(dotbrain_root / "projects" / "alpha")
    assert pulled_dirs == [alpha]
    assert result.pulled == [alpha]


def test_load_name_unknown_warns(
    dotbrain_root: Path, monkeypatch: pytest.MonkeyPatch
):
    _control(dotbrain_root, "alpha")
    monkeypatch.setattr(beads_mod.shutil, "which", lambda _cmd: "/usr/bin/bd")

    result = _invoke(dotbrain_root, "beads", "load", "--name", "ghost", "--dry-run")

    assert result.exit_code == 0, result.output
    assert "no Brainspace: projects/ghost" in result.output


def test_load_all_with_name_is_rejected(dotbrain_root: Path):
    result = _invoke(dotbrain_root, "beads", "load", "--all", "--name", "alpha")
    assert result.exit_code == 2
