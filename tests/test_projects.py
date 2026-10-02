"""Hermetic selection and discovery contracts."""
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import adopter_repos, paths, projects
from dotbrain.cli import app


def seed(tmp_path, name="identity"):
    home = tmp_path / "data"
    brainspace = paths.brainspace(home, name)
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".brain" / "project.yaml").write_text("agents: [codex]\nbeads:\n  mode: none\n", encoding="utf-8")
    repo = tmp_path / "different-checkout-name"
    repo.mkdir()
    (repo / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
    (brainspace / ".repo").write_text(str(repo), encoding="utf-8")
    return home, brainspace, repo


def test_selection_uses_git_root_and_wired_identity(tmp_path):
    home, brainspace, repo = seed(tmp_path)
    nested = repo / "nested"
    nested.mkdir()
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, stdout=str(repo))
    target, = projects.select_projects(home, cwd=nested, run=run)
    assert target == projects.ProjectTarget("identity", brainspace, repo.resolve())
    assert calls[0][1]["cwd"] == nested


def test_named_local_override_and_brain_only(tmp_path):
    home, brainspace, repo = seed(tmp_path)
    other = tmp_path / "local"
    other.mkdir()
    (brainspace / ".repo.local").write_text(str(other), encoding="utf-8")
    assert projects.select_projects(home, project="identity")[0].checkout == other
    (brainspace / ".repo.local").write_text("(brain-only)", encoding="utf-8")
    assert projects.select_projects(home, project="identity")[0].checkout is None
    with pytest.raises(ValueError, match="no available checkout"):
        projects.select_projects(home, project="identity", require_checkout=True)


def test_selector_conflicts_and_missing_projects(tmp_path):
    home, _, repo = seed(tmp_path)
    with pytest.raises(ValueError, match="cannot be combined"):
        projects.select_projects(home, project="identity", all_projects=True)
    with pytest.raises(ValueError, match="does not exist"):
        projects.select_projects(home, project="missing")
    def run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, stdout=str(repo))
    with pytest.raises(ValueError, match="does not match"):
        projects.select_projects(home, project="other", repo=repo, run=run)
    assert not paths.brainspace(home, "missing").exists()


def test_unwired_and_foreign_checkout_rejected(tmp_path):
    home, brainspace, repo = seed(tmp_path)
    (repo / ".brain").unlink()
    with pytest.raises(ValueError, match="not wired"):
        projects._wired(home, repo)
    foreign = tmp_path / "foreign" / "brainspaces" / "identity" / ".brain"
    foreign.mkdir(parents=True)
    (repo / ".brain").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match="conflicts"):
        projects._wired(home, repo)
    with pytest.raises(RuntimeError, match="another dotbrain"):
        adopter_repos.wire_repo(repo, brainspace, home)
    assert (repo / ".brain").resolve() == foreign


@pytest.mark.parametrize("name", ["", ".hidden", "..", "../escape", "a/b", "a\\b", "C:drive", "/abs", "CON", "nul.txt", "bad?", "trailing.", "trailing "])
def test_invalid_names_rejected_without_writes(tmp_path, name):
    with pytest.raises(ValueError, match="invalid project name"):
        paths.brainspace(tmp_path, name)
    assert list(tmp_path.iterdir()) == []


def test_symlink_parent_escape_rejected(tmp_path):
    home = tmp_path / "data"
    home.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (home / "brainspaces").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        paths.brainspace(home, "identity")
    assert list(outside.iterdir()) == []


