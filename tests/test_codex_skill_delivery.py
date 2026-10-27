"""Codex skill migration through disposable checkouts and real lifecycle entry points."""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import adopter_repos, assets, beads, doctor, projects, runtimes, skills, subagents, workflows
from dotbrain.cli import app


@pytest.fixture(scope="session")
def migration_repo_seed(tmp_path_factory):
    repo = tmp_path_factory.mktemp("migration-seed") / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c",
                    "user.email=test@example.invalid", "commit", "--allow-empty", "-qm", "seed"], check=True)
    return repo


@pytest.fixture
def delivery(dotbrain_home, migration_repo_seed, tmp_path):
    repo = tmp_path / "checkout"
    shutil.copytree(migration_repo_seed, repo, symlinks=True)
    brainspace = dotbrain_home / "brainspaces/sample"
    brain = brainspace / ".brain"
    brain.mkdir(parents=True)
    (brain / "project.yaml").write_text(
        "version: 2\nagents: [codex]\nskills: [misc/discovery-test]\nbeads: {mode: none}\n", encoding="utf-8")
    (brainspace / ".repo").write_text(str(repo), encoding="utf-8")
    (repo / ".brain").symlink_to(brain, target_is_directory=True)
    return dotbrain_home, brainspace, repo


def link(delivery):
    home, brainspace, repo = delivery
    return assets.link_project(home, projects.ProjectTarget("sample", brainspace, repo), "skills", "codex")


def legacy_link(delivery, name="discovery-test", source="skills/misc/discovery-test"):
    home, _, repo = delivery
    entry = repo / ".codex/skills" / name
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.symlink_to(home / source, target_is_directory=True)
    return entry


@pytest.mark.skipif(os.name != "nt", reason="Windows case-insensitive destinations")
def test_case_variant_legacy_collision_preserves_old_link(delivery):
    _, _, repo = delivery
    old = legacy_link(delivery, "DISCOVERY-TEST")
    destination = repo / ".agents/skills/discovery-test"
    destination.parent.mkdir(parents=True)
    destination.write_text("foreign", encoding="utf-8")
    result = link(delivery)
    assert result.warnings
    assert old.is_symlink()
    assert destination.read_text() == "foreign"


@pytest.mark.skipif(os.name != "nt", reason="Windows case-insensitive destinations")
def test_case_variant_owned_destination_converges(delivery):
    home, _, repo = delivery
    destination = repo / ".agents/skills/DISCOVERY-TEST"
    destination.parent.mkdir(parents=True)
    destination.symlink_to(home / "skills/misc/discovery-test", target_is_directory=True)
    for _ in range(2):
        result = link(delivery)
        assert result.linked == result.pruned == result.warnings == []
        assert destination.is_symlink()


def snapshot(root):
    """Include empty directories and exact link targets, without following any symlinks."""
    result = {}
    def visit(directory):
        for entry in directory.iterdir():
            relative = entry.relative_to(root).as_posix()
            metadata = entry.lstat()
            if entry.is_symlink() or (os.name == "nt" and metadata.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT):
                result[relative] = ("link", os.readlink(entry), metadata.st_mtime_ns)
            elif entry.is_dir():
                result[relative] = ("directory", metadata.st_mtime_ns)
                visit(entry)
            else:
                result[relative] = ("file", entry.read_bytes(), metadata.st_mtime_ns)
    visit(root)
    return result


