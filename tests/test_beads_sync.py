"""Hermetic tracker synchronization and CLI contract checks."""
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import beads, config, migrate
from dotbrain.cli import app

runner = CliRunner()


def project(home, name, declaration="beads:\n  mode: embedded\n"):
    root = home / "brainspaces" / name
    (root / ".brain").mkdir(parents=True)
    (root / ".brain/project.yaml").write_text(declaration, encoding="utf-8")
    return root


def test_sync_preview_no_mutation(tmp_path):
    root = project(tmp_path, "alpha", "beads:\n  mode: embedded\n  remote: https://example.test/tracker\n")
    before = (root / ".brain/project.yaml").read_bytes()
    result = runner.invoke(app, ["beads", "sync", "--project", "alpha", "--home", str(tmp_path), "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["command"] == "beads sync"
    assert "would pull" in str(report)
    assert not (root / ".beads").exists()
    assert (root / ".brain/project.yaml").read_bytes() == before


def test_sync_uses_bounded_injected_runner_and_declared_remote(tmp_path):
    root = project(tmp_path, "custom", "beads:\n  mode: embedded\n  remote: https://example.test/custom\n")
    (root / ".beads").mkdir()
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        stdout = json.dumps([{"name": "chosen", "url": "https://example.test/custom"},
                             {"name": "origin", "url": "https://example.test/wrong"}])
        return subprocess.CompletedProcess(argv, 0, stdout, "")
    result = beads.pull_beads_for_all(tmp_path, run=run, bd_timeout=3)
    assert not result.errors
    assert len(calls) == 2
    assert calls[1][0] == ["bd", "-C", str(root), "dolt", "pull", "--remote", "chosen"]
    assert calls[0][1]["timeout"] == 3
    assert calls[0][1]["env"]["BEADS_DIR"] == str(root / ".beads")


def test_sync_disabled_and_embedded_without_remote_do_not_pull(tmp_path):
    project(tmp_path, "disabled", "beads:\n  mode: none\n")
    root = project(tmp_path, "local")
    (root / ".beads").mkdir()
    def forbidden(*args, **kwargs):
        pytest.fail("must not run a tracker command")
    result = beads.pull_beads_for_all(tmp_path, run=forbidden)
    assert not result.errors
    assert result.pulled == []
    assert {item["project"]: item["status"] for item in result.targets} == {"disabled": "skipped", "local": "success"}


def test_sync_declared_remote_mismatch_fails_without_pulling_other_remote(tmp_path):
    root = project(tmp_path, "alpha", "beads:\n  mode: embedded\n  remote: https://example.test/declared\n")
    (root / ".beads").mkdir()
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, '[{"name":"origin","url":"https://example.test/other"}]', "")
    result = beads.pull_beads_for_all(tmp_path, run=run)
    assert result.targets[0]["status"] == "failure"
    assert "no tracker binding" in result.errors[0]
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["timeout", "process", "invalid-json"])
def test_sync_remote_discovery_failure_never_reaches_pull(tmp_path, failure):
    root = project(tmp_path, "alpha", "beads:\n  mode: embedded\n  remote: https://example.test/declared\n")
    (root / ".beads").mkdir()
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if failure == "process":
            raise subprocess.CalledProcessError(1, argv, stderr="unavailable")
        return subprocess.CompletedProcess(argv, 0, "not JSON", "")
    result = beads.pull_beads_for_all(tmp_path, run=run)
    assert result.targets[0]["status"] == "failure"
    assert result.errors
    assert len(calls) == 1


def test_failed_hydration_stops_target_and_continues_batch(tmp_path):
    project(tmp_path, "bad", "beads:\n  mode: embedded\n  remote: https://example.test/bad\n")
    good = project(tmp_path, "good", "beads:\n  mode: embedded\n  remote: https://example.test/good\n")
    (good / ".beads").mkdir()
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        if argv[:2] == ["bd", "init"]:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        return subprocess.CompletedProcess(argv, 0, '[{"name":"origin","url":"https://example.test/good"}]', "")
    result = beads.pull_beads_for_all(tmp_path, run=run)
    assert len(result.errors) == 1
    assert result.pulled == [str(good)]
    assert len(calls) == 3  # bad target never reaches remote discovery or a pull


def test_server_custom_database_hydration_failure_rolls_back_generated_files(tmp_path):
    root = project(tmp_path, "custom", "beads:\n  mode: server\n  database: legacy-db\n")
    (tmp_path / "config.yaml").write_text("beads:\n  server:\n    host: localhost\n")
    def run(argv, **kwargs):
        meta = json.loads((root / ".beads/metadata.json").read_text())
        assert meta["dolt_database"] == "legacy-db"
        assert kwargs["timeout"] == 20
        raise subprocess.CalledProcessError(1, argv, stderr="unreachable")
    result = beads.pull_beads_for_all(tmp_path, run=run)
    assert result.targets[0]["status"] == "failure"
    assert not (root / ".beads/metadata.json").exists()
    assert not (root / ".beads/dolt-server.port").exists()


