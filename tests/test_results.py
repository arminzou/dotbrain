import json
from pathlib import Path
import pytest
from conftest import set_fake_home

from typer.testing import CliRunner

from dotbrain import bootstrap
from dotbrain.cli import app

runner = CliRunner()


@pytest.mark.parametrize("command", ["doctor", "skills", "agents"])
@pytest.mark.parametrize("json_output", [False, True])
def test_warning_findings_use_current_severity_and_preserve_success(tmp_path, monkeypatch, command, json_output):
    from dotbrain import doctor

    root = tmp_path / "data"
    brain = root / "brainspaces/example/.brain"
    brain.mkdir(parents=True)
    (brain / "project.yaml").write_text("agents: []\nbeads:\n  mode: none\n", encoding="utf-8")
    if command == "doctor":
        report = doctor.DoctorReport(machine=[doctor.Finding("ok", "git available"),
                                             doctor.Finding("warn", "session unknown", "inspect runtime hooks")])
        monkeypatch.setattr(doctor, "run_doctor", lambda *args, **kwargs: report)
        args = ["doctor"]
        message = "session unknown; inspect runtime hooks"
        scope, project = "machine", None
    else:
        args = [command, "link", "--all"]
        message = "Brain-only project: no checkout assets"
        scope, project = "project", "example"
    args += ["--home", str(root)] + (["--json"] if json_output else [])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert "advisory" not in result.stdout
    if json_output:
        payload = json.loads(result.stdout)
        assert payload["status"] == "success" and payload["errors"] == []
        target, = payload["targets"]
        assert (target["status"], target["scope"], target["project"]) == ("success", scope, project)
        assert target["changes"] == [] and target["errors"] == []
        assert target["findings"] == ([{"severity": "info", "message": "git available"}] if command == "doctor" else []) + [
            {"severity": "warning", "message": message}]
    else:
        if command == "doctor":
            assert "1 warning" in result.stdout
            assert "session unknown" in result.stdout and "Next: inspect runtime hooks" in result.stdout
        else:
            assert f"warning: {message}" in result.stdout


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
    # A packaged subagent reaches Claude Code through the plugin, so use the operator's own agent.
    (root / "agents" / "claude" / "custom.md").write_text("custom")
    (root / "agents" / "agents.yaml").write_text("global: [custom]\n")
    foreign = fake_home / ".claude" / "agents" / "custom.md"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("user owned")
    result = runner.invoke(app, ["bootstrap", "--home", str(root), "--runtime", "claude", "--json"])
    assert result.exit_code == 1, result.output
    assert foreign.read_text() == "user owned"
    assert json.loads(result.stdout)["targets"][0]["errors"]


def test_bootstrap_symlink_privilege_failure_json(tmp_path, fake_home, monkeypatch):
    root = tmp_path / "data"
    bootstrap.ensure_data_root(root)
    (root / "agents" / "claude" / "custom.md").write_text("custom")
    (root / "agents" / "agents.yaml").write_text("global: [custom]\n")
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
