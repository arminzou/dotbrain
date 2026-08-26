"""Tests for workflow wire-all and bootstrap server beads metadata."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dotbrain import beads as beads_mod, bootstrap as bs, paths, workflows


# --------------------------------------------------------------------------- wire_all_brainspaces


def _git_runner(calls=None):
    def run(argv, *, cwd=None, env=None, check=True):
        if calls is not None:
            calls.append(list(argv))
        if argv[0] == "git":
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")
    return run


def _make_adopter_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    return path


def test_wire_all_creates_symlinks(dotbrain_home: Path, brainspace: Path,
                                   fake_home: Path, tmp_path: Path):
    repo = _make_adopter_repo(tmp_path / "example")
    (paths.brainspace(dotbrain_home, "example") / ".repo").write_text(
        f"{repo}\n"
    )

    result = workflows.wire_all_projects(
        dotbrain_home, repo_base=tmp_path, home=fake_home, run=_git_runner()
    )

    assert any("example" in log for log in result.logs)
    for link_name in (".brain", ".beads", ".claude"):
        assert (repo / link_name).is_symlink()
    assert (repo / ".codex").is_dir()
    assert not (repo / ".codex").is_symlink()


def test_wire_all_warns_when_repo_missing(dotbrain_home: Path, brainspace: Path,
                                          fake_home: Path, tmp_path: Path):
    result = workflows.wire_all_projects(
        dotbrain_home, repo_base=tmp_path / "nonexistent", home=fake_home, run=_git_runner()
    )
    assert any("no repo found" in w or "not a git repo" in w for w in result.warnings)


def test_wire_all_warns_non_git_repo(dotbrain_home: Path, brainspace: Path,
                                     fake_home: Path, tmp_path: Path):
    repo = tmp_path / "not-a-repo"
    repo.mkdir()
    (paths.brainspace(dotbrain_home, "example") / ".repo").write_text(f"{repo}\n")

    result = workflows.wire_all_projects(
        dotbrain_home, repo_base=tmp_path, home=fake_home, run=_git_runner()
    )
    assert any("not a git repo" in w for w in result.warnings)


# --------------------------------------------------------------------------- ensure_server_beads_metadata


def test_ensure_server_beads_metadata_noop_when_metadata_exists(tmp_path: Path):
    beads = tmp_path / ".beads"
    beads.mkdir()
    (beads / "metadata.json").write_text("{}")

    result = beads_mod.ensure_server_beads_metadata(
        tmp_path, "myproject", server_host="10.0.0.1"
    )

    assert result is None


def test_ensure_server_beads_metadata_noop_when_no_host(tmp_path: Path):
    beads = tmp_path / ".beads"
    beads.mkdir()

    result = beads_mod.ensure_server_beads_metadata(tmp_path, "myproject")

    assert result is None
    assert not (beads / "metadata.json").exists()


def test_ensure_server_beads_metadata_removes_generated_files_when_test_fails(tmp_path: Path):
    beads = tmp_path / ".beads"
    beads.mkdir()

    def fail_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, "", "connection failed")

    with pytest.raises(subprocess.CalledProcessError):
        beads_mod.ensure_server_beads_metadata(
            tmp_path, "myproject", server_host="10.0.0.1", run=fail_run
        )

    assert not (beads / "metadata.json").exists()
    assert not (beads / "dolt-server.port").exists()


def test_ensure_server_beads_metadata_writes_server_metadata(tmp_path: Path):
    beads = tmp_path / ".beads"
    beads.mkdir()
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    result = beads_mod.ensure_server_beads_metadata(
        tmp_path,
        "myproject",
        server_host="10.0.0.1",
        server_port="3307",
        server_user="beads",
        run=fake_run,
    )

    assert result and "hydrated" in result
    assert json.loads((beads / "metadata.json").read_text()) == {
        "database": "dolt",
        "backend": "dolt",
        "dolt_mode": "server",
        "dolt_server_host": "10.0.0.1",
        "dolt_server_user": "beads",
        "dolt_database": "myproject",
    }
    assert (beads / "dolt-server.port").read_text().strip() == "3307"
    assert not (beads / "config.yaml").exists()
    assert ["bd", "-C", str(tmp_path), "dolt", "test"] in calls


def test_wire_all_skips_beads_link_silently_for_mode_none(
    dotbrain_home: Path, brainspace: Path, fake_home: Path, tmp_path: Path
):
    # A declared no-beads project never has a Brainspace .beads; the repos stage
    # must neither warn about it nor create a dangling link.
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\nprojects:\n  example:\n    beads:\n      mode: none\n"
    )
    repo = _make_adopter_repo(tmp_path / "example")
    (paths.brainspace(dotbrain_home, "example") / ".repo").write_text(f"{repo}\n")

    result = workflows.wire_all_projects(
        dotbrain_home, repo_base=tmp_path, home=fake_home, run=_git_runner()
    )

    assert not any(".beads is missing" in w for w in result.warnings)
    assert not (repo / ".beads").exists()
    for link_name in (".brain", ".claude"):
        assert (repo / link_name).is_symlink()
    assert (repo / ".codex").is_dir()
