import io
import json
import os
import subprocess

import pytest
from typer.testing import CliRunner

from dotbrain import adopter_repos, antigravity, assets, doctor, hooks, paths, presentation, projects, resource_loader, runtimes, workflows
from dotbrain.cli import app
from dotbrain.results import CommandResult, TargetResult


def test_bundle(tmp_path):
    assert antigravity.deliver(tmp_path).linked == ["antigravity/plugins/dotbrain"]
    bundle = antigravity.plugin_dir(tmp_path)
    with resource_loader.plugin_tree() as source:
        for relative in resource_loader.ANTIGRAVITY_PLUGIN_FILES:
            if (source / relative).is_file():
                assert (bundle / relative).read_bytes() == (source / relative).read_bytes()
    manifest = json.loads((bundle / ".antigravity-plugin/plugin.json").read_text(encoding="utf-8"))
    assert manifest["logo"] == "assets/dotbrain-icon-dark.png"
    assert {entry.parent.name for entry in (bundle / "skills").glob("*/SKILL.md")} == {
        "wire-brain", "brain-convention", "maintain-brain", "work-graph", "repo-rules"}
    assert antigravity.state(tmp_path) == "current"


@pytest.mark.parametrize("value,expected", [
    (None, "enabled"), ({}, "enabled"), ({"plugins": {}}, "enabled"),
    ({"plugins": {"dotbrain": {}}}, "enabled"),
    ({"plugins": {"dotbrain": {"enabled": True}}}, "enabled"),
    ({"plugins": {"dotbrain": {"enabled": False}}}, "disabled"),
    ([], None), ({"plugins": None}, None), ({"plugins": {"dotbrain": []}}, None),
    ({"plugins": {"dotbrain": {"enabled": 0}}}, None), ("{", None),
])
def test_activation(tmp_path, value, expected):
    if value is not None:
        raw = value if isinstance(value, str) else json.dumps(value)
        (tmp_path / "config.json").write_text(raw, encoding="utf-8-sig")
    if expected is None:
        with pytest.raises(ValueError):
            antigravity.activation(tmp_path)
    else:
        assert antigravity.activation(tmp_path) == expected


def test_global_reconciliation(dotbrain_home, fake_home, monkeypatch):
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name == "antigravity")
    config_dir = fake_home / ".gemini/config"
    bundle = antigravity.plugin_dir(config_dir)
    config_dir.mkdir(parents=True)
    settings = config_dir / "config.json"
    settings.write_text('{"plugins":{"dotbrain":{"enabled":false}}}', encoding="utf-8-sig")
    before = settings.read_bytes()
    (dotbrain_home / "config.yaml").write_text("skills: [misc/discovery-test]\n", encoding="utf-8")

    skipped = assets.link_global(dotbrain_home, "skills", user_home=fake_home)
    assert any("--runtime antigravity" in notice for notice in skipped.notices)
    assert not bundle.exists()
    assert not assets.link_global(dotbrain_home, "skills", "antigravity", user_home=fake_home).warnings
    link = antigravity.skills_dir(config_dir) / "discovery-test"
    assert link.is_symlink()

    hook_file = bundle / "hooks.json"
    hook_file.write_text("{}", encoding="utf-8")
    assert any("antigravity" in f.message and "stale" in f.message
               for f in doctor._check_machine(dotbrain_home, fake_home))
    (dotbrain_home / "config.yaml").write_text("skills: []\n", encoding="utf-8")
    assets.link_global(dotbrain_home, "skills", user_home=fake_home)
    assert not link.is_symlink()
    assert antigravity.state(config_dir) == "current"
    findings = doctor._check_machine(dotbrain_home, fake_home)
    assert any(f.status == "warn" and "antigravity: dotbrain plugin is disabled" in f.message for f in findings)
    settings.write_text("{", encoding="utf-8")
    assert any(f.status == "warn" and "antigravity: plugin check unavailable" in f.message
               for f in doctor._check_machine(dotbrain_home, fake_home))
    settings.write_bytes(before)
    assert workflows.detach_runtime(dotbrain_home, "antigravity", home=fake_home).status == "success"
    assert settings.read_bytes() == before
    assert not bundle.exists()

    bundle.mkdir()
    foreign = bundle / "foreign"
    foreign.write_text("keep", encoding="utf-8")
    assert assets.link_global(dotbrain_home, "skills", "antigravity", user_home=fake_home).warnings
    assert any("not dotbrain's plugin copy" in f.message for f in doctor._check_machine(dotbrain_home, fake_home))
    assert workflows.detach_runtime(dotbrain_home, "antigravity", home=fake_home).status == "success"
    assert foreign.read_text(encoding="utf-8") == "keep"


