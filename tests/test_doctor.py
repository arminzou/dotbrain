"""Doctor diagnoses declared truth without touching project or tracker state."""
import io
import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from typer.testing import CliRunner

from dotbrain import __version__, assets, cli, cursor, doctor, opencode, owned_copy, paths, projects, runtimes, skills, subagents, workflows
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


def plugin_registry(home, version):
    write(home / ".claude/plugins/installed_plugins.json", json.dumps({"plugins": {
        "dotbrain@dotbrain": [{"installPath": str(home / "plugin"), "version": version}]}}))


def test_plugin_version_skew_is_warning_and_names_fix(tmp_path):
    plugin_registry(tmp_path, "0.0.0")
    before = snapshot(tmp_path)
    findings = doctor._check_plugin_version(tmp_path / ".claude")
    assert len(findings) == 1 and findings[0].status == "warn"
    assert "0.0.0" in findings[0].message and __version__ in findings[0].message
    assert "upgrade both" in findings[0].suggestion
    assert doctor.as_result(doctor.DoctorReport(machine=findings)).status == "success"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("registry", [None, "{broken", "{}", '{"plugins": []}',
                                      '{"plugins": {"dotbrain@dotbrain": [{"installPath": "unused"}]}}'])
def test_plugin_version_input_skips(tmp_path, registry):
    if registry is not None:
        write(tmp_path / ".claude/plugins/installed_plugins.json", registry)
    findings = doctor._check_plugin_version(tmp_path / ".claude")
    assert findings[0].status == "info" and "skipped" in findings[0].message
    assert "unavailable" in findings[0].message


def test_plugin_version_reads_the_configured_claude_profile(tmp_path):
    root, home, profile = tmp_path / "root", tmp_path / "home", tmp_path / "work-profile"
    write(root / "config.yaml", f"version: 4\nprofiles:\n  claude-code: [{profile.as_posix()}]\n")
    write(profile / "plugins/installed_plugins.json", json.dumps({"plugins": {
        "dotbrain@dotbrain": [{"installPath": str(profile / "plugin"), "version": "0.0.0"}]}}))
    findings = doctor._check_machine(root, home)
    assert any(f.status == "warn" and "0.0.0" in f.message for f in findings)


def test_convention_drift_and_absent_input(tmp_path, monkeypatch):
    assert "skipped" in doctor._check_convention(tmp_path)[0].message
    write(tmp_path / ".brain/DOTBRAIN.md", "old convention\n")
    before = snapshot(tmp_path)
    finding = doctor._check_convention(tmp_path)[0]
    assert finding.status == "warn" and finding.suggestion == "run dotbrain refresh"
    assert doctor.as_result(doctor.DoctorReport(machine=[finding])).status == "success"
    assert snapshot(tmp_path) == before
    def unavailable(_):
        raise FileNotFoundError("packaged convention missing")
    monkeypatch.setattr(doctor.resource_loader, "resource", unavailable)
    assert "skipped" in doctor._check_convention(tmp_path)[0].message


def test_design_lifecycle_matches_spec_link_only_and_reads_only(tmp_path):
    write(tmp_path / ".brain/designs/example.md", "---\nlifecycle: active\n---\n# Example\n")
    write(tmp_path / ".brain/designs/finished.md", "---\nlifecycle: shipped\n---\n")
    write(tmp_path / ".brain/designs/open.md", "---\nlifecycle: active\n---\n")
    write(tmp_path / ".beads/metadata.json", "{}")
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        assert argv == ["bd", "--readonly", "list", "--all", "--type", "epic", "--limit", "0", "--json"]
        assert kwargs["cwd"] == tmp_path and kwargs["timeout"] == doctor.PROBE_TIMEOUT
        assert kwargs["env"]["BEADS_DIR"] == str(tmp_path / ".beads")
        return subprocess.CompletedProcess(argv, 0, json.dumps([
            {"status": "closed", "spec_id": "design:example"},
            {"status": "closed", "spec_id": "design:open"},
            {"status": "closed", "spec_id": "design:finished"},
            {"status": "open", "spec_id": "design:open"},
            {"status": "closed", "title": "open", "spec_id": "design:unrelated"},
        ]), "")
    before = snapshot(tmp_path)
    findings = doctor._check_design_lifecycle(tmp_path, "embedded", run)
    assert len(calls) == 1 and len(findings) == 1
    assert findings[0].status == "warn" and "example.md" in findings[0].message
    assert "close-design" in findings[0].suggestion and "correct" in findings[0].suggestion
    assert doctor.as_result(doctor.DoctorReport(machine=findings)).status == "success"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("problem", ["disabled", "uninitialized", "missing", "timeout", "nonzero", "malformed", "shape"])
