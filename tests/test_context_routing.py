"""Context authority, private rule preservation, and bounded retrieval contracts."""
from pathlib import Path
import json
import subprocess
import tomllib

import pytest
from typer.testing import CliRunner

from dotbrain import adopter_repos, brainspaces, doctor, hooks, paths, resource_loader, subagents, workflows
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


@pytest.mark.parametrize("command", ["wire", "refresh"])
@pytest.mark.parametrize("worktree", [False, True])
def test_existing_pointer_survives_wire_and_refresh(tmp_path, monkeypatch, command, worktree):
    home, brainspace, repo = _project(tmp_path)
    brainspaces.seed_brain(brainspace, home)
    if worktree:
        adopter_repos.wire_repo(repo, brainspace, home, skip_beads_link=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                        "commit", "--allow-empty", "-qm", "initial"], cwd=repo, check=True)
        checkout = tmp_path / "worktree"
        subprocess.run(["git", "worktree", "add", "-qb", "fixture", str(checkout)], cwd=repo, check=True)
        repo = checkout
    for name in ("AGENTS.md", "CLAUDE.md"):
        (repo / name).write_text(f"Keep {name}\n{paths.ADOPTER_POINTER}\n", encoding="utf-8")
    if command == "refresh":
        adopter_repos.reconcile(repo, {".brain": brainspace / ".brain"})
    monkeypatch.chdir(repo)
    args = [command, "--repo", str(repo), "--project", "example", "--skip-beads"] if command == "wire" else [command]
    for attempt in range(2):
        result = CliRunner().invoke(app, [*args, "--home", str(home), "--json"])
        assert result.exit_code == 0, result.output
        target = json.loads(result.output)["targets"][0]
        if command == "wire":
            reported = [f["message"] for f in target["findings"] if f["severity"] == "warning"]
        else:
            reported = target["data"]["checkout_changes"]
        assert not [message for message in reported if "AGENTS.md" in message or "CLAUDE.md" in message]
        assert not target["errors"]
        for name in ("AGENTS.md", "CLAUDE.md"):
            assert (repo / name).read_text(encoding="utf-8") == f"Keep {name}\n{paths.ADOPTER_POINTER}\n"


@pytest.mark.parametrize("linked", [False, True])
def test_wire_refresh_unwire_preserve_private_content_and_user_context(tmp_path, linked):
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
def test_refresh_preserves_context_pointers_and_symlinks(tmp_path, newline):
    home, brainspace, repo = _project(tmp_path)
    brainspaces.seed_brain(brainspace, home)
    pointer = paths.ADOPTER_POINTER.encode().replace(b"\n", newline)
    before = b"  Keep whitespace  " + newline
    after = newline + b"Unrelated instructions" + newline
    (repo / "AGENTS.md").write_bytes(before + pointer + newline + after)
    foreign = tmp_path / "foreign.md"
    foreign.write_bytes(pointer + newline)
    (repo / "CLAUDE.md").symlink_to(foreign)
    for _ in range(2):
        _refresh(home)
        assert (repo / "AGENTS.md").read_bytes() == before + pointer + newline + after
        assert (repo / "CLAUDE.md").is_symlink()
        assert foreign.read_bytes() == pointer + newline
    # A partial or quoted block cannot be attributed to Dotbrain.
    unmanaged = b"> " + pointer + newline
    (repo / "AGENTS.md").write_bytes(unmanaged)
    _refresh(home)
    assert (repo / "AGENTS.md").read_bytes() == unmanaged


def test_brain_only_private_entries_remain_untouched(tmp_path):
    home, brainspace, _ = _project(tmp_path)
    (brainspace / ".repo").write_text("(brain-only)\n", encoding="utf-8")
    brain = brainspace / ".brain"
    (brain / "AGENTS.md").write_bytes(b"Private policy\n")
    (brain / "CLAUDE.md").symlink_to("AGENTS.md")
    for _ in range(2):
        _refresh(home)
        assert (brain / "AGENTS.md").read_bytes() == b"Private policy\n"
        assert (brain / "CLAUDE.md").is_symlink()


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_unwire_removes_only_complete_pointer_without_rewriting_user_bytes(tmp_path, newline):
    home, brainspace, repo = _project(tmp_path)
    adopter_repos.wire_repo(repo, brainspace, home, skip_beads_link=True)
    pointer = paths.ADOPTER_POINTER.encode().replace(b"\n", newline)
    before = b"  User whitespace  " + newline
    after = newline + b"> " + pointer + newline
    (repo / "AGENTS.md").write_bytes(before + pointer + newline + after)
    result = adopter_repos.unwire_repo(repo, dotbrain_home=home)
    assert (repo / "AGENTS.md").read_bytes() == before + after
    assert not result.warnings


def test_unwire_warns_about_a_partial_pointer_it_leaves(tmp_path):
    home, brainspace, repo = _project(tmp_path)
    adopter_repos.wire_repo(repo, brainspace, home, skip_beads_link=True)
    edited = paths.ADOPTER_POINTER.splitlines()[0] + "\nMy own note about the Brain\n"
    (repo / "AGENTS.md").write_text(edited, encoding="utf-8")
    result = adopter_repos.unwire_repo(repo, dotbrain_home=home)
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == edited
    assert [w for w in result.warnings if "AGENTS.md" in w and "@.brain/CLAUDE.md" in w]


def test_doctor_does_not_warn_that_private_entries_are_legacy(tmp_path):
    home, brainspace, repo = _project(tmp_path)
    brainspaces.seed_brain(brainspace, home)
    adopter_repos.wire_repo(repo, brainspace, home, skip_beads_link=True)
    report = doctor.run_doctor(home, project="example", home=tmp_path / "user")
    findings = report.machine + report.projects["example"]
    assert not [f.message for f in findings if f.status == "error"]
    assert not [f.message for f in findings if f.status == "warning" and "AGENTS.md" in f.message]


def test_bundled_consumers_keep_private_rules_and_selective_retro_retrieval():
    convention = resource_loader.resource("templates/brain/DOTBRAIN.md").read_text(encoding="utf-8")
    assert "Read `.brain/AGENTS.md` before substantial work" in convention
    assert "the lead or sole agent searches `.brain/RETRO.md`" in convention
    assert "Workers and reviewers reuse supplied findings" in convention
    assert "missing notebook blocks nothing" in convention
    template = resource_loader.resource("templates/brain/AGENTS.md").read_text(encoding="utf-8")
    assert "personal preferences" in template
    assert "public root `RULES.md`" in template
    for role in ("worker", "researcher"):
        claude = subagents.packaged_body(role, "claude-code")
        codex = tomllib.loads(subagents.packaged_body(role, "codex"))["developer_instructions"]
        for consumer in (claude, codex):
            assert "`RULES.md` (when present)" in consumer
            assert "`AGENTS.md`" in consumer
            assert "private rules/preferences" in consumer
            assert "do not read the whole notebook" in consumer
    promotion = Path("plugin/skills/run-retro/references/promotion.md").read_text(encoding="utf-8")
    assert "Personal preferences stay in `.brain/AGENTS.md`" in promotion
