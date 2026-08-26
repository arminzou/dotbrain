"""Tests for workflows.py — wire/unwire orchestration and scenario 9 adopter edge cases."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dotbrain import beads, bootstrap as bootstrap_mod, config, paths, skills, workflows


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


def _commit_brainspace(dotbrain_home: Path, name: str) -> None:
    """Commit a Brainspace into the dotbrain git so git mv/rm work."""
    brainspace = paths.brainspace(dotbrain_home, name)
    (brainspace / ".brain").mkdir(parents=True, exist_ok=True)
    (brainspace / ".brain" / "AGENTS.md").write_text(f"# {name}\n")
    subprocess.run(
        ["git", "-C", str(dotbrain_home), "add", f"brainspaces/{name}"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(dotbrain_home), "commit", "-q", "-m", f"feat(brain): wire {name}"],
        check=True, capture_output=True,
    )


def _seed_byproducts(brainspace: Path) -> list[Path]:
    """Drop in gitignored runtime/wiring litter an offboard must strip."""
    bootstrap_mod.ensure_root_gitignore(brainspace.parents[1])
    runtime = brainspace / ".beads" / "metadata.json"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_text("{}")
    skills = brainspace / ".claude" / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    link = skills / "build-context"
    link.symlink_to("/tmp/build-context")
    return [runtime, link]


def test_offboard_archive_strips_byproducts_and_stages_git_mv(dotbrain_home: Path):
    _commit_brainspace(dotbrain_home, "proj-archive")
    byproducts = _seed_byproducts(dotbrain_home / "brainspaces" / "proj-archive")

    logs = workflows.offboard_brainspace(
        dotbrain_home, "proj-archive", "archive", run=_git_runner(dotbrain_home)
    )

    archive = dotbrain_home / "brainspaces" / ".archive" / "proj-archive"
    assert archive.is_dir()
    assert (archive / ".brain" / "AGENTS.md").exists()  # tracked content moved
    assert not (archive / ".beads" / "metadata.json").exists()  # litter not dragged along
    assert not (archive / ".claude" / "skills" / "build-context").exists()
    assert any("archived" in l for l in logs)
    assert not (dotbrain_home / "brainspaces" / "proj-archive").exists()


# --------------------------------------------------------------------------- delete


def test_offboard_delete_strips_byproducts_and_leaves_no_dir(dotbrain_home: Path):
    _commit_brainspace(dotbrain_home, "proj-delete")
    _seed_byproducts(dotbrain_home / "brainspaces" / "proj-delete")

    logs = workflows.offboard_brainspace(
        dotbrain_home, "proj-delete", "delete", run=_git_runner(dotbrain_home)
    )

    # no orphan directory left behind by the gitignored byproducts
    assert not (dotbrain_home / "brainspaces" / "proj-delete").exists()
    assert any("removed" in l for l in logs)


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
        install_global_hook=False,
        home=Path.home(),
        run=real_git_runner,
    )
    assert (repo / ".brain").is_symlink()
    if paths.INJECT_ADOPTER_POINTER:
        assert paths.ADOPTER_POINTER in (repo / "AGENTS.md").read_text()

    workflows.unwire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        offboard="keep",
        run=real_git_runner,
    )

    for name in (".brain", ".beads", ".claude"):
        assert not (repo / name).exists()
    assert (repo / ".codex").is_dir()
    assert paths.ADOPTER_POINTER not in (repo / "AGENTS.md").read_text()
    exclude_lines = (repo / ".git" / "info" / "exclude").read_text().splitlines()
    for entry in paths.EXCLUDE_ENTRIES:
        assert entry not in exclude_lines
    # Brainspace kept
    assert paths.brainspace(dotbrain_home, "roundtrip").is_dir()


# --------------------------------------------------------------------------- missing Brainspace


def test_offboard_warns_when_brainspace_missing(dotbrain_home: Path):
    logs = workflows.offboard_brainspace(dotbrain_home, "ghost", "keep")
    assert any("not found" in l for l in logs)

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


def test_unwire_no_repo_delete_committed_root(dotbrain_home: Path):
    _commit_brainspace(dotbrain_home, "brain-only")
    # a tracked file with local modifications must not block delete (git rm needs -f)
    (dotbrain_home / "brainspaces" / "brain-only" / ".brain" / "AGENTS.md").write_text("# changed\n")
    calls: list[list[str]] = []

    def run(argv, *, cwd=None, env=None, check=True, **kwargs):
        calls.append(list(argv))
        return subprocess.run(list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True)

    result = workflows.unwire_project(
        dotbrain_home=dotbrain_home,
        project="brain-only",
        no_repo=True,
        offboard="delete",
        run=run,
    )

    assert not (dotbrain_home / "brainspaces" / "brain-only").exists()
    assert any("removed Brainspace" in line for line in result.logs)
    assert not any(call[0] == "ssh" for call in calls)  # DB drop is no longer coupled to unwire


def test_unwire_no_repo_delete_uncommitted_root(dotbrain_home: Path):
    # wire no longer commits, so a freshly-wired root is untracked: delete must not crash on
    # git rm, and git clean -X must not wipe the (untracked) brain before it is removed.
    brainspace = paths.brainspace(dotbrain_home, "fresh")
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".brain" / "AGENTS.md").write_text("# fresh\n")
    _seed_byproducts(brainspace)

    result = workflows.unwire_project(
        dotbrain_home=dotbrain_home, project="fresh", no_repo=True, offboard="delete",
        run=_git_runner(dotbrain_home),
    )

    assert not brainspace.exists()
    assert any("removed Brainspace" in line for line in result.logs)


def test_unwire_no_repo_archive_uncommitted_root(dotbrain_home: Path):
    brainspace = paths.brainspace(dotbrain_home, "fresh")
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".brain" / "AGENTS.md").write_text("# fresh\n")

    result = workflows.unwire_project(
        dotbrain_home=dotbrain_home, project="fresh", no_repo=True, offboard="archive",
        run=_git_runner(dotbrain_home),
    )

    archived = dotbrain_home / "brainspaces" / ".archive" / "fresh"
    assert (archived / ".brain" / "AGENTS.md").exists()  # brain survives the move
    assert not brainspace.exists()
    assert any("uncommitted" in line for line in result.logs)


def test_unwire_no_repo_delete_dry_run_keeps_root(dotbrain_home: Path):
    _commit_brainspace(dotbrain_home, "brain-only")
    calls: list[list[str]] = []

    def run(argv, *, cwd=None, env=None, check=True, **kwargs):
        calls.append(list(argv))
        return subprocess.run(list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True)

    result = workflows.unwire_project(
        dotbrain_home=dotbrain_home, project="brain-only", no_repo=True, offboard="delete",
        dry_run=True, run=run,
    )

    assert (dotbrain_home / "brainspaces" / "brain-only").exists()
    assert any("would remove Brainspace brainspaces/brain-only" in line for line in result.logs)
    assert not any(call[0] == "ssh" for call in calls)


def test_unwire_delete_removes_projects_entry(dotbrain_home: Path):
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\nprojects:\n  fresh:\n    beads:\n      mode: embedded\n"
    )
    brainspace = paths.brainspace(dotbrain_home, "fresh")
    (brainspace / ".brain").mkdir(parents=True)

    result = workflows.unwire_project(
        dotbrain_home=dotbrain_home, project="fresh", no_repo=True, offboard="delete",
        run=_git_runner(dotbrain_home),
    )

    assert not (dotbrain_home / "brainspaces" / "fresh" / ".brain" / "project.yaml").exists()
    assert any("removed" in line for line in result.logs)


def test_unwire_keep_preserves_projects_entry(dotbrain_home: Path):
    (dotbrain_home / "dotbrain.yaml").write_text(
        "version: 2\nprojects:\n  fresh:\n    beads:\n      mode: embedded\n"
    )
    brainspace = paths.brainspace(dotbrain_home, "fresh")
    (brainspace / ".brain").mkdir(parents=True)

    workflows.unwire_project(
        dotbrain_home=dotbrain_home, project="fresh", no_repo=True, offboard="keep",
        run=_git_runner(dotbrain_home),
    )

    assert config.load_project_config(dotbrain_home, "fresh").mode == "embedded"


# --------------------------------------------------------------------------- unwire --all (batch)


def test_refresh_project_repairs_repo_links_links_skills_and_loads_beads(
    tmp_path: Path, dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _make_wired_repo(tmp_path, dotbrain_home, "refreshme")
    brainspace = paths.brainspace(dotbrain_home, "refreshme")
    (brainspace / ".repo").write_text(f"{repo}\n")
    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n  - codex\n")
    loaded: dict[str, object] = {}

    def fake_pull_beads_for_all(dotbrain_home_arg, *, run, projects):
        loaded["root"] = dotbrain_home_arg
        loaded["projects"] = list(projects)
        return beads.BootstrapResult(logs=["beads loaded"], warnings=["beads warning"])

    monkeypatch.setattr(workflows.beads, "pull_beads_for_all", fake_pull_beads_for_all)

    result = workflows.refresh_project(
        dotbrain_home,
        "refreshme",
        repo_base=tmp_path,
        run=_git_runner(dotbrain_home),
    )

    assert result.refreshed == ["refreshme"]
    assert (repo / ".codex").is_dir()
    assert not (repo / ".codex").is_symlink()
    assert "/.codex" not in paths.exclude_entries(repo)
    for skill_path in skills.project_baseline(dotbrain_home):
        skill_name = Path(skill_path).name
        assert (brainspace / ".claude" / "skills" / skill_name).is_symlink()
        assert (repo / ".codex" / "skills" / skill_name).is_symlink()
    assert loaded["projects"] == ["refreshme"]
    assert "beads loaded" in result.logs
    assert "beads warning" in result.warnings
    assert not any(line.startswith("linked skill ") for line in result.logs)
    linked_count = len(skills.project_baseline(dotbrain_home)) * 2  # .claude + .codex
    assert f"refreshed refreshme ({linked_count} skills linked)" in result.logs


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

    result = workflows.refresh_project(dotbrain_home, "refresh-subagents", repo_base=tmp_path, home=fake_home)

    assert result.refreshed == ["refresh-subagents"]
    assert (brainspace / ".claude" / "agents" / "reviewer.md").is_symlink()
    assert (brainspace / ".claude" / "agents" / "verifier.md").is_symlink()
    assert (repo / ".codex" / "agents" / "reviewer.toml").is_symlink()
    assert (repo / ".codex" / "agents" / "verifier.toml").is_symlink()
    assert "project: linked 8 subagent file(s) into refresh-subagents" in result.logs


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
        install_global_hook=False,
        home=fake_home,
    )

    brainspace = paths.brainspace(dotbrain_home, "claude-only")
    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n")
    claude_link = repo / ".claude"
    claude_link.unlink()
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

    result = workflows.refresh_project(dotbrain_home, "claude-only", repo_base=tmp_path, home=fake_home)

    assert result.refreshed == ["claude-only"]
    assert captured["workspaces"] == (".claude",)
    assert claude_link.is_symlink()
    assert (repo / ".codex").is_dir()
    assert (brainspace / ".claude").is_dir()
    assert (brainspace / ".codex").exists()


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
        install_global_hook=False,
        home=fake_home,
    )
    brainspace = paths.brainspace(dotbrain_home, "refresh-downgraded")
    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n  - codex\n")
    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
    )
    assert (repo / ".codex").is_dir()

    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n")
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

    result = workflows.refresh_project(dotbrain_home, "refresh-downgraded", repo_base=tmp_path, home=fake_home)

    assert result.refreshed == ["refresh-downgraded"]
    assert captured["workspaces"] == (".claude",)
    assert (brainspace / ".codex").is_dir()
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

    result = workflows.refresh_projects(dotbrain_home, projects=["missing-repo"])

    assert result.refreshed == ["missing-repo"]
    assert any("no repo found" in warning or "not a git repo" in warning for warning in result.warnings)
    assert "beads loaded" in result.logs


def _wired_project(tmp_path: Path, dotbrain_home: Path, name: str) -> Path:
    """A wired adopter repo plus a Brainspace .repo pointer so batch unwire can resolve it."""
    repo = _make_wired_repo(tmp_path, dotbrain_home, name)
    (paths.brainspace(dotbrain_home, name) / ".repo").write_text(f"{repo}\n")
    return repo


def test_unwire_all_disconnects_every_repo(tmp_path: Path, dotbrain_home: Path):
    repo_a = _wired_project(tmp_path, dotbrain_home, "proj-a")
    repo_b = _wired_project(tmp_path, dotbrain_home, "proj-b")

    results = workflows.unwire_all_projects(
        dotbrain_home=dotbrain_home, run=_git_runner(dotbrain_home),
    )

    assert {r.project for r in results} == {"proj-a", "proj-b"}
    for repo in (repo_a, repo_b):
        for link in paths.BRAINSPACE_LINKS:
            assert not (repo / link).exists()
        assert paths.ADOPTER_POINTER not in (repo / "AGENTS.md").read_text()


def test_unwire_all_dry_run_preserves_repos(tmp_path: Path, dotbrain_home: Path):
    # Regression: --dry-run must not touch adopter repos. The repo disconnect once
    # ran unconditionally, so a "preview" silently removed live symlinks.
    repo = _wired_project(tmp_path, dotbrain_home, "proj-dry")

    results = workflows.unwire_all_projects(
        dotbrain_home=dotbrain_home, dry_run=True, run=_git_runner(dotbrain_home),
    )

    for link in paths.BRAINSPACE_LINKS:
        assert (repo / link).is_symlink()
    assert paths.ADOPTER_POINTER in (repo / "AGENTS.md").read_text()
    logs = [line for r in results for line in r.logs]
    assert any("would remove symlink" in line for line in logs)


def test_unwire_all_skips_brain_only_project(tmp_path: Path, dotbrain_home: Path):
    brainspace = paths.brainspace(dotbrain_home, "brain-only")
    (brainspace / ".brain").mkdir(parents=True)

    results = workflows.unwire_all_projects(
        dotbrain_home=dotbrain_home, run=_git_runner(dotbrain_home),
    )

    brain_only = next(r for r in results if r.project == "brain-only")
    assert brain_only.repo is None
    assert not any("error" in line for line in brain_only.logs)


def test_unwire_all_continues_after_one_project_fails(
    tmp_path: Path, dotbrain_home: Path, monkeypatch: pytest.MonkeyPatch
):
    repo_ok = _wired_project(tmp_path, dotbrain_home, "proj-ok")
    _wired_project(tmp_path, dotbrain_home, "proj-bad")
    real_unwire_repo = workflows.unwire_repo

    def flaky(repo: Path, dry_run: bool = False):
        if repo.name == "proj-bad":
            raise RuntimeError("boom")
        return real_unwire_repo(repo, dry_run=dry_run)

    monkeypatch.setattr(workflows, "unwire_repo", flaky)

    results = workflows.unwire_all_projects(
        dotbrain_home=dotbrain_home, run=_git_runner(dotbrain_home),
    )

    by_project = {r.project: r for r in results}
    assert any("error unwiring proj-bad" in line for line in by_project["proj-bad"].logs)
    for link in paths.BRAINSPACE_LINKS:
        assert not (repo_ok / link).exists()