def test_design_lifecycle_tracker_skips(tmp_path, problem):
    write(tmp_path / ".brain/designs/example.md", "---\nlifecycle: active\n---\n")
    if problem != "uninitialized":
        write(tmp_path / ".beads/metadata.json", "{}")
    def run(argv, **kwargs):
        assert "--readonly" in argv
        assert problem not in ("disabled", "uninitialized")
        if problem == "missing":
            raise FileNotFoundError("bd absent")
        if problem == "timeout":
            raise subprocess.TimeoutExpired(argv, doctor.PROBE_TIMEOUT)
        return subprocess.CompletedProcess(argv, 1 if problem == "nonzero" else 0,
                                           "{}" if problem == "shape" else "{broken", "unavailable")
    findings = doctor._check_design_lifecycle(tmp_path, "none" if problem == "disabled" else "embedded", run)
    assert len(findings) == 1 and findings[0].status == "info"
    assert "skipped" in findings[0].message and "tracker" in findings[0].message


def test_design_lifecycle_absent_or_no_active_designs_needs_no_tracker(tmp_path):
    def run(*args, **kwargs):
        pytest.fail("no tracker input needed")
    assert "skipped" in doctor._check_design_lifecycle(tmp_path, "none", run)[0].message
    write(tmp_path / ".brain/designs/example.md", "---\nlifecycle: shipped\n---\n")
    assert "no active designs" in doctor._check_design_lifecycle(tmp_path, "none", run)[0].message


def test_isolated_upgrade_and_refresh_clear_version_and_convention_drift(tmp_path, monkeypatch):
    root, home = tmp_path / "root", tmp_path / "user"
    brainspace = make_project(root)
    (root / ".git").mkdir()
    write(root / "config.yaml", "sync:\n  enabled: false\n")
    write(brainspace / ".brain/DOTBRAIN.md", "stale convention\n")
    plugin_registry(home, __version__)
    monkeypatch.setattr(doctor, "__version__", "0.0.0")
    run = recording_run(tmp_path, [])
    before = snapshot(tmp_path)
    report = doctor.run_doctor(root, home=home, project="example", run=run)
    assert snapshot(tmp_path) == before
    assert any(f.status == "warn" and "CLI 0.0.0" in f.message for f in report.machine)
    assert any(f.status == "warn" and "DOTBRAIN.md" in f.message for f in report.projects["example"])
    assert doctor.as_result(report).status == "success"
    # Upgrading the CLI to the plugin's version and refreshing are separate operations.
    monkeypatch.setattr(doctor, "__version__", __version__)
    refreshed = workflows.refresh_projects(root, project="example", run=run)
    assert not refreshed.errors
    assert "DOTBRAIN.md" in refreshed.targets[0].data["shared_brain_changes"]
    report = doctor.run_doctor(root, home=home, project="example", run=run)
    assert not any(f.status == "warn" and ("CLI" in f.message or "DOTBRAIN.md" in f.message)
                   for f in report.machine + report.projects["example"])


def test_empty_all_checks_machine_once_and_unknown_session_information(tmp_path, monkeypatch):
    calls = []
    original = doctor._check_machine
    monkeypatch.setattr(doctor, "_check_machine", lambda root, home: calls.append(root) or original(root, home))
    report = doctor.run_doctor(tmp_path, home=tmp_path / "user", all_projects=True)
    assert calls == [tmp_path] and report.projects == {}
    assert any("no registered projects" in f.message for f in report.machine)
    assert any(f.status == "info" and "session consumption is unknown" in f.suggestion for f in report.machine)
    assert not errors(report.machine)
    assert doctor.as_result(report).status == "success"


def test_disabled_components_do_not_require_bd_node_dolt(tmp_path, monkeypatch):
    root = tmp_path / "home"
    make_project(root)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: "git" if name == "git" else None)
    calls = []
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(tmp_path, calls))
    assert calls == [] and not errors(report.machine) and not errors(report.projects["example"])
    assert any(f.message == paths.NO_CHECKOUT for f in report.projects["example"])


