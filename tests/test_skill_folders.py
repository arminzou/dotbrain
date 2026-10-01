from pathlib import Path

import pytest

from dotbrain import assets, projects, skills


def write(path, content="skill"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_folder_expansion_precedence_dedup_and_node_modules(tmp_path):
    root = tmp_path / "skills"
    for name in ("bundle/a", "bundle/nested/b", "bundle/node_modules/ignored", "direct", "direct/child"):
        write(root / name / "SKILL.md")
    assert skills.resolve_selection(tmp_path, ["bundle", "bundle/a", "direct"]) == ("bundle/a", "bundle/nested/b", "direct")
    (root / "alias").symlink_to(root / "bundle/a", target_is_directory=True)
    assert skills.resolve_selection(tmp_path, ["alias", "bundle/a"]) == ("bundle/a",)


@pytest.mark.parametrize("entry", ["missing", "empty", "file", "/bundle", "../bundle", "C:/bundle"])
def test_bad_folder_selection_preserves_destinations_and_cache(tmp_path, entry):
    root = tmp_path / "skills"
    write(root / "bundle/a/SKILL.md")
    (root / "empty").mkdir()
    write(root / "file")
    cache = tmp_path / ".cache/skills/sentinel"
    write(cache)
    dest = tmp_path / "receiver"
    dest.mkdir()
    (dest / "old").symlink_to(root / "bundle/a", target_is_directory=True)
    result = skills.link_into(tmp_path, dest, ["bundle", entry], prune_owned_only=True, preserve_collisions=True)
    assert result.warnings
    assert (dest / "old").is_symlink() and not (dest / "a").exists()
    assert cache.exists()


@pytest.mark.parametrize("second", ["same", "Same"])
def test_casefold_collision_names_both_sources_before_any_writes(tmp_path, second):
    write(tmp_path / "skills/one/same/SKILL.md")
    write(tmp_path / "skills/two" / second / "SKILL.md")
    result = skills.link_into(tmp_path, tmp_path / "receiver", ["one", "two"], preserve_collisions=True)
    assert result.warnings and "one/same" in result.warnings[0] and f"two/{second}" in result.warnings[0]
    assert not (tmp_path / "receiver").exists()


def test_source_and_marker_symlinks_cannot_escape(tmp_path):
    home = tmp_path / "home"
    root = home / "skills"
    root.mkdir(parents=True)
    outside = tmp_path / "outside"
    write(outside / "SKILL.md")
    (root / "foreign").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        skills.resolve_selection(home, ["foreign"])
    (root / "marker").mkdir()
    (root / "marker/SKILL.md").symlink_to(outside / "SKILL.md")
    with pytest.raises(ValueError):
        skills.resolve_selection(home, ["marker"])
    with pytest.raises(ValueError):
        assets.catalog(home, "skills")


def test_catalog_and_source_helper_reject_escaped_skills_root(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    outside = tmp_path / "outside"
    write(outside / "skill/SKILL.md")
    (home / "skills").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        assets.catalog(home, "skills")
    with pytest.raises(ValueError):
        skills._resolve_skill_source(home, "skill")


def test_project_and_global_reconcile_folder_add_remove_without_yaml_changes(tmp_path):
    home = tmp_path / "home"
    root = home / "skills"
    write(root / "bundle/a/SKILL.md")
    write(root / "bundle/b/SKILL.md")
    global_yaml = "global_extra: [bundle]\n"
    write(root / "skills.yaml", global_yaml)
    brainspace = home / "brainspaces/example"
    declarations = "agents: [claude, codex]\nskills: [bundle]\n"
    write(brainspace / ".brain/project.yaml", declarations)
    project = tmp_path / "project"
    project.mkdir()
    (project / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
    (brainspace / ".repo").write_text(str(project), encoding="utf-8")
    target = projects.ProjectTarget("example", brainspace, project)
    # The injected seam avoids requiring Git for this source/delivery check.
    import subprocess
    run = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, str(project / ".git/info/exclude") + "\n", "")
    first = assets.link_project(home, target, "skills", run=run)
    assert len(first.linked) == 4
    global_result = assets.link_global(home, "skills", user_home=tmp_path / "user")
    assert len(global_result.linked) == 4
    assert assets.link_project(home, target, "skills", run=run).linked == []
    (root / "bundle/b/SKILL.md").unlink()
    (root / "bundle/b").rmdir()
    write(root / "bundle/c/SKILL.md")
    result = assets.link_project(home, target, "skills", run=run)
    assert len(result.linked) == 2 and len(result.pruned) == 2
    result = assets.link_global(home, "skills", user_home=tmp_path / "user")
    assert len(result.linked) == 2 and len(result.pruned) == 2
    assert (root / "skills.yaml").read_text() == global_yaml
    assert (brainspace / ".brain/project.yaml").read_text() == declarations
    report = projects.inspect_project(home, target)
    assert report["skills"] == {"configured": ["bundle"], "effective": ["bundle/a", "bundle/c"]}
    catalog = assets.catalog(home, "skills", project="example")
    assert {item["name"] for item in catalog if item["selected"]} == {"bundle/a", "bundle/c"}