def test_fresh_wire_refresh_link_doctor_unwire_converge(delivery, tmp_path):
    home, brainspace, repo = delivery
    declaration = brainspace / ".brain/project.yaml"
    declaration.write_text(declaration.read_text(encoding="utf-8") + "packaged-subagents: [worker]\n", encoding="utf-8")
    config = repo / ".codex/config.toml"
    config.parent.mkdir()
    config.write_text('personality = "pragmatic"\n', encoding="utf-8")
    user_agent = repo / ".codex/agents/mine.toml"
    user_agent.parent.mkdir()
    user_agent.write_text('name = "mine"\n', encoding="utf-8")
    assert not workflows.wire_project(dotbrain_home=home, repo=repo).errors
    entry = repo / ".agents/skills/discovery-test"
    assert entry.resolve() == (home / "skills/misc/discovery-test").resolve()
    assert not (repo / ".codex/skills").exists()
    assert subagents.is_managed_copy(repo / ".codex/agents/dotbrain-worker.toml")
    for operation in (lambda: workflows.wire_project(dotbrain_home=home, repo=repo),
                      lambda: workflows.refresh_projects(home, cwd=repo)):
        result = operation()
        assert not result.errors and result.logs == []
    repeated = link(delivery)
    assert repeated.linked == repeated.pruned == repeated.warnings == []
    before = snapshot(tmp_path)
    report = doctor.run_doctor(home, home=tmp_path / "user", cwd=repo)
    assert not [f for f in report.projects["sample"] if f.status == "error"]
    assert snapshot(tmp_path) == before
    exclude = adopter_repos.git_exclude_file(repo)
    assert "/.agents/skills/discovery-test" in exclude.read_text().splitlines()
    assert "/.agents" not in exclude.read_text().splitlines()
    assert not workflows.unwire_project(dotbrain_home=home, repo=repo).errors
    assert not entry.is_symlink()
    assert config.read_text() == 'personality = "pragmatic"\n'
    assert user_agent.read_text() == 'name = "mine"\n'
    assert "/.agents/skills/discovery-test" not in exclude.read_text().splitlines()


@pytest.mark.parametrize("operation", ["wire", "refresh", "skills-link"])
def test_owned_legacy_links_migrate_and_prune_stale(delivery, operation):
    home, _, repo = delivery
    old = legacy_link(delivery)
    stale = legacy_link(delivery, "stale")
    cached = home / ".cache/skills/retired/SKILL.md"
    cached.parent.mkdir(parents=True)
    cached.write_text("preserve until migration succeeds", encoding="utf-8")
    retired = legacy_link(delivery, "retired", ".cache/skills/retired")
    adopter_repos.reconcile_link_excludes(repo, linked=[".codex/skills/discovery-test", ".codex/skills/stale", ".codex/skills/retired"])
    if operation == "wire":
        result = workflows.wire_project(dotbrain_home=home, repo=repo)
        assert not result.errors
    elif operation == "refresh":
        result = workflows.refresh_projects(home, cwd=repo)
        assert not result.errors
    else:
        result = link(delivery)
        assert not result.warnings
    new = repo / ".agents/skills/discovery-test"
    assert new.is_symlink() and new.resolve() == (home / "skills/misc/discovery-test").resolve()
    assert all(not entry.is_symlink() for entry in (old, stale, retired))
    excludes = adopter_repos.git_exclude_file(repo).read_text().splitlines()
    assert "/.agents/skills/discovery-test" in excludes
    assert not any(line.startswith("/.codex/skills/") for line in excludes)
    again = link(delivery)
    assert not again.warnings and again.linked == again.pruned == []


@pytest.mark.parametrize("kind", ["file", "directory", "foreign-link", "dangling-link", "loop"])
def test_mixed_legacy_ownership_preserved_and_reported(delivery, tmp_path, kind):
    _, _, repo = delivery
    old = legacy_link(delivery)
    foreign = old.parent / "mine"
    if kind == "file":
        foreign.write_text("keep", encoding="utf-8")
    elif kind == "directory":
        foreign.mkdir()
        (foreign / "SKILL.md").write_text("keep", encoding="utf-8")
    else:
        outside = tmp_path / "outside"
        if kind == "foreign-link":
            outside.mkdir()
        foreign.symlink_to("mine" if kind == "loop" else outside, target_is_directory=True)
    before = snapshot(repo / ".codex")
    result = link(delivery)
    assert not old.is_symlink()
    assert any(str(foreign) in warning and "ambiguous" in warning for warning in result.warnings)
    after = snapshot(repo / ".codex")
    # Directory timestamps change when the owned sibling is removed; foreign resources do not.
    assert {k: v for k, v in after.items() if k.startswith("skills/mine")} == {
        k: v for k, v in before.items() if k.startswith("skills/mine")}
    again = link(delivery)
    assert again.linked == again.pruned == [] and again.warnings == result.warnings


