"""Doctor diagnoses declared truth without touching project or tracker state."""
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from dotbrain import cli, doctor, paths, projects, skills, subagents
from dotbrain.cli import app


def write(path, content=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_project(root, name="example", repo=None, runtimes=(), mode="none", selected=()):
    brainspace = root / "brainspaces" / name
    declaration = {"agents": list(runtimes), "beads": {"mode": mode}, "skills": list(selected)}
    write(brainspace / ".brain/project.yaml", yaml.safe_dump(declaration))
    write(brainspace / ".repo", str(repo) if repo else "(brain-only)")
    if mode != "none":
        write(brainspace / ".beads/metadata.json", "{}")
    if repo:
        repo.mkdir(parents=True, exist_ok=True)
        (repo / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
        if mode != "none":
            (repo / ".beads").symlink_to(brainspace / ".beads", target_is_directory=True)
        for runtime in runtimes:
            (repo / f".{runtime}").mkdir()
        write(repo / ".git/info/exclude", "/.brain\n" + ("/.beads\n" if mode != "none" else ""))
    return brainspace


def recording_run(repo, calls, failure=None):
    def run(argv, **kwargs):
        recorded = {key: value for key, value in kwargs.items() if key != "env"}
        if "env" in kwargs:
            recorded["env"] = {"BEADS_DIR": kwargs["env"]["BEADS_DIR"]}
        calls.append((list(argv), recorded))
        assert kwargs.get("timeout") == doctor.PROBE_TIMEOUT
        if argv[0] == "git":
            output = str(repo if "--show-toplevel" in argv else repo / ".git")
        else:
            if failure:
                return failure(argv, kwargs)
            output = "ready"
        return subprocess.CompletedProcess(argv, 0, output + "\n", "")
    return run


def snapshot(root):
    return {p.relative_to(root).as_posix(): ("link", str(p.readlink())) if p.is_symlink()
            else ("file", p.read_bytes()) if p.is_file() else ("dir",)
            for p in root.rglob("*")}


def errors(findings):
    return [f.message for f in findings if f.status == "error"]


def test_empty_all_checks_machine_once_and_unknown_session_advisories(tmp_path, monkeypatch):
    calls = []
    original = doctor._check_machine
    monkeypatch.setattr(doctor, "_check_machine", lambda root, home: calls.append(root) or original(root, home))
    report = doctor.run_doctor(tmp_path, home=tmp_path / "user", all_projects=True)
    assert calls == [tmp_path] and report.projects == {}
    assert any("no registered projects" in f.message for f in report.machine)
    assert any("session consumption is unknown" in f.suggestion for f in report.machine)
    assert not errors(report.machine)
    assert doctor.as_result(report).status == "success"


def test_disabled_components_do_not_require_bd_node_dolt(tmp_path, monkeypatch):
    root = tmp_path / "home"
    make_project(root)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: "git" if name == "git" else None)
    calls = []
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(tmp_path, calls))
    assert calls == [] and not errors(report.machine) and not errors(report.projects["example"])
    assert any("Brain-only" in f.message for f in report.projects["example"])


def test_named_wrong_brainspace_and_beads_destinations_are_errors(tmp_path):
    root = tmp_path / "home"
    repo = tmp_path / "repo"
    make_project(root, repo=repo, mode="embedded")
    other = make_project(root, "other", mode="embedded")
    for name in (".brain", ".beads"):
        (repo / name).unlink()
        (repo / name).symlink_to(other / name, target_is_directory=True)
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(repo, []))
    found = errors(report.projects["example"])
    assert sum("wrong Brainspace" in message for message in found) == 2


def test_repo_local_override_is_the_diagnosed_checkout(tmp_path):
    root = tmp_path / "home"
    local = tmp_path / "local"
    brainspace = make_project(root, repo=local)
    write(brainspace / ".repo", str(tmp_path / "missing-canonical"))
    write(brainspace / ".repo.local", str(local))
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(local, []))
    assert report.checkouts["example"] == str(local)
    assert not errors(report.projects["example"])