@pytest.mark.parametrize("runtime", ["hermes", "pi", "opencode", "cursor"])
def test_all_checks_runtime_project_delivery_only_for_present_checkouts(tmp_path, runtime):
    root = tmp_path / "home"
    repo = tmp_path / "repo"
    write(root / "skills/example/SKILL.md", "# example")
    make_project(root, "wired", repo=repo, runtimes=(runtime,), selected=("example",))
    absent = make_project(root, "absent", runtimes=(runtime,))
    write(absent / ".repo", str(tmp_path / "elsewhere"))
    unregistered = make_project(root, "unregistered", runtimes=(runtime,))
    (unregistered / ".repo").unlink()
    # Incomplete owned delivery still needs diagnosis for present checkouts.
    rt = runtimes.find(runtime)
    directory = runtimes.user_dir(rt, tmp_path / "user")
    bundle = (opencode.packaged_dir(directory) if runtime == "opencode" else
              assets.HOME_DELIVERY[runtime].plugin_dir(root if runtime == "cursor" else directory))
    write(bundle / owned_copy.MARKER)
    if runtime == "opencode":
        write(opencode.plugin_file(directory), "foreign plugin")
    if runtime == "cursor":
        write(bundle / cursor.GLOBAL)

    report = doctor.run_doctor(root, home=tmp_path / "user", all_projects=True,
                               run=recording_run(repo, []))

    assert any(f.message.startswith(f"{runtime}:") and f.status == "warn"
               for f in report.projects["wired"])
    for name in ("absent", "unregistered"):
        assert not any(f.message.startswith(f"{runtime}:") for f in report.projects[name])
    assert any(f.status == "skip" for f in report.projects["absent"])
    assert any(f.message == paths.NO_CHECKOUT for f in report.projects["unregistered"])


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
    assert len(calls) == 3  # bd version, dolt test, ready
    assert all("--readonly" in argv for argv, _ in calls)
    assert all(kwargs["env"]["BEADS_DIR"] == str(root / "brainspaces/failed/.beads") for _, kwargs in calls)
    assert doctor.as_result(report).status == "partial"
    assert snapshot(tmp_path) == before


def test_selected_skill_and_codex_copy_health_no_cache_writes(tmp_path):
    root = tmp_path / "home"
    repo = tmp_path / "repo"
    write(root / "skills/bundle/one/SKILL.md", "skill")
    brainspace = make_project(root, repo=repo, runtimes=("codex",), selected=("bundle",))
    selected_agents = ("custom",)
    write(root / "subagents/codex/custom.toml", 'name = "custom"\n')
    declaration = brainspace / ".brain/project.yaml"
    declaration.write_text(declaration.read_text() + "\nsubagents: [custom]\n")
    subagents.link_project_subagents(root, brainspace, (".codex",), selected_agents, workspace_dirs={".codex": repo / ".codex"})
    skills.link_project(root, brainspace, (".codex",), ["bundle"], workspace_dirs={".codex": repo / ".codex"})
    entries = ["/.brain", "/.agents/skills/one"] + [f"/.codex/agents/{name}.toml" for name in selected_agents]
    write(repo / ".git/info/exclude", "\n".join(entries) + "\n")
    # Real-file Codex delivery needs no cache at diagnosis time.
    import shutil
    shutil.rmtree(root / ".cache", ignore_errors=True)
    before = snapshot(tmp_path)
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(repo, []))
    assert not errors(report.projects["example"])
    assert snapshot(tmp_path) == before and not (root / ".cache").exists()
    dest = repo / f".codex/agents/{selected_agents[0]}.toml"
    dest.write_text(dest.read_text() + "# stale\n")
    skill = repo / ".agents/skills/one"
    skill.unlink()
    write(root / "skills/other/SKILL.md")
    skill.symlink_to(root / "skills/other", target_is_directory=True)
    report = doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(repo, []))
    assert len(errors(report.projects["example"])) == 2


