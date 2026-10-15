"""Tests for workflows.py — wire/unwire orchestration and scenario 9 adopter edge cases."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dotbrain import beads, bootstrap as bootstrap_mod, config, paths, skills, subagents, workflows


@pytest.mark.parametrize("conflict", ["other-project", "foreign-root", "invalid-name", "symlink-escape"])
def test_wire_rejection_precedes_all_housekeeping(tmp_path: Path, conflict: str):
    home = tmp_path / "home"
    (home / ".git").mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    original = home / "brainspaces" / "original"
    (original / ".brain").mkdir(parents=True)
    (original / ".repo").write_text("registered-checkout", encoding="utf-8")
    (original / ".brain" / "project.yaml").write_text("agents: []\nbeads:\n  mode: none\n", encoding="utf-8")
    target = original / ".brain"
    if conflict == "foreign-root":
        target = tmp_path / "foreign" / "brainspaces" / "original" / ".brain"
        target.mkdir(parents=True)
    (repo / ".brain").symlink_to(target, target_is_directory=True)
    project = "other" if conflict == "other-project" else "../escape" if conflict == "invalid-name" else "original"
    if conflict == "symlink-escape":
        external = tmp_path / "external"
        external.mkdir()
        (original / ".brain" / "project.yaml").unlink()
        (original / ".brain").rmdir()
        (original / ".brain").symlink_to(external, target_is_directory=True)

    before = sorted(p.relative_to(home).as_posix() for p in home.rglob("*"))
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        assert argv == ["git", "rev-parse", "--show-toplevel"]
        return subprocess.CompletedProcess(argv, 0, stdout=str(repo))
    with pytest.raises((ValueError, RuntimeError)):
        workflows.wire_project(dotbrain_home=home, repo=repo, project=project, run_beads=False, run=run)

    assert sorted(p.relative_to(home).as_posix() for p in home.rglob("*")) == before
    assert not (home / ".gitignore").exists()
    assert (original / ".repo").read_text(encoding="utf-8") == "registered-checkout"
    assert (repo / ".brain").is_symlink()
    assert calls == [["git", "rev-parse", "--show-toplevel"]]


def _make_wired_repo(tmp_path: Path, dotbrain_home: Path, name: str) -> Path:
    """Return a fully wired adopter repo with symlinks, exclude entries, and pointer."""
    repo = tmp_path / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "AGENTS.md").write_text(f"# {name}\n")

    brainspace = paths.brainspace(dotbrain_home, name)
    for link in paths.BRAINSPACE_LINKS:
        (brainspace / link).mkdir(parents=True)
        (repo / link).symlink_to(brainspace / link)

    exclude = repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(exist_ok=True)
    exclude.write_text("\n".join(paths.EXCLUDE_ENTRIES) + "\n")

    agents = repo / "AGENTS.md"
    agents.write_text(f"# {name}\n\n{paths.ADOPTER_POINTER}\n")
    return repo


def _git_runner(dotbrain_home: Path):
    """Runner that executes git commands for real (needed for archive/delete staging)."""
    def run(argv, *, cwd=None, check=True):
        return subprocess.run(list(argv), cwd=cwd, check=check, capture_output=True, text=True)
    return run


# --------------------------------------------------------------------------- keep (default)


def test_unwire_keep_removes_symlinks_and_cleans_repo(tmp_path: Path, dotbrain_home: Path):
    repo = _make_wired_repo(tmp_path, dotbrain_home, "proj-keep")

    result = workflows.unwire_repo(repo)

    for name in paths.BRAINSPACE_LINKS:
        assert not (repo / name).exists()
    assert paths.ADOPTER_POINTER not in (repo / "AGENTS.md").read_text()
    exclude_lines = (repo / ".git" / "info" / "exclude").read_text().splitlines()
    for entry in paths.EXCLUDE_ENTRIES:
        assert entry not in exclude_lines
    assert not result.warnings


# --------------------------------------------------------------------------- archive


# --------------------------------------------------------------------------- delete


# --------------------------------------------------------------------------- full round-trip


def test_wire_then_unwire_round_trip(tmp_path: Path, dotbrain_home: Path):
    """Wire a repo then unwire it; final state matches the disconnected_adopter_repo shape."""
    repo = tmp_path / "roundtrip"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "AGENTS.md").write_text("# Round Trip\n")

    def real_git_runner(argv, *, cwd=None, env=None, check=True):
        if argv[0] in ("git", "bd"):
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        home=Path.home(),
        run=real_git_runner,
    )
    assert (repo / ".brain").is_symlink()
    if paths.INJECT_ADOPTER_POINTER:
        assert paths.ADOPTER_POINTER in (repo / "AGENTS.md").read_text()

    workflows.unwire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run=real_git_runner,
    )

    for name in (".brain", ".beads"):
        assert not (repo / name).exists()
    assert (repo / ".claude").is_dir()
    assert (repo / ".codex").is_dir()
    assert paths.ADOPTER_POINTER not in (repo / "AGENTS.md").read_text()
    exclude_lines = (repo / ".git" / "info" / "exclude").read_text().splitlines()
    for entry in paths.EXCLUDE_ENTRIES:
        assert entry not in exclude_lines
    # Brainspace kept
    assert paths.brainspace(dotbrain_home, "roundtrip").is_dir()


def test_unwire_removes_managed_workspace_links_and_preserves_project_files(
    tmp_path: Path, dotbrain_home: Path
):
    repo = tmp_path / "workspace-unwire"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    brainspace = paths.brainspace(dotbrain_home, "workspace-unwire")
    for name in paths.BRAINSPACE_LINKS:
        (brainspace / name).mkdir(parents=True)
        (repo / name).symlink_to(brainspace / name)
    project_file = repo / ".claude" / "project.json"
    project_file.parent.mkdir()
    project_file.write_text("project-owned\n")
    managed_skill = repo / ".claude" / "skills" / "managed"
    managed_skill.parent.mkdir()
    managed_target = dotbrain_home / "skills" / "managed"
    managed_target.mkdir(parents=True)
    managed_skill.symlink_to(managed_target)
    managed_agent = repo / ".codex" / "agents" / "managed.toml"
    managed_agent.parent.mkdir(parents=True)
    managed_agent.symlink_to(dotbrain_home / "agents" / "codex" / "managed.toml")
    exclude = repo / ".git" / "info" / "exclude"
    exclude.write_text(
        "\n".join((*paths.EXCLUDE_ENTRIES, "/.claude/skills/managed", "/.codex/agents/managed.toml")) + "\n"
    )
    subprocess.run(["git", "add", ".claude/project.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "project workspace"], cwd=repo, check=True)

    result = workflows.unwire_repo(repo, dotbrain_home=dotbrain_home)

    assert project_file.read_text() == "project-owned\n"
    assert not managed_skill.exists()
    assert (repo / ".codex").is_dir()
    assert subprocess.run(
        ["git", "diff", "--exit-code", "--", ".claude/project.json"], cwd=repo, check=False
    ).returncode == 0
    excludes = exclude.read_text().splitlines()
    assert "/.claude/skills/managed" not in excludes
    assert "/.codex/agents/managed.toml" not in excludes
    assert not any("removed empty workspace" in log for log in result.logs)


# --------------------------------------------------------------------------- missing Brainspace


def test_drop_remote_beads_database_via_ssh_runs_mysql():
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    log = beads.drop_remote_beads_database(
        "brain-only",
        ssh_host="ssh-hop",
        server_host="10.0.0.1",
        server_port="3307",
        server_user="beads",
        run=fake_run,
    )

    assert log == "dropped remote beads database: brain-only"
    assert calls == [[
        "ssh",
        "ssh-hop",
        "mysql --host 10.0.0.1 --port 3307 -u beads -e 'DROP DATABASE IF EXISTS `brain-only`;'",
    ]]


def test_drop_remote_beads_database_without_ssh_runs_mysql_directly():
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    log = beads.drop_remote_beads_database(
        "brain-only", server_host="db.local", server_port="3399", server_user="robot", run=fake_run
    )

    assert log == "dropped remote beads database: brain-only"
    assert calls == [[
        "mysql", "--host", "db.local", "--port", "3399",
        "-u", "robot", "-e", "DROP DATABASE IF EXISTS `brain-only`;",
    ]]


def test_drop_remote_beads_database_rejects_unsafe_names():
    with pytest.raises(ValueError, match="unsafe"):
        beads.drop_remote_beads_database("bad;name", server_host="db.local")

    with pytest.raises(ValueError, match="protected"):
        beads.drop_remote_beads_database("dotbrain", server_host="db.local")


def test_unwire_keep_preserves_projects_entry(dotbrain_home: Path):
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\nprojects:\n  fresh:\n    beads:\n      mode: embedded\n"
    )
    brainspace = paths.brainspace(dotbrain_home, "fresh")
    (brainspace / ".brain").mkdir(parents=True)

    with pytest.raises(ValueError, match="no available checkout"):
        workflows.unwire_project(dotbrain_home=dotbrain_home, project="fresh", run=_git_runner(dotbrain_home))

    assert config.load_project_config(dotbrain_home, "fresh").mode == "embedded"


def test_refresh_project_repairs_repo_links_links_skills_and_loads_beads(
    tmp_path: Path, dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _make_wired_repo(tmp_path, dotbrain_home, "refreshme")
    brainspace = paths.brainspace(dotbrain_home, "refreshme")
    (brainspace / ".repo").write_text(f"{repo}\n")
    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n  - codex\n")
    legacy_skill = repo / ".claude" / "skills" / "operate-execution"
    legacy_skill.parent.mkdir(parents=True)
    legacy_skill.symlink_to(dotbrain_home / "skills" / "brain" / "operate-execution")
    loaded: dict[str, object] = {}

    def fake_pull_beads_for_all(dotbrain_home_arg, *, run, projects):
        loaded["root"] = dotbrain_home_arg
        loaded["projects"] = list(projects)
        return beads.BootstrapResult(logs=["beads loaded"], warnings=["beads warning"])

    monkeypatch.setattr(workflows.beads, "pull_beads_for_all", fake_pull_beads_for_all)

    result = workflows.refresh_project(
        dotbrain_home,
        "refreshme",
        run=_git_runner(dotbrain_home),
    )

    assert result.refreshed == ["refreshme"]
    assert (repo / ".codex").is_dir()
    assert not (repo / ".codex").is_symlink()
    assert "/.codex" not in paths.exclude_entries(repo)
    assert not (repo / ".claude" / "skills" / "wire-brain").exists()
    assert not (repo / ".codex" / "skills" / "wire-brain").exists()
    assert not legacy_skill.exists()
    assert loaded["projects"] == ["refreshme"]
    assert "shared tracker: beads loaded" in result.logs
    assert "beads warning" in result.warnings
    assert not any(line.startswith("linked skill ") for line in result.logs)


def test_refresh_project_links_subagents(tmp_path: Path, dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch):
    repo = _make_wired_repo(tmp_path, dotbrain_home, "refresh-subagents")
    brainspace = paths.brainspace(dotbrain_home, "refresh-subagents")
    (brainspace / ".repo").write_text(f"{repo}\n")
    (brainspace / ".brain" / "project.yaml").write_text(
        "agents:\n"
        "  - claude\n"
        "  - codex\n"
        "subagents:\n"
    "  - reviewer\n"
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    monkeypatch.setattr(
        workflows.beads,
        "pull_beads_for_all",
        lambda dotbrain_home_arg, *, run, projects: beads.BootstrapResult(logs=[], warnings=[]),
    )

    result = workflows.refresh_project(dotbrain_home, "refresh-subagents")

    assert result.refreshed == ["refresh-subagents"]
    assert not (repo / ".claude" / "agents" / "reviewer.md").exists()
    assert not (repo / ".claude" / "agents" / "verifier.md").exists()
    assert (repo / ".codex" / "agents" / "dotbrain-reviewer.toml").is_file()
    assert (repo / ".codex" / "agents" / "dotbrain-verifier.toml").is_file()
    assert len([entry for entry in result.targets[0].data["checkout_changes"] if entry.startswith("linked ")]) == len(subagents.PROJECT_BASELINE)  # Codex only; the plugin delivers to Claude Code


def test_refresh_project_honors_declared_agent_workspaces(
    tmp_path: Path, dotbrain_home: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = tmp_path / "claude-only"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)

    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        home=fake_home,
    )

    brainspace = paths.brainspace(dotbrain_home, "claude-only")
    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\nbeads: {mode: none}\n")
    claude_workspace = repo / ".claude"
    captured: dict[str, tuple[str, ...]] = {}

    def fake_link_project(dotbrain_home_arg, brainspace_arg, workspaces, skill_paths, **kwargs):
        captured["workspaces"] = tuple(workspaces)
        return skills.LinkResult()

    monkeypatch.setattr(workflows.skills, "link_project", fake_link_project)
    monkeypatch.setattr(
        workflows.beads,
        "pull_beads_for_all",
        lambda dotbrain_home_arg, *, run, projects: beads.BootstrapResult(logs=[], warnings=[]),
    )

    result = workflows.refresh_project(dotbrain_home, "claude-only")

    assert result.refreshed == ["claude-only"], result.errors
    assert captured["workspaces"] == (".claude",)
    assert claude_workspace.is_dir()
    assert not claude_workspace.is_symlink()
    assert (repo / ".codex").is_dir()
    assert not (brainspace / ".claude").exists()  # repo-backed: workspace lives in the repo
    assert not (brainspace / ".codex").exists()  # repo-backed: workspace lives in the repo


def test_refresh_project_does_not_rewire_preserved_undeclared_workspace(
    tmp_path: Path, dotbrain_home: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = tmp_path / "refresh-downgraded"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)

    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        home=fake_home,
    )
    brainspace = paths.brainspace(dotbrain_home, "refresh-downgraded")
    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n  - codex\nbeads: {mode: none}\n")
    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        home=fake_home,
    )
    assert (repo / ".codex").is_dir()

    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\nbeads: {mode: none}\n")
    captured: dict[str, tuple[str, ...]] = {}

    def fake_link_project(dotbrain_home_arg, brainspace_arg, workspaces, skill_paths, **kwargs):
        captured["workspaces"] = tuple(workspaces)
        return skills.LinkResult()

    monkeypatch.setattr(workflows.skills, "link_project", fake_link_project)
    monkeypatch.setattr(
        workflows.beads,
        "pull_beads_for_all",
        lambda dotbrain_home_arg, *, run, projects: beads.BootstrapResult(logs=[], warnings=[]),
    )

    result = workflows.refresh_project(dotbrain_home, "refresh-downgraded")

    assert result.refreshed == ["refresh-downgraded"], result.errors
    assert captured["workspaces"] == (".claude",)
    assert not (brainspace / ".codex").exists()  # repo-backed: workspace lives in the repo
    assert (repo / ".codex").is_dir()
def test_refresh_projects_warns_for_missing_repo_and_still_loads_beads(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    brainspace = paths.brainspace(dotbrain_home, "missing-repo")
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".claude").mkdir()
    (brainspace / ".codex").mkdir()
    (brainspace / ".repo").write_text("/does/not/exist\n")

    monkeypatch.setattr(
        workflows.beads,
        "pull_beads_for_all",
        lambda dotbrain_home_arg, *, run, projects: beads.BootstrapResult(logs=["beads loaded"]),
    )

    (brainspace / ".brain" / "project.yaml").write_text("agents: []\nbeads: {mode: none}\n", encoding="utf-8")
    result = workflows.refresh_projects(dotbrain_home, project="missing-repo")

    assert result.errors
    assert result.refreshed == []


def test_refresh_projects_silent_for_brain_only_project(
    dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    brainspace = paths.brainspace(dotbrain_home, "brain-only")
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".repo").write_text("(brain-only)\n")

    monkeypatch.setattr(
        workflows.beads,
        "pull_beads_for_all",
        lambda dotbrain_home_arg, *, run, projects: beads.BootstrapResult(logs=[]),
    )

    (brainspace / ".brain" / "project.yaml").write_text("agents: []\nbeads: {mode: none}\n", encoding="utf-8")
    result = workflows.refresh_projects(dotbrain_home, project="brain-only")

    assert result.refreshed == ["brain-only"]
    assert not any("(brain-only)" in warning for warning in result.warnings)
    assert not any("no repo found" in warning for warning in result.warnings)