def test_cli_partial_batch_truthful_json(tmp_path, monkeypatch):
    project(tmp_path, "bad", "beads:\n  mode: impossible\n")
    project(tmp_path, "good", "beads:\n  mode: none\n")
    result = runner.invoke(app, ["beads", "sync", "--all", "--home", str(tmp_path), "--json"])
    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert report["status"] == "partial"
    assert [item["status"] for item in report["targets"]] == ["failure", "skipped"]


def test_cli_missing_tool_json_failure(tmp_path, monkeypatch):
    project(tmp_path, "alpha")
    monkeypatch.setattr(beads.shutil, "which", lambda _: None)
    result = runner.invoke(app, ["beads", "sync", "--project", "alpha", "--home", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert "not installed" in str(json.loads(result.stdout))


@pytest.mark.parametrize("args", [["beads", "load"], ["migrate-beads"], ["list-beads-db"], ["drop-beads-db", "orphan"], ["beads", "sync", "--name", "alpha"]])
def test_retired_surfaces_rejected(args):
    result = runner.invoke(app, args + ["--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["status"] == "failure"


def test_cli_orphan_database_admin_and_confirmation(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(beads, "drop_remote_beads_database", lambda name, **kwargs: calls.append(name) or "dropped " + name)
    args = ["beads", "drop-db", "orphan", "--home", str(tmp_path), "--server-host", "localhost", "--json"]
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert not calls
    result = runner.invoke(app, args + ["--yes"])
    assert result.exit_code == 0
    assert calls == ["orphan"]
    assert json.loads(result.stdout)["targets"][0]["data"]["database"] == "orphan"


def test_cli_admin_timeout_failure_json(tmp_path, monkeypatch):
    def run(**kwargs):
        raise subprocess.TimeoutExpired("mysql", 20)
    monkeypatch.setattr(beads, "list_remote_beads_databases", run)
    result = runner.invoke(app, ["beads", "list-db", "--home", str(tmp_path), "--server-host", "localhost", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["status"] == "failure"


def test_remote_admin_runner_is_bounded_and_rejects_unsafe_names():
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "Database\norphan\n", "")
    assert beads.list_remote_beads_databases(server_host="localhost", run=run) == ["orphan"]
    assert calls[-1][1]["timeout"] == 20
    beads.drop_remote_beads_database("orphan", server_host="localhost", run=run)
    assert calls[-1][1]["timeout"] == 20
    for name in ("dotbrain", "unsafe;DROP", "../x"):
        with pytest.raises(ValueError):
            beads.drop_remote_beads_database(name, server_host="localhost", run=run)
    assert len(calls) == 2


def test_sync_store_symlink_escape_is_rejected_without_mutation(tmp_path):
    home = tmp_path / "home"
    root = project(home, "alpha", "beads:\n  mode: server\n")
    external = tmp_path / "outside"
    external.mkdir()
    (root / ".beads").symlink_to(external, target_is_directory=True)
    result = beads.pull_beads_for_all(home, run=lambda *a, **k: pytest.fail("no subprocess on invalid store"))
    assert result.targets[0]["status"] == "failure"
    assert list(external.iterdir()) == []


def test_intentional_beads_writes_preserve_unknown_declarations(tmp_path):
    root = project(tmp_path, "p", "agents: []\nexecution:\n  engine: custom\nskills: []\nsubagents: []\npublic_tracker: custom\nbeads:\n  mode: embedded\n  extension:\n    nested: [1, 2]\n")
    import yaml
    before = yaml.safe_load((root / ".brain/project.yaml").read_text())
    config.write_project_config(tmp_path, "p", config.ProjectBeads(mode="server", database="legacy"))
    after = yaml.safe_load((root / ".brain/project.yaml").read_text())
    expected = {**before, "beads": {**before["beads"], "mode": "server", "database": "legacy"}}
    assert after == expected


def test_migration_legacy_cleanup_preserves_other_projects_and_unknown_values(tmp_path):
    root = project(tmp_path, "alpha")
    (tmp_path / "config.yaml").write_text("beads:\n  server:\n    host: localhost\n")
    legacy = tmp_path / "dotbrain.yaml"
    legacy.write_text("version: 2\nunknown: [a, b]\nprojects:\n  alpha:\n    other: keep\n    beads:\n      mode: embedded\n      remote: old\n      extension: keep\n  beta:\n    custom:\n      nested: true\n    beads:\n      mode: none\n")
    config.write_project_config(tmp_path, "alpha", config.ProjectBeads(mode="server", database="alpha"))
    config.remove_legacy_project_beads(tmp_path, "alpha")
    import yaml
    doc = yaml.safe_load(legacy.read_text())
    assert doc["unknown"] == ["a", "b"]
    assert doc["projects"]["alpha"] == {"other": "keep", "beads": {"extension": "keep"}}
    assert doc["projects"]["beta"] == {"custom": {"nested": True}, "beads": {"mode": "none"}}
    assert config.load_project_config(tmp_path, "alpha").mode == "server"
