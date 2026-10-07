"""Disposable main/worktree flow through the public CLI with enabled runtimes."""
import json
import subprocess

import yaml
from typer.testing import CliRunner

from conftest import set_fake_home
from dotbrain.cli import app
from dotbrain import subagents


def test_named_detach_rejects_another_projects_wiring(tmp_path, monkeypatch):
    from dotbrain import workflows
    import pytest

    home = tmp_path / "data"
    selected = home / "brainspaces" / "selected"
    foreign = home / "brainspaces" / "other" / ".brain"
    (selected / ".brain").mkdir(parents=True)
    foreign.mkdir(parents=True)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (selected / ".repo").write_text(str(checkout), encoding="utf-8")
    link = checkout / ".brain"
    link.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(RuntimeError, match="another Brainspace"):
        workflows.unwire_project(dotbrain_home=home, project="selected")
    assert link.is_symlink() and link.resolve() == foreign


def test_main_worktree_maintenance_and_detachment(tmp_path, monkeypatch):
    runtime_home = tmp_path / "runtime-home"
    runtime_home.mkdir()
    set_fake_home(monkeypatch, runtime_home)
    home = tmp_path / "data"
    runner = CliRunner()

    def invoke(*args):
        result = runner.invoke(app, [*args, "--home", str(home), "--json"])
        assert result.exit_code == 0, result.output
        return json.loads(result.stdout)

    invoke("bootstrap")
    main = tmp_path / "custom-checkout"
    main.mkdir()

    def git(*args):
        return subprocess.run(["git", "-C", str(main), *args], check=True,
                              capture_output=True, text=True)

    git("init")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "--allow-empty", "-m", "seed")
    invoke("wire", "--repo", str(main), "--project", "sample", "--skip-beads")
    brainspace = home / "brainspaces" / "sample"
    declaration = brainspace / ".brain" / "project.yaml"
    settings = yaml.safe_load(declaration.read_text(encoding="utf-8"))
    settings["skills"] = ["bundle"]
    settings["operator-extra"] = {"preserve": True}
    declaration.write_text(yaml.safe_dump(settings, sort_keys=False), encoding="utf-8")
    for name in ("alpha", "beta"):
        source = home / "skills" / "bundle" / name
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    before = {path: path.read_bytes() for path in (declaration, brainspace / ".repo")}
    worktree = tmp_path / "feature-checkout"
    git("worktree", "add", "-b", "feature", str(worktree))
    user_dir = worktree / ".claude" / "notes" / "empty"
    user_dir.mkdir(parents=True)
    user_file = worktree / ".codex" / "config.toml"
    user_file.parent.mkdir()
    user_file.write_text('personality = "pragmatic"\n', encoding="utf-8")
    invoke("wire", "--repo", str(worktree))
    assert invoke("wire", "--repo", str(worktree))["targets"][0]["changes"] == []
    nested = worktree / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)
    refreshed = invoke("refresh")
    assert refreshed["targets"][0]["project"] == "sample"
    assert invoke("refresh")["targets"][0]["changes"] == []
    for workspace in (".claude", ".codex"):
        for name in ("alpha", "beta"):
            link = worktree / workspace / "skills" / name
            assert link.is_symlink()
            assert link.resolve() == home / "skills" / "bundle" / name
    assert subagents.is_managed_copy(worktree / ".codex" / "agents" / "dotbrain-reviewer.toml")
    assert not (worktree / ".claude" / "agents" / "reviewer.md").exists()
    assert {path: path.read_bytes() for path in before} == before
    assert [path.name for path in (home / "brainspaces").iterdir()] == ["sample"]
    def snapshot():
        return {str(path): path.read_bytes() for root in (home, worktree)
                for path in root.rglob("*") if path.is_file() and not path.is_symlink()}

    before_diagnosis = snapshot()
    diagnosis = invoke("doctor")
    selected = next(target for target in diagnosis["targets"] if target["project"] == "sample")
    assert selected["checkout"] == str(worktree)
    assert snapshot() == before_diagnosis
    invoke("unwire")
    assert user_file.read_text(encoding="utf-8") == 'personality = "pragmatic"\n'
    assert user_dir.is_dir()
    assert not (worktree / ".brain").exists()
    assert (main / ".brain").is_symlink()
    assert brainspace.is_dir()
    assert {path: path.read_bytes() for path in before} == before