def test_claude_expected_link_and_global_selections(tmp_path):
    root = tmp_path / "home"
    user = tmp_path / "user"
    write(root / "subagents/claude/custom.md", "custom")
    write(root / "config.yaml", "version: 4\nsubagents: [custom]\n")
    receiver = user / ".claude/agents"
    receiver.mkdir(parents=True)
    (receiver / "custom.md").symlink_to(root / "subagents/claude/custom.md")
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
    assert any(f.status == "info" and "not verified" in f.message for f in findings)
    assert not any(f.status == "warn" for f in findings)


@pytest.mark.parametrize("hooks", [None, {}])
def test_registered_plugin_missing_session_hook_remains_warning(tmp_path, hooks):
    install = tmp_path / "plugin"
    if hooks is not None:
        write(install / "hooks/hooks.json", json.dumps({"hooks": hooks}))
    write(tmp_path / ".codex/plugins/installed_plugins.json", json.dumps({"plugins": {
        "dotbrain@dotbrain": [{"installPath": str(install)}]}}))
    assert doctor._check_plugin(tmp_path, "codex")[0].status == "warn"


def test_malformed_plugin_registry_remains_warning(tmp_path):
    write(tmp_path / ".codex/plugins/installed_plugins.json", "{broken")
    assert doctor._check_plugin(tmp_path, "codex")[0].status == "warn"


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
    output = buffer.buffer.getvalue().decode("cp1252")
    assert "Doctor" in output and "1 warning" in output
    assert r"\u2603" in output and "[ok]" in output


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


@pytest.mark.parametrize("terminal,json_output,dumb,fail", [
    (True, False, False, False), (True, False, False, True),
    (True, True, False, False), (False, False, False, False),
    (True, False, True, False),
])
def test_doctor_spinner_only_in_interactive_text_and_clears_before_report(tmp_path, monkeypatch, terminal, json_output, dumb, fail):
    from dotbrain import presentation
    events = []
    @contextmanager
    def status(label, **kwargs):
        assert "all projects" in label
        events.append("start")
        try:
            yield
        finally:
            events.append("stop")
    original_console = presentation.console
    monkeypatch.setattr(presentation, "console", lambda: SimpleNamespace(
        is_terminal=terminal, is_dumb_terminal=dumb, status=status))
    def run(*args, **kwargs):
        events.append("check")
        # Final reports use the real console, after the status context exits.
        monkeypatch.setattr(presentation, "console", original_console)
        if fail:
            raise RuntimeError("probe failed")
        return doctor.DoctorReport(machine=[doctor.Finding("ok", "ready")])
    monkeypatch.setattr(doctor, "run_doctor", run)
    result = CliRunner().invoke(app, ["doctor", "--all", "--home", str(tmp_path), *(["--json"] if json_output else [])])
    assert result.exit_code == (1 if fail else 0), result.output
    assert events == (["start", "check", "stop"] if terminal and not json_output and not dumb else ["check"])
    assert "Checking machine" not in result.stdout
    if json_output:
        assert json.loads(result.stdout)["command"] == "doctor"


@pytest.mark.parametrize("stdout, status", [
    ("bd version 1.2.2 (6c124203e: HEAD@6c124203e771)\n", "warn"),
    ("bd version 1.3.1 (c1c4b642a: HEAD@c1c4b642ac1c)\n", "ok"),
    ("bd version 1.4.0 (abc)\n", "ok"),
    ("garbled\n", "info"),
])
def test_bd_version_reports_releases_older_than_the_qualified_one(tmp_path, stdout, status):
    # bd 1.3 guards ownership and migrates the schema; older releases miss the behavior the skills rely on.
    def run(argv, **kwargs):
        assert argv == ["bd", "--readonly", "version"]
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

    assert doctor._check_bd_version(tmp_path, run).status == status


def test_plugin_check_needs_hooks_without_packaged_claude_agents(tmp_path):
    install = tmp_path / "plugin-install"
    write(install / "hooks/hooks.json", json.dumps({"hooks": {"SessionStart": [{"hooks": [{"command": "dotbrain hook session-start"}]}]}}))
    write(tmp_path / ".claude/plugins/installed_plugins.json", json.dumps({"plugins": {"dotbrain@dotbrain": [{"installPath": str(install)}]}}))
    findings = doctor._check_plugin(tmp_path, "claude-code")
    assert not any(f.status == "warn" for f in findings)