@pytest.fixture
def project(dotbrain_home, brainspace, disconnected_adopter_repo, monkeypatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = disconnected_adopter_repo
    declaration = brainspace / ".brain/project.yaml"
    declaration.write_text("agents: [antigravity]\nbeads: {mode: none}\nskills: []\n", encoding="utf-8")
    return projects.ProjectTarget("example", brainspace, repo)


@pytest.mark.parametrize("agents", ["codex, antigravity", "antigravity, codex", "codex"])
def test_shared_receiver(project, dotbrain_home, agents):
    repo = project.checkout
    (project.brainspace / ".brain/project.yaml").write_text(
        f"agents: [{agents}]\nbeads: {{mode: none}}\nskills: [misc/discovery-test]\n", encoding="utf-8")
    legacy = repo / ".codex/skills/discovery-test"
    legacy.parent.mkdir(parents=True)
    legacy.symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)
    assert not workflows.wire_project(dotbrain_home=dotbrain_home, repo=repo, project="example", run_beads=False).errors
    receiver = repo / ".agents/skills"
    assert (receiver / "discovery-test").is_symlink()
    assert not legacy.is_symlink()
    assert not assets.link_project(dotbrain_home, project, "skills").linked
    excludes = adopter_repos.git_exclude_file(repo)
    text = excludes.read_text(encoding="utf-8")
    assert text.splitlines().count("/.agents/skills/discovery-test") == 1
    refreshed = workflows.refresh_projects(dotbrain_home, project="example")
    target = refreshed.targets[0]
    assert not target.errors
    assert not any(".agents exists" in item["message"] for item in target.findings)
    (receiver / "discovery-test").unlink()
    findings = doctor._check_project(project, dotbrain_home, adopter_repos._default_run)
    assert sum("discovery-test" in f.message and f.status == "error" for f in findings) == 1
    assets.link_project(dotbrain_home, project, "skills")
    (receiver / "mine").mkdir()
    excludes.write_text(text + "/.agents\n", encoding="utf-8")
    adopter_repos.unwire_repo(repo, dotbrain_home=dotbrain_home)
    assert (receiver / "mine").is_dir()
    assert not (receiver / "discovery-test").is_symlink()
    assert "/.agents" in excludes.read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("relative,kind", [
    (".agents", "symlink"), (".agents/skills", "symlink"),
    pytest.param(".agents", "junction", marks=pytest.mark.skipif(os.name != "nt", reason="Windows junction")),
    pytest.param(".agents/skills", "junction", marks=pytest.mark.skipif(os.name != "nt", reason="Windows junction")),
])
def test_empty_receiver_and_conflicts(project, dotbrain_home, tmp_path, relative, kind):
    repo = project.checkout
    assert not workflows.wire_project(dotbrain_home=dotbrain_home, repo=repo, project="example", run_beads=False).errors
    assert not (repo / ".agents").exists()
    findings = doctor._check_project(project, dotbrain_home, adopter_repos._default_run)
    assert not any(".agents" in f.message and f.status == "error" for f in findings)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    receiver = repo / relative
    receiver.parent.mkdir(parents=True, exist_ok=True)
    if kind == "junction":
        subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/j", str(receiver), str(foreign)],
                       check=True, capture_output=True)
    else:
        receiver.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match="foreign asset directory"):
        assets.link_project(dotbrain_home, project, "skills")
    with pytest.raises(ValueError, match="foreign asset directory"):
        workflows.wire_project(dotbrain_home=dotbrain_home, repo=repo, project="example", run_beads=False)
    assert workflows.refresh_projects(dotbrain_home, project="example").targets[0].errors
    assert any("foreign asset directory" in f.message
               for f in doctor._check_project(project, dotbrain_home, adopter_repos._default_run))
    assert list(foreign.iterdir()) == []


def test_new_wire_checks_shared_receiver_before_writes(dotbrain_home, disconnected_adopter_repo, monkeypatch, tmp_path):
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name == "codex")
    repo = disconnected_adopter_repo
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (repo / ".agents").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match="foreign asset directory"):
        workflows.wire_project(dotbrain_home=dotbrain_home, repo=repo, project="new", run_beads=False)
    assert not (dotbrain_home / "brainspaces/new").exists()
    assert not (repo / ".brain").is_symlink()
    assert list(foreign.iterdir()) == []


def hook(event, payload, **kwargs):
    output = io.BytesIO()
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert hooks.handle_antigravity_event(event, stream=io.BytesIO(raw), output=output, **kwargs) == 0
    assert len(output.getvalue().splitlines()) == 1
    return json.loads(output.getvalue())


