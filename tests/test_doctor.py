"""Tests for the dotbrain doctor read-only health check."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from dotbrain import config, doctor, paths
from dotbrain.cli import app

from conftest import set_fake_home

runner = CliRunner()


# --------------------------------------------------------------------------- machine checks


def test_check_binary_found():
    f = doctor._check_binary("python3")
    assert f.status == "ok"


def test_check_binary_missing():
    f = doctor._check_binary("zzz-nonexistent-xyzzy")
    assert f.status == "error"
    assert f.suggestion


def test_check_binary_dolt_warns_not_errors():
    """dolt is a server-host dep — missing is a warning, not a hard error."""
    f = doctor._check_binary_dolt()
    if f.status != "ok":
        assert f.status == "warn", f"dolt missing should be warn, got {f.status}: {f.message}"


def test_check_dotbrain_config_valid(dotbrain_home: Path):
    f = doctor._check_dotbrain_config(dotbrain_home)
    assert f.status == "ok"


def test_check_dotbrain_config_broken(dotbrain_home: Path):
    (dotbrain_home / "dotbrain.yaml").write_text(": !!bad yaml [[")
    f = doctor._check_dotbrain_config(dotbrain_home)
    assert f.status == "error"


def test_check_global_skills_config_present(dotbrain_home: Path):
    (dotbrain_home / "skills" / "skills.yaml").write_text("")
    f = doctor._check_global_skills_config(dotbrain_home)
    assert f.status == "ok"


def test_check_global_skills_config_missing(tmp_path: Path):
    f = doctor._check_global_skills_config(tmp_path)
    assert f.status == "ok"


def test_check_templates_present(dotbrain_home: Path):
    f = doctor._check_templates(dotbrain_home)
    assert f.status == "ok"


def test_check_templates_ignores_data_root_templates(tmp_path: Path):
    f = doctor._check_templates(tmp_path)
    assert f.status == "ok"


def test_check_global_hook_installed(dotbrain_home: Path, fake_home: Path):
    from dotbrain.brainspaces import ensure_json_hook
    from dotbrain.bootstrap import _global_hook_command

    target = fake_home / ".claude" / "settings.json"
    cmd = _global_hook_command("claude-worktree-bootstrap.sh", dotbrain_home, fake_home)
    ensure_json_hook(target, "SessionStart", cmd)

    f = doctor._check_global_hook(fake_home, ".claude/settings.json",
                                  "claude-worktree-bootstrap.sh", dotbrain_home, "Claude")
    assert f.status == "ok"


def test_check_global_hook_missing(dotbrain_home: Path, fake_home: Path):
    f = doctor._check_global_hook(fake_home, ".claude/settings.json",
                                  "claude-worktree-bootstrap.sh", dotbrain_home, "Claude")
    assert f.status == "warn"
    assert "not found" in f.message.lower()


# --------------------------------------------------------------------------- project wiring


def test_check_repo_file_brain_only(brainspace: Path):
    (brainspace / ".repo").write_text("(brain-only)\n")
    f, resolved = doctor._check_repo_file(brainspace)
    assert f is not None
    assert f.status == "ok"
    assert "brain-only" in f.message
    assert resolved is None


def test_check_repo_file_missing(brainspace: Path):
    f, resolved = doctor._check_repo_file(brainspace)
    assert f is not None
    assert f.status == "error"
    assert ".repo" in f.message
    assert resolved is None


def test_check_repo_file_bad_target(brainspace: Path):
    (brainspace / ".repo").write_text("/nonexistent/path/x\n")
    f, resolved = doctor._check_repo_file(brainspace)
    assert f is not None
    assert f.status == "error"
    assert resolved is None


def test_check_repo_file_valid_repo(dotbrain_home: Path, tmp_path: Path):
    brainspace = dotbrain_home / "brainspaces" / "demo"
    brainspace.mkdir(parents=True)
    repo = tmp_path / "demo"
    repo.mkdir()
    (brainspace / ".repo").write_text(f"{repo}\n")
    f, resolved = doctor._check_repo_file(brainspace)
    assert f is None
    assert resolved == repo


def test_check_brainspace_links_all_ok(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "myrepo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    brainspace = dotbrain_home / "brainspaces" / "myrepo"
    for link in paths.BRAINSPACE_LINKS:
        (brainspace / link).mkdir(parents=True, exist_ok=True)
        (repo / link).symlink_to(brainspace / link)
    findings = doctor._check_brainspace_links(repo, brainspace)
    assert len(findings) == 0


def test_check_brainspace_links_missing(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "bare"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    brainspace = dotbrain_home / "brainspaces" / "bare"
    for link in paths.BRAINSPACE_LINKS:
        (brainspace / link).mkdir(parents=True, exist_ok=True)
    findings = doctor._check_brainspace_links(repo, brainspace)
    assert len(findings) == len(paths.BRAINSPACE_LINKS)
    assert all(f.status == "warn" for f in findings)


def test_check_brainspace_links_broken(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "brokenlinks"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    brainspace = dotbrain_home / "brainspaces" / "brokenlinks"
    brainspace.mkdir(parents=True, exist_ok=True)
    for link in paths.BRAINSPACE_LINKS:
        (brainspace / link).mkdir(parents=True, exist_ok=True)
        (repo / link).symlink_to(brainspace / link)
    # Break one
    (brainspace / ".brain").rmdir()
    findings = doctor._check_brainspace_links(repo, brainspace)
    broken = [f for f in findings if f.status == "error"]
    assert len(broken) == 1
    assert "broken" in broken[0].message.lower()


def test_check_repo_excludes_ok(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "with_excludes"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    exclude = repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("\n".join(paths.EXCLUDE_ENTRIES) + "\n")
    findings = doctor._check_repo_excludes(repo)
    assert len(findings) == 0


def test_check_repo_excludes_missing(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "no_excludes"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    findings = doctor._check_repo_excludes(repo)
    assert len(findings) == len(paths.EXCLUDE_ENTRIES)


def test_check_agent_pointer_uses_wire_marker(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Doctor uses wire's own idempotency marker: the '.brain/AGENTS.md' substring."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "with_pointer"
    repo.mkdir()
    # Wire's marker is the substring — the full ADOPTER_POINTER contains it.
    (repo / "AGENTS.md").write_text(f"# Context\n\n{paths.ADOPTER_POINTER}\n")
    findings = doctor._check_agent_pointer(repo)
    assert len(findings) == 0


def test_check_agent_pointer_matches_wire_substring(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A file with just '.brain/AGENTS.md' (wire's marker) passes — no false positive."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "dotbrain_style"
    repo.mkdir()
    # Simulates dotbrain's own AGENTS.md — has .brain/AGENTS.md but not the full pointer.
    (repo / "AGENTS.md").write_text("# Agent Context\n\nDotbrain: read `.brain/AGENTS.md` first.\n")
    findings = doctor._check_agent_pointer(repo)
    assert len(findings) == 0, f"wire's marker should suffice, got: {findings}"


def test_check_agent_pointer_missing(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = tmp_path / "no_pointer"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# Context\n\nNo pointer here.\n")
    findings = doctor._check_agent_pointer(repo)
    assert len(findings) == 1
    assert findings[0].status == "warn"


def test_dotbrain_repo_skipped_in_wiring(dotbrain_home: Path):
    """The dotbrain repo itself is not an adopter — wiring checks skip it."""
    brainspace = dotbrain_home / "brainspaces" / "dotbrain"
    brainspace.mkdir(parents=True, exist_ok=True)
    (brainspace / ".repo").write_text(f"{dotbrain_home}\n")
    findings = doctor._check_project_wiring(brainspace, dotbrain_home)
    assert len(findings) == 1
    assert findings[0].status == "ok"
    assert "not an adopter" in findings[0].message


# --------------------------------------------------------------------------- beads state


def test_check_beads_state_none_mode(dotbrain_home: Path):
    config.write_project_config(dotbrain_home, "demo", config.ProjectBeads(mode="none"))
    findings = doctor._check_beads_state(dotbrain_home / "brainspaces" / "demo", "demo", dotbrain_home)
    assert len(findings) == 1
    assert findings[0].status == "ok"
    assert "disabled" in findings[0].message


def test_check_beads_state_missing_dir(dotbrain_home: Path):
    findings = doctor._check_beads_state(dotbrain_home / "brainspaces" / "demo", "demo", dotbrain_home)
    assert any(f.status == "warn" and "not initialized" in f.message for f in findings)


# --------------------------------------------------------------------------- Runner seam


def _recording_run(calls: list[dict[str, Any]]):
    """Factory: returns a Runner that records every call into `calls` and returns success."""

    def _run(argv, *, cwd=None, check=True, timeout=None):
        calls.append({"argv": list(argv), "cwd": str(cwd) if cwd else None})
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    return _run


def _recording_run_fails(exit_code: int, stderr: str):
    """Factory: returns a Runner that fails 'bd dolt test' and succeeds for other calls."""

    def _run(argv, *, cwd=None, check=True, timeout=None):
        if "dolt" in argv and "test" in argv:
            raise subprocess.CalledProcessError(exit_code, argv, stderr=stderr)
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    return _run


def test_beads_server_connectivity_calls_bd_dolt_test(dotbrain_home: Path):
    """With a metadata.json present, server-mode projects run 'bd dolt test'."""
    brainspace = dotbrain_home / "brainspaces" / "demo"
    brainspace.mkdir(parents=True, exist_ok=True)
    beads = brainspace / ".beads"
    beads.mkdir()
    (beads / "metadata.json").write_text(json.dumps({"dolt_mode": "server"}))
    (brainspace / ".brain").mkdir(exist_ok=True)
    (brainspace / ".brain" / "project.yaml").write_text("beads:\n  mode: server\n")

    calls: list[dict[str, Any]] = []
    findings = doctor._check_beads_state(brainspace, "demo", dotbrain_home, run=_recording_run(calls))

    dolt_test = [c for c in calls if "dolt" in c["argv"] and "test" in c["argv"]]
    assert len(dolt_test) == 1, f"expected bd dolt test call, got: {calls}"
    assert dolt_test[0]["cwd"] == str(brainspace)


def test_beads_no_mutating_commands(dotbrain_home: Path):
    """Doctor must never issue mutating commands — no bd init, bd dolt set, git, rm, mkdir."""
    brainspace = dotbrain_home / "brainspaces" / "demo"
    brainspace.mkdir(parents=True, exist_ok=True)
    beads = brainspace / ".beads"
    beads.mkdir()
    (beads / "metadata.json").write_text(json.dumps({"dolt_mode": "server"}))

    calls: list[dict[str, Any]] = []
    doctor._check_beads_state(brainspace, "demo", dotbrain_home, run=_recording_run(calls))

    all_argv = [" ".join(c["argv"]) for c in calls]
    mutators = ["bd init", "bd dolt set", "git ", "rm ", "mkdir", "bd close",
                "bd update", "bd create"]
    for argv_line in all_argv:
        for m in mutators:
            assert m not in argv_line, f"mutating command found: {argv_line}"


def test_beads_connectivity_failure_reports_error(dotbrain_home: Path):
    """When bd dolt test fails, doctor reports it as an error."""
    brainspace = dotbrain_home / "brainspaces" / "demo"
    brainspace.mkdir(parents=True, exist_ok=True)
    beads = brainspace / ".beads"
    beads.mkdir()
    (beads / "metadata.json").write_text(json.dumps({"dolt_mode": "server"}))
    (brainspace / ".brain").mkdir(exist_ok=True)
    (brainspace / ".brain" / "project.yaml").write_text("beads:\n  mode: server\n")

    findings = doctor._check_beads_state(
        brainspace, "demo", dotbrain_home,
        run=_recording_run_fails(1, "connection refused"),
    )
    errors = [f for f in findings if f.status == "error"]
    assert len(errors) >= 1
    assert any("unreachable" in e.message.lower() for e in errors)


# --------------------------------------------------------------------------- orchestration


def test_run_doctor_no_projects(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    import shutil
    projects = dotbrain_home / "brainspaces"
    for d in list(projects.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            shutil.rmtree(d)
    report = doctor.run_doctor(dotbrain_home)
    has_warn = any(f.status == "warn" and "no Brainspaces" in f.message
                   for f in report.machine)
    assert has_warn


def test_run_doctor_with_wired_project(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    set_fake_home(monkeypatch, fake_home)

    repo = tmp_path / "proj"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    brainspace = dotbrain_home / "brainspaces" / "proj"
    brainspace.mkdir(parents=True, exist_ok=True)
    (brainspace / ".repo").write_text(f"{repo}\n")
    for link in paths.BRAINSPACE_LINKS:
        (brainspace / link).mkdir(parents=True, exist_ok=True)
        (repo / link).symlink_to(brainspace / link)

    exclude = repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("\n".join(paths.EXCLUDE_ENTRIES) + "\n")

    (repo / "AGENTS.md").write_text(f"# Context\n\n{paths.ADOPTER_POINTER}\n")

    report = doctor.run_doctor(dotbrain_home, home=fake_home)
    assert "proj" in report.projects

    proj_findings = report.projects["proj"]
    statuses = {f.status for f in proj_findings}
    assert "error" not in statuses


def test_run_doctor_machine_always_runs(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    report = doctor.run_doctor(dotbrain_home)
    assert len(report.machine) >= 5  # bd, dolt, config, skills, templates, 2 hooks


# --------------------------------------------------------------------------- CLI integration


def test_doctor_cli_help():
    result = runner.invoke(app, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output.lower()
    assert "read-only" in result.output.lower()


def test_doctor_cli_runs(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    result = runner.invoke(app, ["doctor"])
    # No errors expected on a fixture checkout (dolt is warn, hooks are warn)
    assert result.exit_code == 0, result.output
    assert "Machine readiness" in result.output
    assert "ok" in result.output or "warn" in result.output or "error" in result.output


def test_doctor_cli_exits_nonzero_on_errors(dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    """When doctor finds errors (not just warnings), exit code is 1."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    (dotbrain_home / "dotbrain.yaml").write_text("not: [valid")
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1, result.output
    assert "Next: fix errors" in result.output


def test_doctor_cli_in_help_tree():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output