def test_all_skips_shared_checkouts_absent_on_this_machine(tmp_path):
    root = tmp_path / "home"
    repo = tmp_path / "repo"
    make_project(root, "local", repo=repo)
    write(make_project(root, "shared") / ".repo", str(tmp_path / "elsewhere"))
    override = make_project(root, "override")
    write(override / ".repo", str(tmp_path / "elsewhere"))
    write(override / ".repo.local", str(tmp_path / "missing-local"))
    calls = []
    before = snapshot(tmp_path)
    report = doctor.run_doctor(root, home=tmp_path / "user", all_projects=True, run=recording_run(repo, calls))
    assert snapshot(tmp_path) == before
    assert not errors(report.projects["local"])
    assert not errors(report.projects["shared"])
    assert [f.status for f in report.projects["shared"]].count("skip") == 1
    assert not any(str(tmp_path / "elsewhere") in str(kwargs.get("cwd")) for _, kwargs in calls)
    assert any("registered checkout missing" in m for m in errors(report.projects["override"]))
    statuses = {t.project: t.status for t in doctor.as_result(report).targets}
    assert statuses == {None: statuses[None], "local": "success", "shared": "skipped", "override": "failure"}
    explicit = doctor.run_doctor(root, home=tmp_path / "user", project="shared", run=recording_run(repo, []))
    assert any("registered checkout missing" in m for m in errors(explicit.projects["shared"]))


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, encoding="utf-8").stdout.strip()