def test_hook_lookup_and_sync(project, dotbrain_home, tmp_path, monkeypatch):
    repo = project.checkout
    brain = project.brainspace / ".brain"
    (repo / ".brain").symlink_to(brain)
    convention = brain / "DOTBRAIN.md"
    convention.write_text("caf\u00e9", encoding="utf-8")
    nested = repo / "\u00e9quipe"
    nested.mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / ".brain").mkdir()
    (foreign / ".brain/DOTBRAIN.md").write_text("foreign", encoding="utf-8")
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.chdir(plugin)
    (dotbrain_home / "config.yaml").write_text("sync: {enabled: true}\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(hooks, "_start_home_sync", lambda home, **kwargs: calls.append((home, kwargs)))

    def run(argv, *, cwd, timeout, **kwargs):
        assert 0 < timeout <= 3.0
        return subprocess.CompletedProcess(argv, 0, str(repo if cwd == nested else cwd))

    home = dotbrain_home.resolve()
    result = hook("startup", {"cwd": str(nested), "workspacePaths": [str(home)]}, run=run)
    assert result == {"injectSteps": [{"systemMessage": {"systemMessage": "## dotbrain convention\n\ncaf\u00e9\n\n"}}]}
    assert calls == [(home, {"push_only": False, "wait": hooks.SESSION_START_SYNC_SECONDS})]
    redirected = tmp_path / "redirected"
    redirected.mkdir()
    (redirected / ".brain").symlink_to(foreign / ".brain", target_is_directory=True)
    fallback = {"cwd": str(foreign),
                "workspacePaths": ["relative", str(foreign), str(redirected), str(nested)]}
    assert hook("startup", fallback, run=run) == result
    assert hook("turn-end", fallback, run=run) == {}
    assert calls[-1] == (home, {"push_only": True, "wait": 0})
    assert hook("startup", {"cwd": str(home)}, run=run) == {}
    assert len(calls) == 4
    assert hook("startup", {}, run=run) == {}
    assert len(calls) == 4

    convention.unlink()
    convention.symlink_to(foreign / ".brain/DOTBRAIN.md")
    assert hook("startup", fallback, run=run) == {}
    assert len(calls) == 5


def test_hook_git_budget(project, monkeypatch):
    times = iter((10.0, 10.1, 13.1))
    monkeypatch.setattr(hooks, "monotonic", lambda: next(times))
    calls = []

    def run(argv, *, timeout, **kwargs):
        calls.append(timeout)
        raise subprocess.TimeoutExpired(argv, timeout)

    assert hook("startup", {"cwd": str(project.checkout), "workspacePaths": [str(project.brainspace)]}, run=run) == {}
    assert calls == [pytest.approx(2.9)]


def test_cli_hook_utf8(project, tmp_path, monkeypatch):
    brain = project.brainspace / ".brain"
    (project.checkout / ".brain").symlink_to(brain)
    (brain / "DOTBRAIN.md").write_text("caf\u00e9", encoding="utf-8")
    nested = project.checkout / "\u00e9quipe"
    nested.mkdir()
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["hook", "antigravity", "--event", "startup"],
                               input=json.dumps({"cwd": str(nested)}, ensure_ascii=False).encode("utf-8"))
    assert result.exit_code == 0, result.output
    assert "caf\u00e9" in json.loads(result.stdout)["injectSteps"][0]["systemMessage"]["systemMessage"]


def test_presentation_groups_only_global_changes(capsys):
    presentation.render_operation(CommandResult("skills link", targets=[
        TargetResult(project="example", changes=["linked .agents/skills/one", "linked antigravity/two"])
    ]))
    output = capsys.readouterr().out
    assert output.index("Changes") < output.index(".agents/skills/one") < output.index("Antigravity resources")


def test_missing_command_fallback(tmp_path):
    with resource_loader.plugin_tree() as source:
        entries = json.loads((source / "hooks.json").read_text(encoding="utf-8"))["dotbrain"]
    for name, event in (("SessionStart", "startup"), ("Stop", "turn-end")):
        command = f"dotbrain hook antigravity --event {event} || echo {{}}"
        assert entries[name] == [{"type": "command", "command": command, "timeout": 15}]
        shell = ["cmd.exe", "/d", "/c"] if os.name == "nt" else ["/bin/sh", "-c"]
        result = subprocess.run([*shell, command], cwd=tmp_path, env={**os.environ, "PATH": str(tmp_path)},
                                capture_output=True, text=True, check=True)
        assert result.stdout.strip() == "{}"
