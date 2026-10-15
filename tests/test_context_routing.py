"""Context authority, legacy preservation, and bounded retrieval contracts."""
from pathlib import Path
import subprocess
import tomllib

import pytest
from typer.testing import CliRunner

from dotbrain import adopter_repos, brainspaces, doctor, hooks, paths, resource_loader, workflows
from dotbrain.cli import app


def _project(tmp_path):
    home = tmp_path / "home"
    brainspace = home / "brainspaces" / "example"
    brain = brainspace / ".brain"
    brain.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=home, check=True)
    (brain / "project.yaml").write_text("agents: []\nskills: []\nbeads: {mode: none}\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (brainspace / ".repo").write_text(str(repo), encoding="utf-8")
    return home, brainspace, repo


def _refresh(home):
    result = CliRunner().invoke(app, ["refresh", "--project", "example", "--home", str(home), "--json"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("linked", [False, True])
def test_wire_refresh_unwire_preserve_legacy_content_and_user_context(tmp_path, linked):
    home, brainspace, repo = _project(tmp_path)
    brain = brainspace / ".brain"
    outside = tmp_path / "foreign-instructions.md"
    outside.write_bytes(b"Foreign rules\r\n")
    (brain / "AGENTS.md").write_bytes(b"Unfamiliar private policy\r\n")
    if linked:
        (brain / "CLAUDE.md").symlink_to(outside)
    else:
        (brain / "CLAUDE.md").write_bytes(b"Distinct legacy instructions\r\n")
    (repo / "CLAUDE.md").symlink_to(outside)
    (repo / "AGENTS.md").write_bytes(b"Keep these instructions\r\n")
    (repo / "RULES.md").write_bytes(b"Repository rules\r\n")
    (brain / "RETRO.md").write_bytes(b"Private finding canary\r\n" * 10000)
    preserved = [brain / "AGENTS.md", brain / "CLAUDE.md", brain / "RETRO.md",
                 repo / "AGENTS.md", repo / "RULES.md", outside]
    before = {p: p.read_bytes() for p in preserved}
    result = workflows.wire_project(dotbrain_home=home, repo=repo, project="example", run_beads=False)
    assert not result.errors
    for _ in range(2):
        _refresh(home)
        assert {p: p.read_bytes() for p in preserved} == before
        assert (repo / "CLAUDE.md").is_symlink()
        assert (brain / "CLAUDE.md").is_symlink() == linked
    payload = hooks.brain_context(cwd=repo)
    assert len(payload) < hooks.PAYLOAD_LIMIT
    assert b"Private finding canary" not in payload
    assert b"Unfamiliar private policy" not in payload
    result = adopter_repos.unwire_repo(repo, dotbrain_home=home)
    assert not result.errors
    assert not (repo / ".brain").exists()
    assert (repo / "CLAUDE.md").is_symlink()
    assert {p: p.read_bytes() for p in preserved} == before


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_refresh_removes_only_complete_managed_pointer_and_preserves_symlinks(tmp_path, newline):
    home, brainspace, repo = _project(tmp_path)
    brainspaces.seed_brain(brainspace, home)
    pointer = paths.LEGACY_ADOPTER_POINTER.encode().replace(b"\n", newline)
    before = b"  Keep whitespace  " + newline
    after = newline + b"Unrelated instructions" + newline
    (repo / "AGENTS.md").write_bytes(before + pointer + newline + after)
    foreign = tmp_path / "foreign.md"
    foreign.write_bytes(pointer + newline)
    (repo / "CLAUDE.md").symlink_to(foreign)
    for _ in range(2):
        _refresh(home)
        assert (repo / "AGENTS.md").read_bytes() == before + after
        assert (repo / "CLAUDE.md").is_symlink()
        assert foreign.read_bytes() == pointer + newline
    # A partial or quoted block cannot be attributed to Dotbrain.
    unmanaged = b"> " + pointer + newline
    (repo / "AGENTS.md").write_bytes(unmanaged)
    _refresh(home)
    assert (repo / "AGENTS.md").read_bytes() == unmanaged


@pytest.mark.parametrize("linked", [False, True])
def test_accounted_legacy_content_survives_explicit_removal_and_repeat_refresh(tmp_path, linked):
    home, brainspace, repo = _project(tmp_path)
    brain = brainspace / ".brain"
    brainspaces.seed_brain(brainspace, home)
    source = b"Fixture domain term: widget\n"
    (brain / "AGENTS.md").write_bytes(source)
    if linked:
        (brain / "CLAUDE.md").symlink_to("AGENTS.md")
    else:
        (brain / "CLAUDE.md").write_bytes(b"Fixture supporting explanation\n")
    # Exercise the explicit curation procedure: retain source evidence, classify
    # content, and verify destinations before removing the inventoried entries.
    snapshot = {name: (brain / name).read_bytes() for name in ("AGENTS.md", "CLAUDE.md")}
    archive = brain / "docs" / "legacy-entry-snapshot.md"
    archive.write_bytes(b"\n".join(snapshot.values()))
    (brain / "CONTEXT.md").write_bytes(source)
    if not linked:
        (brain / "docs" / "reference.md").write_bytes(snapshot["CLAUDE.md"])
    assert all(content in archive.read_bytes() for content in snapshot.values())
    assert (brain / "CONTEXT.md").read_bytes() == snapshot["AGENTS.md"]
    (brain / "CLAUDE.md").unlink()
    (brain / "AGENTS.md").unlink()
    public = "When making or reviewing changes, read root `RULES.md`.\n"
    (repo / "AGENTS.md").write_text(public, encoding="utf-8")
    (repo / "RULES.md").write_text("Check the relevant behavior before committing.\n", encoding="utf-8")
    for _ in range(2):
        _refresh(home)
        for name in ("AGENTS.md", "CLAUDE.md", "RETRO.md"):
            assert not (brain / name).exists()
            assert not (brain / name).is_symlink()
        assert (brain / "CONTEXT.md").read_bytes() == source
        assert all(content in archive.read_bytes() for content in snapshot.values())
    adopter_repos.unwire_repo(repo, dotbrain_home=home)
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == public
    assert (repo / "RULES.md").is_file()


def test_brain_only_legacy_entries_remain_untouched(tmp_path):
    home, brainspace, _ = _project(tmp_path)
    (brainspace / ".repo").write_text("(brain-only)\n", encoding="utf-8")
    brain = brainspace / ".brain"
    (brain / "AGENTS.md").write_bytes(b"Private policy\n")
    (brain / "CLAUDE.md").symlink_to("AGENTS.md")
    for _ in range(2):
        _refresh(home)
        assert (brain / "AGENTS.md").read_bytes() == b"Private policy\n"
        assert (brain / "CLAUDE.md").is_symlink()


@pytest.mark.parametrize("dangling", [False, True])
def test_seed_and_refresh_never_follow_retired_entry_symlinks(tmp_path, dangling):
    home, brainspace, _ = _project(tmp_path)
    brain = brainspace / ".brain"
    foreign = tmp_path / "external-context.md"
    if not dangling:
        foreign.write_bytes(b"External private context\r\n")
    for name in ("AGENTS.md", "CLAUDE.md"):
        (brain / name).symlink_to(foreign)
    brainspaces.seed_brain(brainspace, home)
    _refresh(home)
    for name in ("AGENTS.md", "CLAUDE.md"):
        assert (brain / name).is_symlink()
        assert (brain / name).resolve() == foreign.resolve()
    if dangling:
        assert not foreign.exists()
    else:
        assert foreign.read_bytes() == b"External private context\r\n"


def test_doctor_does_not_require_private_entries(tmp_path):
    home, brainspace, repo = _project(tmp_path)
    brainspaces.seed_brain(brainspace, home)
    adopter_repos.wire_repo(repo, brainspace, home, skip_beads_link=True)
    report = doctor.run_doctor(home, project="example", home=tmp_path / "user")
    findings = report.machine + report.projects["example"]
    assert not [f.message for f in findings if f.status == "error"]
    assert not [f.message for f in findings if "AGENTS.md" in f.message or "CLAUDE.md" in f.message]


def test_bundled_retrieval_consumers_retire_required_private_entry_reads():
    convention = resource_loader.resource("templates/brain/DOTBRAIN.md").read_text(encoding="utf-8")
    assert "the lead or sole agent searches `.brain/RETRO.md`" in convention
    assert "Workers and reviewers reuse supplied findings" in convention
    assert "missing notebook blocks nothing" in convention
    assert not resource_loader.resource("templates/brain/AGENTS.md").is_file()
    for role in ("worker", "researcher"):
        claude = Path(f"plugin/agents/{role}.md").read_text(encoding="utf-8")
        codex = tomllib.loads(resource_loader.resource(f"agents/codex/{role}.toml").read_text(encoding="utf-8"))["developer_instructions"]
        for consumer in (claude, codex):
            assert "RULES.md" in consumer
            assert "do not read the whole notebook" in consumer
            assert "Brain's `AGENTS.md`" not in consumer
    # Migration inventories may name retired entries; runtime consumers may not.
    for path in Path("plugin/skills").rglob("*.md"):
        if path.parent.name == "curate-project-context":
            continue
        text = path.read_text(encoding="utf-8")
        assert ".brain/AGENTS.md" not in text, path
        assert ".brain/CLAUDE.md" not in text, path