@pytest.mark.parametrize("kind", ["file", "directory", "foreign-link", "dangling-link"])
def test_destination_collision_retains_legacy_until_resolved(delivery, tmp_path, kind):
    home, _, repo = delivery
    old = legacy_link(delivery)
    new = repo / ".agents/skills/discovery-test"
    new.parent.mkdir(parents=True)
    if kind == "file":
        new.write_text("keep", encoding="utf-8")
    elif kind == "directory":
        new.mkdir()
        (new / "SKILL.md").write_text("keep", encoding="utf-8")
    else:
        outside = tmp_path / "outside"
        if kind == "foreign-link":
            outside.mkdir()
        new.symlink_to(outside, target_is_directory=True)
    before = snapshot(repo)
    for _ in range(2):
        result = link(delivery)
        assert result.warnings and result.linked == result.pruned == []
        assert old.is_symlink()
        assert snapshot(repo) == before
    if new.is_dir() and not new.is_symlink():
        (new / "SKILL.md").unlink()
        new.rmdir()
    else:
        new.unlink()
    assert not link(delivery).warnings
    assert new.resolve() == (home / "skills/misc/discovery-test").resolve()
    assert not old.is_symlink()


@pytest.mark.parametrize("receiver", [".agents", ".agents/skills", ".codex/skills"])
def test_foreign_receivers_preserved_and_reported(delivery, tmp_path, receiver):
    _, _, repo = delivery
    legacy_link(delivery)
    entry = repo / receiver
    if receiver == ".codex/skills":
        (entry / "discovery-test").unlink()
        entry.rmdir()
    else:
        entry.parent.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "foreign"
    outside.mkdir()
    (outside / "mine").write_text("keep", encoding="utf-8")
    entry.symlink_to(outside, target_is_directory=True)
    before = snapshot(tmp_path)
    if receiver == ".codex/skills":
        result = link(delivery)
        assert any(str(entry) in warning for warning in result.warnings)
        assert snapshot(outside)["mine"] == before["foreign/mine"]
    else:
        with pytest.raises(ValueError, match="foreign asset directory"):
            link(delivery)
        assert snapshot(tmp_path) == before
    assert entry.is_symlink()


def test_failed_migration_retains_legacy_and_cache_then_recovers(delivery, monkeypatch):
    home, _, repo = delivery
    old = legacy_link(delivery)
    cached = home / ".cache/skills/retired/SKILL.md"
    cached.parent.mkdir(parents=True)
    cached.write_text("keep", encoding="utf-8")
    original = Path.symlink_to
    def fail(self, target, target_is_directory=False):
        if self.parent == repo / ".agents/skills":
            raise OSError("injected delivery failure")
        return original(self, target, target_is_directory=target_is_directory)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "symlink_to", fail)
        with pytest.raises(OSError, match="injected delivery failure"):
            link(delivery)
    assert old.is_symlink() and old.resolve() == (home / "skills/misc/discovery-test").resolve()
    assert cached.read_text() == "keep"
    assert not (repo / ".agents/skills/discovery-test").is_symlink()
    assert not link(delivery).warnings and not old.is_symlink()


