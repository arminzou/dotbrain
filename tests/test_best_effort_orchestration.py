"""Regression tests for review-found best-effort orchestration behavior."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dotbrain import beads as beads_mod, migrate, paths


def _seed_beads(brainspace: Path, mode: str) -> None:
    beads = brainspace / ".beads"
    beads.mkdir(parents=True)
    (beads / "metadata.json").write_text(json.dumps({"dolt_mode": mode, "backend": "dolt"}))


def _stats_json(total: int) -> str:
    return json.dumps({"schema_version": 1, "summary": {"total_issues": total}})


def _write_server_defaults(dotbrain_home: Path, *projects: str) -> None:
    text = (
        "version: 2\n"
        "beads:\n"
        "  server:\n"
        "    host: 10.0.0.1\n"
        "    port: 3307\n"
        "    user: beads\n"
    )
    if projects:
        text += "projects:\n"
        for name in projects:
            text += f"  {name}:\n    beads:\n      mode: server\n"
    (dotbrain_home / "dotbrain.yaml").write_text(text)


def test_pull_beads_hydrates_metadata_from_dotbrain_defaults(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_server_defaults(dotbrain_home, "myproject")
    # Hydration targets the Brainspace directly, not an adopter repo.
    brainspace = paths.brainspace(dotbrain_home, "myproject")
    beads = brainspace / ".beads"
    beads.mkdir(parents=True)

    pull_calls: list[list[str]] = []

    def record_pull(argv, **kwargs):
        pull_calls.append(list(argv))
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    monkeypatch.setattr(beads_mod.shutil, "which", lambda name: "/bin/bd")
    monkeypatch.setattr(beads_mod.subprocess, "run", record_pull)

    result = beads_mod.pull_beads_for_all(dotbrain_home)

    assert result.pulled == [str(brainspace)]
    assert pull_calls == [
        ["bd", "-C", str(brainspace), "dolt", "test"],
        ["bd", "-C", str(brainspace), "dolt", "pull"],
    ]
    assert not result.warnings
    assert json.loads((beads / "metadata.json").read_text()) == {
        "database": "dolt",
        "backend": "dolt",
        "dolt_mode": "server",
        "dolt_server_host": "10.0.0.1",
        "dolt_server_user": "beads",
        "dolt_database": "myproject",
    }
    assert (beads / "dolt-server.port").read_text() == "3307\n"


def test_pull_beads_hydrates_repo_less_brainspace(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    # Regression (dotbrain-o71): a Brainspace with no wired code repo must still be hydrated.
    _write_server_defaults(dotbrain_home, "brain-only")
    brainspace = paths.brainspace(dotbrain_home, "brain-only")
    beads = brainspace / ".beads"
    beads.mkdir(parents=True)

    monkeypatch.setattr(beads_mod.shutil, "which", lambda name: "/bin/bd")
    monkeypatch.setattr(
        beads_mod.subprocess, "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(list(argv), 0, "", ""),
    )

    result = beads_mod.pull_beads_for_all(dotbrain_home)

    assert result.pulled == [str(brainspace)]
    assert not result.warnings
    metadata = json.loads((beads / "metadata.json").read_text())
    assert metadata["dolt_mode"] == "server"
    assert metadata["dolt_database"] == "brain-only"


def test_pull_beads_creates_missing_beads_dir(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    # .beads is never tracked, so a fresh clone has no directory at all;
    # hydration must create it instead of skipping the Brainspace.
    _write_server_defaults(dotbrain_home, "freshclone")
    brainspace = paths.brainspace(dotbrain_home, "freshclone")
    brainspace.mkdir(parents=True)
    assert not (brainspace / ".beads").exists()

    monkeypatch.setattr(beads_mod.shutil, "which", lambda name: "/bin/bd")
    monkeypatch.setattr(
        beads_mod.subprocess, "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(list(argv), 0, "", ""),
    )

    result = beads_mod.pull_beads_for_all(dotbrain_home)

    assert result.pulled == [str(brainspace)]
    assert not result.warnings
    metadata = json.loads((brainspace / ".beads" / "metadata.json").read_text())
    assert metadata["dolt_mode"] == "server"
    assert metadata["dolt_database"] == "freshclone"


def test_pull_beads_skips_mode_none_project(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\n"
        "beads:\n"
        "  server:\n"
        "    host: 10.0.0.1\n"
        "projects:\n"
        "  notracker:\n"
        "    beads:\n"
        "      mode: none\n"
    )
    brainspace = paths.brainspace(dotbrain_home, "notracker")
    brainspace.mkdir(parents=True)

    monkeypatch.setattr(beads_mod.shutil, "which", lambda name: "/bin/bd")
    monkeypatch.setattr(
        beads_mod.subprocess, "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(list(argv), 0, "", ""),
    )

    result = beads_mod.pull_beads_for_all(dotbrain_home)

    assert result.pulled == []
    assert not (brainspace / ".beads").exists()


def test_pull_beads_uses_declared_database_name(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\n"
        "beads:\n"
        "  server:\n"
        "    host: 10.0.0.1\n"
        "projects:\n"
        "  renamed:\n"
        "    beads:\n"
        "      mode: server\n"
        "      database: legacy_name\n"
    )
    brainspace = paths.brainspace(dotbrain_home, "renamed")
    brainspace.mkdir(parents=True)

    monkeypatch.setattr(beads_mod.shutil, "which", lambda name: "/bin/bd")
    monkeypatch.setattr(
        beads_mod.subprocess, "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(list(argv), 0, "", ""),
    )

    beads_mod.pull_beads_for_all(dotbrain_home)

    metadata = json.loads((brainspace / ".beads" / "metadata.json").read_text())
    assert metadata["dolt_database"] == "legacy_name"


def test_pull_beads_hydrates_declared_embedded_project(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\n"
        "projects:\n"
        "  fork:\n"
        "    beads:\n"
        "      mode: embedded\n"
        "      remote: https://example.com/fork\n"
        "  empty-fork:\n"
        "    beads:\n"
        "      mode: embedded\n"
    )
    fork = paths.brainspace(dotbrain_home, "fork")
    empty_fork = paths.brainspace(dotbrain_home, "empty-fork")
    fork.mkdir(parents=True)
    empty_fork.mkdir(parents=True)

    init_calls: list[tuple[str, str]] = []

    def fake_init_beads(brainspace, project, root, *, remote="", run=None, **kwargs):
        init_calls.append((project, remote))
        (brainspace / ".beads").mkdir(mode=0o700)
        return None

    monkeypatch.setattr(beads_mod.shutil, "which", lambda name: "/bin/bd")
    monkeypatch.setattr(beads_mod, "init_beads", fake_init_beads)
    monkeypatch.setattr(
        beads_mod.subprocess, "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(list(argv), 0, "", ""),
    )

    result = beads_mod.pull_beads_for_all(dotbrain_home)

    assert sorted(init_calls) == [
        ("empty-fork", ""), ("fork", "https://example.com/fork"),
    ]
    assert any("hydrated embedded beads for fork" in log for log in result.logs)
    assert any("empty-fork: declared embedded with no remote" in w for w in result.warnings)


def test_migrate_all_continues_after_project_failure(dotbrain_home: Path):
    bad = paths.brainspace(dotbrain_home, "bad")
    good = paths.brainspace(dotbrain_home, "good")
    _seed_beads(bad, "embedded")
    _seed_beads(good, "embedded")

    def fail_bad_project(argv, *, cwd=None, env=None, check=True):
        if Path(cwd).name == "bad":
            raise RuntimeError("backup sync failed")
        stdout = _stats_json(3) if list(argv) == ["bd", "stats", "--json"] else ""
        return subprocess.CompletedProcess(list(argv), 0, stdout, "")

    results = migrate.migrate_all(
        dotbrain_home=dotbrain_home,
        server_host="h",
        run=fail_bad_project,
    )

    by_project = {result.project: result for result in results}
    assert by_project["bad"].status == "failed"
    assert any("backup sync failed" in warning for warning in by_project["bad"].warnings)
    assert by_project["good"].status == "migrated"