def test_current_nested_checkout_and_shared_excludes(tmp_path):
    root = tmp_path / "home"
    repo = tmp_path / "worktree"
    make_project(root, repo=repo)
    nested = repo / "src/nested"
    nested.mkdir(parents=True)
    calls = []
    report = doctor.run_doctor(root, home=tmp_path / "user", cwd=nested, run=recording_run(repo, calls))
    assert report.checkouts["example"] == str(repo)
    assert not errors(report.projects["example"])
    assert any("--git-common-dir" in argv for argv, _ in calls)
    assert not any(argv[0] == "bd" for argv, _ in calls)


def test_real_worktree_uses_git_shared_excludes_read_only(tmp_path):
    root = tmp_path / "home"
    main = tmp_path / "main"
    main.mkdir()
    subprocess.run(["git", "init", "--quiet", str(main)], check=True)
    subprocess.run(["git", "-C", str(main), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "init"], check=True)
    worktree = tmp_path / "worktree"
    subprocess.run(["git", "-C", str(main), "worktree", "add", "--detach", str(worktree)], check=True, capture_output=True)
    brainspace = make_project(root)
    (worktree / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
    write(brainspace / ".repo", str(main))
    write(main / ".git/info/exclude", "/.brain\n")
    before = snapshot(tmp_path)
    report = doctor.run_doctor(root, home=tmp_path / "user", cwd=worktree)
    assert not errors(report.projects["example"])
    assert report.checkouts["example"] == str(worktree)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("failure", ["timeout", "missing", "nonzero", "called_process"])
def test_bounded_readonly_beads_failures_do_not_stop_other_projects(tmp_path, failure):
    root = tmp_path / "home"
    make_project(root, "failed", mode="server")
    make_project(root, "healthy")
    calls = []
    def fail(argv, kwargs):
        assert "--readonly" in argv
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, 15)
        if failure == "missing":
            raise FileNotFoundError("bd missing")
        if failure == "called_process":
            raise subprocess.CalledProcessError(1, argv, stderr="connection refused")
        return subprocess.CompletedProcess(argv, 1, "", "connection refused")
    before = snapshot(tmp_path)
    report = doctor.run_doctor(root, home=tmp_path / "user", all_projects=True, run=recording_run(tmp_path, calls, fail))
    assert errors(report.projects["failed"]) and not errors(report.projects["healthy"])
    assert len(calls) == 2
    assert all("--readonly" in argv for argv, _ in calls)
    assert all(kwargs["env"]["BEADS_DIR"] == str(root / "brainspaces/failed/.beads") for _, kwargs in calls)
    assert doctor.as_result(report).status == "partial"
    assert snapshot(tmp_path) == before


def test_selected_skill_and_codex_copy_health_no_cache_writes(tmp_path):
    root = tmp_path / "home"
    repo = tmp_path / "repo"
    write(root / "skills/bundle/one/SKILL.md", "skill")
    brainspace = make_project(root, repo=repo, runtimes=("codex",), selected=("bundle",))
    selected_agents = subagents.project_link_set(())
    subagents.link_project_subagents(root, brainspace, (".codex",), selected_agents, workspace_dirs={".codex": repo / ".codex"})
    skills.link_project(root, brainspace, (".codex",), ["bundle"], workspace_dirs={".codex": repo / ".codex"})
    entries = ["/.brain", "/.codex/skills/one"] + [f"/.codex/agents/{name}.toml" for name in selected_agents]
    write(repo / ".git/info/exclude", "\n".join(entries) + "\n")
    # Real-file Codex delivery needs no cache at diagnosis time.
    import shutil
    shutil.rmtree(root / ".cache")
    before = snapshot(tmp_path)
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(repo, []))
    assert not errors(report.projects["example"])
    assert snapshot(tmp_path) == before and not (root / ".cache").exists()
    dest = repo / f".codex/agents/{selected_agents[0]}.toml"
    dest.write_text(dest.read_text() + "# stale\n")
    skill = repo / ".codex/skills/one"
    skill.unlink()
    write(root / "skills/other/SKILL.md")
    skill.symlink_to(root / "skills/other", target_is_directory=True)
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(repo, []))
    assert len(errors(report.projects["example"])) == 2


