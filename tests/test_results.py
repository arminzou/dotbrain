import json
from pathlib import Path
import pytest
from conftest import set_fake_home

from typer.testing import CliRunner

from dotbrain import bootstrap
from dotbrain.cli import app

runner = CliRunner()


def test_projects_io_error_is_operational_json_failure(monkeypatch, tmp_path):
    from dotbrain import projects
    def denied(root):
        raise PermissionError("project configuration is unreadable")
    monkeypatch.setattr(projects, "list_projects", denied)
    result = runner.invoke(app, ["projects", "list", "--home", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["errors"] == ["project configuration is unreadable"]


@pytest.fixture(autouse=True)
def sandbox_home(monkeypatch, fake_home):
    set_fake_home(monkeypatch, fake_home)


def test_bootstrap_json_repeat_is_unchanged(tmp_path, fake_home):
    root = tmp_path / "data"
    args = ["bootstrap", "--home", str(root), "--json"]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    assert json.loads(first.stdout)["targets"][0]["changes"]
    second = runner.invoke(app, args)
    assert second.exit_code == 0, second.output
    assert json.loads(second.stdout)["targets"][0]["changes"] == []
    assert second.stderr == ""
    assert not (root / "brainspaces").exists()


def test_bootstrap_invalid_runtime_json_no_writes(tmp_path):
    root = tmp_path / "data"
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--runtime", "invalid", "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["status"] == "failure"
    assert not root.exists()


def test_parser_failure_json():
    result = runner.invoke(app, ["bootstrap", "--obsolete", "--json"])
    assert result.exit_code == 2, result.output
    assert json.loads(result.stdout)["errors"]


def test_bootstrap_escaping_seed_receiver_has_no_writes(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "skills").symlink_to(outside, target_is_directory=True)
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--json"])
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["status"] == "failure"
    assert list(outside.iterdir()) == []
    assert not (root / "config.yaml").exists()
    assert not (root / ".git").exists()


def test_bootstrap_failure_json(monkeypatch, tmp_path):
    def fail(root):
        raise RuntimeError("Install git and retry bootstrap")
    monkeypatch.setattr(bootstrap, "ensure_data_root", fail)
    result = runner.invoke(app, ["bootstrap", "--home", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["targets"][0]["errors"] == ["Install git and retry bootstrap"]


def test_bootstrap_preserves_global_yaml(tmp_path, fake_home):
    root = tmp_path / "data"
    bootstrap.ensure_data_root(root)
    config = root / "skills" / "skills.yaml"
    original = "# keep comment\nunknown: {nested: true}\nglobal_extra: []\n"
    config.write_text(original)
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--json"])
    assert result.exit_code == 0, result.output
    assert config.read_text() == original


def test_bootstrap_foreign_asset_is_preserved_and_failed(tmp_path, fake_home):
    root = tmp_path / "data"
    bootstrap.ensure_data_root(root)
    (root / "agents" / "agents.yaml").write_text("global: [reviewer]\n")
    foreign = fake_home / ".claude" / "agents" / "reviewer.md"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("user owned")
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--runtime", "claude", "--json"])
    assert result.exit_code == 1, result.output
    assert foreign.read_text() == "user owned"
    assert json.loads(result.stdout)["targets"][0]["errors"]


def test_bootstrap_symlink_privilege_failure_json(tmp_path, fake_home, monkeypatch):
    root = tmp_path / "data"
    bootstrap.ensure_data_root(root)
    (root / "agents" / "agents.yaml").write_text("global: [reviewer]\n")
    def denied(self, target, target_is_directory=False):
        exc = OSError("A required privilege is not held by the client")
        exc.winerror = 1314
        raise exc
    monkeypatch.setattr(Path, "symlink_to", denied)
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--runtime", "claude", "--json"])
    assert result.exit_code == 1, result.output
    assert "Developer Mode" in json.loads(result.stdout)["targets"][0]["errors"][0]


@pytest.mark.parametrize("config_path", ["skills/skills.yaml", "agents/agents.yaml"])
def test_bootstrap_malformed_yaml_is_operational_json_failure(tmp_path, config_path):
    root = tmp_path / "data"
    bootstrap.ensure_data_root(root)
    (root / config_path).write_text("targets: [unterminated\n")
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--json"])
    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "failure"
    assert report["targets"][0]["errors"]


@pytest.mark.parametrize("command", ["list", "show"])
def test_projects_malformed_yaml_is_operational_json_failure(tmp_path, command):
    root = tmp_path / "data"
    brain = root / "brainspaces" / "example" / ".brain"
    brain.mkdir(parents=True)
    (brain / "project.yaml").write_text("agents: [unterminated\n")
    args = ["projects", command, "--home", str(root), "--json"]
    if command == "show":
        args.extend(["--project", "example"])
    result = runner.invoke(app, args)
    assert result.exit_code == 1, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "failure"
    if command == "list":
        target, = report["targets"]
        assert target["project"] == "example" and target["status"] == "failure"
        assert target["errors"]
    else:
        assert report["errors"]


@pytest.mark.parametrize("runtime", ["codex", "all"])
def test_bootstrap_missing_subagent_runtime_preserves_destinations(tmp_path, fake_home, runtime):
    root = tmp_path / "data"
    bootstrap.ensure_data_root(root)
    (root / "agents" / "agents.yaml").write_text("global: [custom-agent]\n")
    source = root / "agents" / "claude" / "custom-agent.md"
    source.write_text("custom claude definition")
    codex_dest = fake_home / ".codex" / "agents"
    codex_dest.mkdir(parents=True)
    stale = codex_dest / "stale.toml"
    stale.symlink_to(source)
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--runtime", runtime, "--json"])
    assert result.exit_code == 1, result.output
    errors = json.loads(result.stdout)["targets"][0]["errors"]
    assert any("custom-agent" in error and "codex" in error for error in errors)
    assert stale.is_symlink()
    assert not (fake_home / ".claude" / "agents").exists()