@pytest.mark.parametrize("agents", ["claude, codex", "codex, claude"])
def test_multi_runtime_collision_preserves_cached_legacy_content(delivery, agents):
    home, brainspace, repo = delivery
    (brainspace / ".brain/project.yaml").write_text(
        f"agents: [{agents}]\nskills: [misc/discovery-test]\n", encoding="utf-8")
    cached = home / ".cache/skills/discovery-test/SKILL.md"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"legacy skill content\n")
    old = legacy_link(delivery, source=".cache/skills/discovery-test")
    destination = repo / ".agents/skills/discovery-test"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"foreign collision\n")
    target = projects.ProjectTarget("sample", brainspace, repo)
    for _ in range(2):
        result = assets.link_project(home, target, "skills")
        assert result.warnings
        assert old.is_symlink() and (old / "SKILL.md").read_bytes() == b"legacy skill content\n"
        assert cached.read_bytes() == b"legacy skill content\n"
        assert destination.read_bytes() == b"foreign collision\n"
    # A runtime-specific refresh cannot own shared cache retirement either.
    assets.link_project(home, target, "skills", "claude")
    assert (old / "SKILL.md").read_bytes() == b"legacy skill content\n"
    destination.unlink()
    assert not assets.link_project(home, target, "skills").warnings
    assert not old.is_symlink()
    assert destination.resolve() == (home / "skills/misc/discovery-test").resolve()
    again = assets.link_project(home, target, "skills")
    assert again.linked == again.pruned == again.warnings == []


@pytest.mark.parametrize("failed_receiver", [".claude/skills", ".agents/skills"])
def test_multi_runtime_failure_preserves_cached_legacy_content(delivery, monkeypatch, failed_receiver):
    home, brainspace, repo = delivery
    (brainspace / ".brain/project.yaml").write_text(
        "agents: [claude, codex]\nskills: [misc/discovery-test]\n", encoding="utf-8")
    cached = home / ".cache/skills/discovery-test/SKILL.md"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(b"legacy skill content\n")
    old = legacy_link(delivery, source=".cache/skills/discovery-test")
    target = projects.ProjectTarget("sample", brainspace, repo)
    original = Path.symlink_to
    def fail(self, destination, target_is_directory=False):
        if self.parent == repo / failed_receiver:
            raise OSError("injected multi-runtime delivery failure")
        return original(self, destination, target_is_directory=target_is_directory)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "symlink_to", fail)
        with pytest.raises(OSError, match="injected multi-runtime delivery failure"):
            assets.link_project(home, target, "skills")
    assert old.is_symlink() and (old / "SKILL.md").read_bytes() == b"legacy skill content\n"
    assert cached.read_bytes() == b"legacy skill content\n"
    assert not assets.link_project(home, target, "skills").warnings
    assert not old.is_symlink()
    again = assets.link_project(home, target, "skills")
    assert again.linked == again.pruned == again.warnings == []


def test_failed_owned_replacement_preserves_both_links(delivery, monkeypatch):
    home, _, repo = delivery
    old = legacy_link(delivery)
    new = repo / ".agents/skills/discovery-test"
    new.parent.mkdir(parents=True)
    previous = home / "skills/previous"
    previous.mkdir()
    (previous / "SKILL.md").write_text("previous", encoding="utf-8")
    new.symlink_to(previous, target_is_directory=True)
    before = os.readlink(new)
    with monkeypatch.context() as patch:
        patch.setattr(skills.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("injected replacement failure")))
        with pytest.raises(OSError, match="injected replacement failure"):
            link(delivery)
    assert os.readlink(new) == before and old.is_symlink()
    assert sorted(p.name for p in new.parent.iterdir()) == ["discovery-test"]
    assert not link(delivery).warnings and not old.is_symlink()


@pytest.mark.parametrize("command", [["wire"], ["refresh"], ["skills", "link"], ["unwire"]])
def test_unsupported_lifecycle_dry_runs_reject_without_mutation(delivery, tmp_path, command):
    home, _, repo = delivery
    legacy_link(delivery)
    before = snapshot(tmp_path)
    selector = ["--project", "sample"] if command == ["refresh"] else ["--repo", str(repo)]
    result = CliRunner().invoke(app, [*command, *selector, "--home", str(home), "--dry-run", "--json"])
    assert result.exit_code == 2 and "--dry-run" in result.output
    assert snapshot(tmp_path) == before