def test_claude_expected_link_and_global_selections(tmp_path):
    root = tmp_path / "home"
    user = tmp_path / "user"
    write(root / "agents/claude/custom.md", "custom")
    write(root / "agents/agents.yaml", "global: [custom]\n")
    receiver = user / ".claude/agents"
    receiver.mkdir(parents=True)
    (receiver / "custom.md").symlink_to(root / "agents/claude/custom.md")
    make_project(root)
    report = doctor.run_doctor(root, home=user, project="example")
    assert any("no definition for runtime 'codex'" in message for message in errors(report.machine))
    assert not any("custom.md" in message for message in errors(report.machine))
    (receiver / "custom.md").unlink()
    write(receiver / "custom.md", "custom")
    report = doctor.run_doctor(root, home=user, project="example")
    assert any("custom.md" in message for message in errors(report.machine))


def test_missing_asset_sources_and_malformed_project_are_isolated(tmp_path):
    root = tmp_path / "home"
    make_project(root, "missing", repo=tmp_path / "repo", selected=("missing-folder",))
    broken = make_project(root, "broken")
    write(broken / ".brain/project.yaml", "agents: [")
    make_project(root, "healthy")
    report = doctor.run_doctor(root, home=tmp_path / "user", all_projects=True, run=recording_run(tmp_path / "repo", []))
    assert errors(report.projects["missing"]) and errors(report.projects["broken"])
    assert not errors(report.projects["healthy"])


def test_plugin_installed_hook_is_distinct_from_activation(tmp_path):
    install = tmp_path / "plugin"
    write(install / "hooks/hooks.json", json.dumps({"hooks": {"SessionStart": [{"hooks": [{"command": "dotbrain hook session-start"}]}]}}))
    write(tmp_path / ".codex/plugins/installed_plugins.json", json.dumps({"plugins": {"dotbrain@dotbrain": [{"installPath": str(install)}]}}))
    findings = doctor._check_plugin(tmp_path, "codex")
    assert any(f.status == "ok" and "hook files" in f.message for f in findings)
    assert any(f.status == "warn" and "not verified" in f.message for f in findings)


def test_site_node_optional_and_bounded(tmp_path):
    brainspace = tmp_path / "project"
    calls = []
    run = recording_run(tmp_path, calls, lambda argv, kwargs: subprocess.CompletedProcess(argv, 0, "v18.0.0", ""))
    assert doctor._check_brain_site(brainspace, run=run) == [] and calls == []
    (brainspace / ".brain/site").mkdir(parents=True)
    findings = doctor._check_brain_site(brainspace, run=run)
    assert len(calls) == 1 and findings[0].status == "warn"


def test_cli_json_exits_and_outside_selection(tmp_path, monkeypatch):
    root = tmp_path / "home"
    make_project(root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "user"))
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--home", str(root), "--all", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert sum(target["scope"] == "machine" for target in payload["targets"]) == 1
    for flags in ([], ["--project", "missing"], ["--all", "--project", "example"], ["--scope", "global"]):
        result = runner.invoke(app, ["doctor", "--home", str(root), "--json", *flags])
        assert result.exit_code == 2, result.output
        assert json.loads(result.stdout)["status"] == "failure"
    write(root / "config.yaml", "beads: [")
    result = runner.invoke(app, ["doctor", "--home", str(root), "--all", "--json"])
    assert result.exit_code == 1 and json.loads(result.stdout)["status"] != "success"


def test_report_renders_under_legacy_windows_encoding(monkeypatch):
    report = doctor.DoctorReport(machine=[doctor.Finding("warn", "Unicode path \u2603; session unknown")])
    buffer = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", buffer)
    cli._render_doctor(report)
    buffer.flush()
    assert "doctor: success" in buffer.buffer.getvalue().decode("cp1252")


def test_path_resolution_runtime_error_is_a_json_operational_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, "run_doctor", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("symlink loop")))
    result = CliRunner().invoke(app, ["doctor", "--home", str(tmp_path), "--all", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["errors"] == ["symlink loop"]


def test_doctor_help_has_current_selectors():
    result = CliRunner().invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    for option in ("--project", "--all", "--home", "--json"):
        assert option in result.output
    assert "Read-only" in result.output