@pytest.fixture
def synced_home(tmp_path):
    """A dotbrain home under Git, pushed to a bare remote and clean."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    root = tmp_path / "home"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    for key, value in (("user.name", "Test"), ("user.email", "test@example.com"), ("core.autocrlf", "false")):
        git(root, "config", key, value)
    write(root / "brainspaces/alpha/.brain/CONTEXT.md", "base\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "initial")
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "-u", "origin", "main")
    return root


def sync_findings(root):
    # These real-Git tests check metadata; probe deadlines are exercised with a fake runner below.
    def run(argv, **kwargs):
        return doctor._default_run(argv, **{**kwargs, "timeout": None})

    return [(f.status, f.message) for f in doctor._check_home_sync(root, run)]


def test_home_sync_probe_timeout_is_reported(tmp_path):
    (tmp_path / ".git").mkdir()

    def run(argv, **kwargs):
        assert kwargs["timeout"] == doctor.PROBE_TIMEOUT
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    findings = doctor._check_home_sync(tmp_path, run)
    assert len(findings) == 1 and findings[0].status == "warn"
    assert findings[0].message.startswith("home sync check unavailable:")
    assert f"timed out after {doctor.PROBE_TIMEOUT} seconds" in findings[0].message


def test_clean_synced_home_reports_no_sync_problems(synced_home, tmp_path):
    before = snapshot(synced_home)
    assert sync_findings(synced_home) == [("ok", "home sync: nothing waiting for origin/main (as last fetched)")]
    assert snapshot(synced_home) == before
    report = doctor.run_doctor(synced_home, home=tmp_path / "user", all_projects=True)
    assert not [f for f in report.machine if f.message.startswith("home sync") and f.status in {"warn", "error"}]


def test_sync_disabled_and_home_outside_git_are_informational(synced_home, tmp_path):
    assert sync_findings(tmp_path / "plain") == [
        ("info", "home sync inactive: the dotbrain home is not a Git repository")]
    write(synced_home / "config.yaml", "sync:\n  enabled: false\n")
    assert sync_findings(synced_home) == [("info", "home sync disabled (sync.enabled: false)")]


def test_no_remote_is_informational(synced_home):
    git(synced_home, "remote", "remove", "origin")
    assert sync_findings(synced_home) == [("info", "home sync: no remote configured; sync commits stay local")]


def test_waiting_commits_are_counted_against_last_known_upstream(synced_home):
    for n in (1, 2):
        write(synced_home / f"brainspaces/alpha/.brain/{n}.md")
        git(synced_home, "add", "-A")
        git(synced_home, "commit", "-q", "-m", f"alpha: {n}")
    git(synced_home, "remote", "set-url", "origin", str(synced_home.parent / "unreachable.git"))  # proves no fetch
    assert sync_findings(synced_home) == [("info", "home sync: 2 local commits waiting to be pushed to origin/main")]


def test_conflict_copies_and_size_limit_skips_are_reported_by_path(synced_home):
    write(synced_home / "config.yaml", "sync:\n  max-file-size: 100\n")
    copy = "brainspaces/alpha/.brain/CONTEXT.sync-conflict-2026-10-20-host.md"
    write(synced_home / copy, "theirs\n")
    git(synced_home, "add", "-A")
    git(synced_home, "commit", "-q", "-m", "sync: merge")
    git(synced_home, "push", "-q")
    write(synced_home / "brainspaces/alpha/.brain/big bin.dat", "x" * 200)
    write(synced_home / "brainspaces/alpha/.brain/CONTEXT.md", "y" * 200)  # tracked, now over the limit
    write(synced_home / "brainspaces/alpha/.brain/small.md")
    found = sync_findings(synced_home)
    assert ("warn", f"home sync: open conflict copy {copy}") in found
    assert [m for s, m in found if s == "warn" and "size limit" in m] == [
        f"home sync: brainspaces/alpha/.brain/{name} is over the size limit and stays uncommitted"
        for name in ("CONTEXT.md", "big bin.dat")]
    assert not [s for s, _ in found if s == "error"]


@pytest.mark.parametrize("state, marker", [("merge", "MERGE_HEAD"), ("rebase", "rebase-merge")])
def test_merge_or_replay_in_progress_fails(synced_home, tmp_path, state, marker):
    git(synced_home, "switch", "-q", "-c", "other")
    write(synced_home / "brainspaces/alpha/.brain/CONTEXT.md", "other\n")
    git(synced_home, "commit", "-q", "-am", "other")
    git(synced_home, "switch", "-q", "main")
    write(synced_home / "brainspaces/alpha/.brain/CONTEXT.md", "main\n")
    git(synced_home, "commit", "-q", "-am", "main")
    assert subprocess.run(["git", state, "other"], cwd=synced_home, capture_output=True).returncode
    found = sync_findings(synced_home)
    assert ("error", f"home sync blocked: {marker} in the dotbrain home") in found
    report = doctor.run_doctor(synced_home, home=tmp_path / "user", all_projects=True)
    assert doctor.as_result(report).status == "failure"
    result = CliRunner().invoke(app, ["doctor", "--home", str(synced_home), "--all", "--json"])
    assert result.exit_code == 1
    machine = next(t for t in json.loads(result.stdout)["targets"] if t["scope"] == "machine")
    assert any(f["severity"] == "error" and f["message"].startswith("home sync blocked") for f in machine["findings"])


def packaged_messages(report):
    return [f.message for f in report.projects["example"]
            if "packaged" in f.message or "dotbrain-" in f.message or "unversioned" in f.message]


def test_packaged_subagent_findings(tmp_path):
    from dotbrain import config
    root, repo = tmp_path / "home", tmp_path / "repo"
    brainspace = make_project(root, repo=repo, runtimes=("codex",))
    declaration = brainspace / ".brain/project.yaml"
    base = declaration.read_text()
    first, second = config.PACKAGED_ROLES[:2]
    agents_dir = repo / ".codex/agents"
    subagents.reconcile_packaged(agents_dir, [first], "codex", label="agents")

    def run():
        return doctor.run_doctor(root, home=tmp_path / "user", project="example", run=recording_run(repo, []))

    declaration.write_text(base + f"version: 2\npackaged-subagents: [{first}]\n")
    assert packaged_messages(run()) == []

    declaration.write_text(base)
    assert any("unversioned" in m for m in packaged_messages(run()))

    declaration.write_text(base + f"version: 2\npackaged-subagents: [{second}]\nsubagents: [dotbrain-mine]\n")
    write(agents_dir / "dotbrain-foreign.toml", 'name = "x"\n')
    messages = packaged_messages(run())
    assert any(f"'{second}' is not delivered" in m for m in messages)
    assert any(f"dotbrain-{first}.toml: delivered packaged subagent is not listed" in m for m in messages)
    assert any("dotbrain-foreign.toml: dotbrain-* file is not managed" in m for m in messages)
    assert any("'dotbrain-mine' uses the reserved" in m for m in messages)

    declaration.write_text(base + "version: 2\npackaged-subagents: []\n")
    (agents_dir / f"dotbrain-{first}.toml").unlink()
    (agents_dir / "dotbrain-foreign.toml").unlink()
    messages = packaged_messages(run())
    assert len(messages) == 1 and "per-role effort" in messages[0]
