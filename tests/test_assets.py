import json
from pathlib import Path
import pytest

from typer.testing import CliRunner

from dotbrain import assets, projects, skills, subagents
from dotbrain.cli import app


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.parametrize("kind", ["skills", "agents"])
@pytest.mark.parametrize("runtime", ["all", "codex"])
def test_asset_batch_isolates_malformed_declaration(tmp_path, kind, runtime):
    home = tmp_path / "home"
    for name, declaration in (("bad", "agents: ["), ("good", "agents: [codex]\n")):
        brainspace = home / "brainspaces" / name
        write(brainspace / ".brain/project.yaml", declaration)
        repo = tmp_path / name
        (repo / ".codex").mkdir(parents=True)
        (repo / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
        write(brainspace / ".repo", str(repo))
    result = CliRunner().invoke(app, [kind, "link", "--all", "--home", str(home),
                                     "--runtime", runtime, "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert [(target["project"], target["status"]) for target in payload["targets"]] == [
        ("bad", "failure"), ("good", "success")]


def test_codex_delivery_migrates_updates_prunes_and_preserves_foreign(tmp_path):
    home = tmp_path / "home"
    source = home / "agents/codex/reviewer.toml"
    write(source, 'name = "reviewer"\n')
    dest = tmp_path / "repo/.codex/agents"
    dest.mkdir(parents=True)
    (dest / source.name).symlink_to(source)
    write(dest / "custom.toml", 'name = "custom"\n')
    foreign = tmp_path / "foreign.toml"
    write(foreign, "foreign")
    (dest / "foreign.toml").symlink_to(foreign)
    first = subagents.link_files_into(home, dest, [source], label="agents", preserve_collisions=True, runtime="codex")
    assert first.linked == ["agents/reviewer.toml"]
    copy = dest / source.name
    assert not copy.is_symlink() and subagents.is_managed_copy(copy)
    assert subagents.link_files_into(home, dest, [source], label="agents", preserve_collisions=True, runtime="codex").linked == []
    write(source, 'name = "new"\n')
    subagents.link_files_into(home, dest, [source], label="agents", preserve_collisions=True, runtime="codex")
    assert 'name = "new"' in copy.read_text()
    copy.write_text(copy.read_text() + "# local disposable edit\n")
    subagents.link_files_into(home, dest, [source], label="agents", preserve_collisions=True, runtime="codex")
    assert "disposable" not in copy.read_text()
    result = subagents.link_files_into(home, dest, [], label="agents", preserve_collisions=True, runtime="codex")
    assert result.pruned == ["agents/reviewer.toml"]
    assert (dest / "custom.toml").read_text() == 'name = "custom"\n'
    assert (dest / "foreign.toml").is_symlink()


def test_unmarked_codex_collision_preserved(tmp_path):
    source = tmp_path / "home/agents/codex/reviewer.toml"
    write(source, "source")
    dest = tmp_path / "dest"
    write(dest / source.name, "user")
    result = subagents.link_files_into(tmp_path / "home", dest, [source], label="agents", preserve_collisions=True, runtime="codex")
    assert result.warnings and (dest / source.name).read_text() == "user"


def test_agent_runtime_selection_failure_does_not_prune(tmp_path):
    home = tmp_path / "home"
    write(home / "agents/claude/custom.md", "custom")
    dest = tmp_path / "workspace/.claude/agents"
    dest.mkdir(parents=True)
    old = dest / "old.md"
    old.symlink_to(home / "agents/claude/custom.md")
    result = subagents.link_project_subagents(home, tmp_path, (".claude", ".codex"), ["custom"], workspace_dirs={".claude": tmp_path / "workspace/.claude"})
    assert result.warnings and old.is_symlink()
    assert not (tmp_path / ".codex").exists()


def test_skill_collision_no_mutation(tmp_path):
    for name in ("a/same", "b/same"):
        write(tmp_path / "home/skills" / name / "SKILL.md", name)
    dest = tmp_path / "dest"
    result = skills.link_into(tmp_path / "home", dest, ["a/same", "b/same"], preserve_collisions=True)
    assert result.warnings and not dest.exists()


def test_catalogs_and_invalid_json_selection(tmp_path):
    write(tmp_path / "skills/test/SKILL.md", "test")
    runner = CliRunner()
    for kind in ("skills", "agents"):
        result = runner.invoke(app, [kind, "list", "--home", str(tmp_path), "--runtime", "codex", "--json"])
        assert result.exit_code == 0, result.output
        rows = json.loads(result.stdout)["targets"][0]["data"]["assets"]
        assert rows
        for args in (["--scope", "all"], ["--runtime", "other"], ["--project", "missing"], ["--scope", "global", "--all"]):
            result = runner.invoke(app, [kind, "link", "--home", str(tmp_path), "--json", *args])
            assert result.exit_code == 2, result.output
            assert json.loads(result.stdout)["status"] == "failure"


def test_foreign_asset_receiver_and_cache_cannot_redirect_writes(tmp_path):
    import pytest
    home = tmp_path / "home"
    brainspace = home / "brainspaces/example"
    write(brainspace / ".brain/project.yaml", "agents: [codex]\n")
    repo = tmp_path / "repo"
    (repo / ".codex").mkdir(parents=True)
    (repo / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (repo / ".codex/agents").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match="foreign asset directory"):
        assets.link_project(home, projects.ProjectTarget("example", brainspace, repo), "agents")
    assert list(foreign.iterdir()) == []
    (home / ".cache").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError):
        subagents.sync_packaged_subagents(home)
    assert list(foreign.iterdir()) == []


def test_private_agent_seed_cannot_write_through_foreign_directory(tmp_path):
    import pytest
    home = tmp_path / "home"
    home.mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (home / "agents").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError):
        subagents.seed_private_subagents(home)
    assert list(foreign.iterdir()) == []


def test_skill_cache_parent_escape_preserves_external_data_and_destination(tmp_path):
    home = tmp_path / "home"
    write(home / "skills/source/SKILL.md", "skill")
    outside = tmp_path / "outside"
    protected = outside / "skills/user.txt"
    write(protected, "user content")
    (home / ".cache").symlink_to(outside, target_is_directory=True)
    destination = tmp_path / "destination"
    result = skills.link_into(home, destination, ["source"], preserve_collisions=True)
    assert result.warnings
    assert protected.read_text() == "user content"
    assert not destination.exists()
    with pytest.raises(ValueError, match="escapes"):
        skills._remove_legacy_skill_cache(home)
    assert protected.is_file()