def test_supported_tracker_dry_run_preserves_all_wiring(delivery, tmp_path, monkeypatch):
    home, brainspace, repo = delivery
    legacy_link(delivery)
    assert not link(delivery).warnings
    (brainspace / ".brain/project.yaml").write_text(
        "agents: [codex]\nskills: [misc/discovery-test]\nbeads: {mode: embedded}\n", encoding="utf-8")
    monkeypatch.setattr(beads, "ensure_embedded_beads", lambda *a, **k: pytest.fail("dry run wrote tracker state"))
    before = snapshot(tmp_path)
    result = CliRunner().invoke(app, ["beads", "sync", "--project", "sample", "--home", str(home), "--dry-run", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["targets"][0]["project"] == "sample"
    assert snapshot(tmp_path) == before
    assert (repo / ".brain").is_symlink() and (repo / ".agents/skills/discovery-test").is_symlink()


def test_global_homes_and_runtime_workspaces_unchanged():
    codex = runtimes.find("codex")
    assert codex.workspace == ".codex" and codex.skill_path == ".agents/skills"
    assert runtimes.global_targets("skills")["codex"] == "~/.codex/skills"
    assert runtimes.global_targets("agents")["codex"] == "~/.codex/agents"
    assert all(rt.skill_path == f"{rt.workspace}/skills" for rt in runtimes.RUNTIMES.values() if rt.name != "codex")


def test_migration_and_unwire_retain_sibling_excludes(delivery, tmp_path):
    home, brainspace, main = delivery
    sibling = tmp_path / "sibling"
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-b", "sibling", str(sibling)],
                   check=True, capture_output=True)
    (sibling / ".brain").symlink_to(brainspace / ".brain", target_is_directory=True)
    for checkout in (main, sibling):
        legacy_link((home, brainspace, checkout))
        adopter_repos.reconcile_link_excludes(checkout, linked=[".codex/skills/discovery-test"])
    assert not link(delivery).warnings
    exclude = adopter_repos.git_exclude_file(main)
    assert "/.codex/skills/discovery-test" in exclude.read_text().splitlines()
    assert not link((home, brainspace, sibling)).warnings
    assert "/.codex/skills/discovery-test" not in exclude.read_text().splitlines()
    assert not workflows.unwire_project(dotbrain_home=home, repo=main).errors
    assert "/.agents/skills/discovery-test" in exclude.read_text().splitlines()
    assert (sibling / ".agents/skills/discovery-test").is_symlink()
    assert not workflows.unwire_project(dotbrain_home=home, repo=sibling).errors
    assert "/.agents/skills/discovery-test" not in exclude.read_text().splitlines()


def test_unwire_preserves_foreign_resources_in_shared_skill_directory(delivery, tmp_path):
    home, _, repo = delivery
    old = legacy_link(delivery)
    assert not link(delivery).warnings and not old.is_symlink()
    shared = repo / ".agents/skills"
    mine = shared / "mine"
    mine.mkdir()
    (mine / "SKILL.md").write_text("keep", encoding="utf-8")
    # A nested project-owned resource is not a delivery link, even if it references our sources.
    (mine / "reference").symlink_to(home / "skills/misc/discovery-test", target_is_directory=True)
    (repo / ".agents/config-reference").symlink_to(home / "skills", target_is_directory=True)
    (shared / "foreign").symlink_to(tmp_path / "missing", target_is_directory=True)
    (shared / "loop").symlink_to("loop", target_is_directory=True)
    before = snapshot(mine)
    assert not workflows.unwire_project(dotbrain_home=home, repo=repo).errors
    assert snapshot(mine) == before and (shared / "foreign").is_symlink()
    assert (shared / "loop").is_symlink()
    assert (repo / ".agents/config-reference").is_symlink()
    assert not (shared / "discovery-test").is_symlink()


def test_existing_replacement_and_mixed_collision_cleanup_independently(delivery):
    home, brainspace, repo = delivery
    old = legacy_link(delivery)
    other = legacy_link(delivery, "other")
    new = repo / ".agents/skills/discovery-test"
    new.parent.mkdir(parents=True)
    new.symlink_to(home / "skills/misc/discovery-test", target_is_directory=True)
    (new.parent / "other").write_text("keep", encoding="utf-8")
    source = home / "skills/other"
    source.mkdir()
    (source / "SKILL.md").write_text("other", encoding="utf-8")
    (brainspace / ".brain/project.yaml").write_text(
        "agents: [codex]\nskills: [misc/discovery-test, other]\nbeads: {mode: none}\n", encoding="utf-8")
    result = link(delivery)
    assert result.warnings and result.pruned == [".codex/skills/discovery-test"]
    assert not old.is_symlink() and other.is_symlink()
    assert (new.parent / "other").read_text() == "keep"
    assert link(delivery).pruned == []


def test_invalid_selection_preserves_legacy_and_cache_without_creating_destination(delivery, tmp_path):
    home, brainspace, repo = delivery
    legacy_link(delivery)
    cache = home / ".cache/skills/cached/SKILL.md"
    cache.parent.mkdir(parents=True)
    cache.write_text("keep", encoding="utf-8")
    (brainspace / ".brain/project.yaml").write_text(
        "agents: [codex]\nskills: [misc/discovery-test, missing]\nbeads: {mode: none}\n", encoding="utf-8")
    before = snapshot(tmp_path)
    result = link(delivery)
    assert result.warnings == ["skill not found: missing"]
    assert result.linked == result.pruned == []
    assert snapshot(tmp_path) == before and not (repo / ".agents").exists()


def test_escaping_cache_rejects_before_legacy_pruning(delivery, tmp_path):
    home, _, repo = delivery
    old = legacy_link(delivery, "stale")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("keep", encoding="utf-8")
    cache = home / ".cache/skills"
    cache.parent.mkdir()
    cache.symlink_to(outside, target_is_directory=True)
    before = snapshot(tmp_path)
    result = link(delivery)
    assert result.warnings and "escapes" in result.warnings[0]
    assert result.linked == result.pruned == [] and old.is_symlink()
    assert snapshot(tmp_path) == before and not (repo / ".agents").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction preservation")
@pytest.mark.parametrize("relative", [".agents", ".agents/skills", ".codex/skills"])
def test_junction_receivers_are_preserved_during_delivery_and_unwire(delivery, tmp_path, relative, monkeypatch):
    # Python 3.11 has reparse metadata but no Path.is_junction().
    monkeypatch.delattr(Path, "is_junction", raising=False)
    home, _, repo = delivery
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "mine").symlink_to(home / "skills/misc/discovery-test", target_is_directory=True)
    receiver = repo / relative
    receiver.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(receiver), str(outside)], check=True, capture_output=True)
    before = snapshot(outside)
    if relative == ".codex/skills":
        assert any(str(receiver) in warning for warning in link(delivery).warnings)
    else:
        with pytest.raises(ValueError, match="foreign asset directory"):
            link(delivery)
    assert not workflows.unwire_project(dotbrain_home=home, repo=repo).errors
    assert receiver.lstat().st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    assert snapshot(outside) == before


@pytest.mark.skipif(os.name != "nt", reason="Windows junction preservation")
@pytest.mark.parametrize("relative", [".codex", ".codex/agents"])
def test_unwire_preserves_marked_agents_behind_foreign_junctions(delivery, tmp_path, relative, monkeypatch):
    monkeypatch.delattr(Path, "is_junction", raising=False)
    home, _, repo = delivery
    outside = tmp_path / "outside"
    outside.mkdir()
    marked = outside / ("agents/dotbrain-worker.toml" if relative == ".codex" else "dotbrain-worker.toml")
    marked.parent.mkdir(parents=True, exist_ok=True)
    marked.write_text(subagents.GENERATED_NOTICE + "\n" + subagents.MANAGED_MARKER + '\nname = "worker"\n', encoding="utf-8")
    assert subagents.is_managed_copy(marked)
    receiver = repo / relative
    receiver.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(receiver), str(outside)], check=True, capture_output=True)
    before = snapshot(outside)
    assert not workflows.unwire_project(dotbrain_home=home, repo=repo).errors
    assert receiver.lstat().st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT
    assert snapshot(outside) == before