def test_project_symlink_escape_and_asset_escape_rejected(tmp_path):
    home, _, _ = seed(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (home / "brainspaces" / "escaped").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        paths.brainspaces(home)
    with pytest.raises(ValueError, match="inside"):
        paths.confined_path(home / "skills", "../outside")


def test_discovery_reports_local_declarations_without_subprocesses(tmp_path, monkeypatch):
    home, _, repo = seed(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("discovery must not invoke subprocesses")
    monkeypatch.setattr(subprocess, "run", forbidden)
    report, = projects.list_projects(home)
    assert report["project"] == "identity"
    assert report["checkout"] == str(repo)
    assert report["runtimes"] == ["codex"]
    assert report["beads"]["mode"] == "none"
    assert report["wiring"] == {".brain": "healthy"}


def test_projects_list_remains_available_with_missing_selected_skill(tmp_path):
    home, brainspace, _ = seed(tmp_path)
    declaration = brainspace / ".brain/project.yaml"
    declaration.write_text(declaration.read_text() + "skills: [missing]\n", encoding="utf-8")
    result = CliRunner().invoke(app, ["projects", "list", "--home", str(home), "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["targets"][0]["project"] == "identity"
    result = CliRunner().invoke(app, ["projects", "show", "--project", "identity",
                                    "--home", str(home), "--json"])
    assert result.exit_code == 2


@pytest.mark.parametrize("declaration", ["agents: [", "agents: []\nbeads: server\n"])
def test_projects_list_isolates_malformed_declaration(tmp_path, declaration):
    home, _, _ = seed(tmp_path)
    bad = home / "brainspaces/bad/.brain"
    bad.mkdir(parents=True)
    (bad / "project.yaml").write_text(declaration, encoding="utf-8")
    for extra in ([], ["--json"]):
        result = CliRunner().invoke(app, ["projects", "list", "--home", str(home), *extra])
        assert result.exit_code == 1, result.output
        if extra:
            payload = json.loads(result.stdout)
            assert payload["status"] == "partial"
            assert [(target["project"], target["status"]) for target in payload["targets"]] == [
                ("bad", "failure"), ("identity", "success")]
        else:
            assert "identity" in result.stdout and "bad" in result.stdout
            assert "Declaration error" in result.stdout and "error:" in result.stdout


def test_projects_cli_json_and_selection_failure(tmp_path):
    home, _, _ = seed(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["projects", "list", "--home", str(home), "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["targets"][0]["project"] == "identity"
    result = runner.invoke(app, ["projects", "show", "--project", "missing", "--home", str(home), "--json"])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["errors"]


def test_real_git_nested_main_and_wired_worktree_selection(tmp_path):
    home, brainspace, repo = seed(tmp_path)
    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    git("init")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "initial")
    worktree = tmp_path / "worktree-with-another-name"
    git("worktree", "add", "-b", "test-worktree", str(worktree))
    (worktree / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
    nested = worktree / "nested"
    nested.mkdir()
    target, = projects.select_projects(home, cwd=nested)
    assert target.project == "identity"
    assert target.checkout == worktree.resolve()
    assert projects.select_projects(home, project="identity")[0].checkout == repo
    assert projects.select_projects(home, repo=nested)[0] == target


def test_same_root_other_project_refused_before_link_changes(tmp_path):
    home, brainspace, repo = seed(tmp_path)
    other = paths.brainspace(home, "other")
    (other / ".brain").mkdir(parents=True)
    before = (repo / ".brain").resolve()
    with pytest.raises(RuntimeError, match="another Brainspace"):
        adopter_repos.ensure_wiring_matches(repo, home, "other")
    with pytest.raises(RuntimeError, match="another Brainspace"):
        adopter_repos.wire_repo(repo, other, home)
    assert (repo / ".brain").resolve() == before
    assert not (repo / ".beads").exists()


def test_projects_text_exposes_settings_and_brain_only(tmp_path):
    home, brainspace, _ = seed(tmp_path)
    (brainspace / ".repo.local").write_text("(brain-only)", encoding="utf-8")
    result = CliRunner().invoke(app, ["projects", "show", "--project", "identity", "--home", str(home)])
    assert result.exit_code == 0, result.output
    assert "identity" in result.stdout and "Brain-only" in result.stdout
    assert "Runtimes" in result.stdout and "Codex" in result.stdout
    assert "Tracker" in result.stdout and "none" in result.stdout
    assert "Settings" in result.stdout and "beads.mode" in result.stdout
    assert "Effective skills" in result.stdout


def test_discovery_child_symlink_escape_rejected(tmp_path):
    home, brainspace, _ = seed(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    (external / "project.yaml").write_text("agents: []", encoding="utf-8")
    (brainspace / ".brain" / "project.yaml").unlink()
    (brainspace / ".brain").rmdir()
    (brainspace / ".brain").symlink_to(external, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        projects.list_projects(home)
