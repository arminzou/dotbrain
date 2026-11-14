"""Tests for brainspaces.py: Brain seeding and workspace preparation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from dotbrain import hooks
from dotbrain import brainspaces, resource_loader


# --------------------------------------------------------------------------- pure helpers


# --------------------------------------------------------------------------- mutators


def test_seed_brain_creates_skeleton(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    brainspaces.seed_brain(brainspace, dotbrain_home)
    brain = brainspace / ".brain"
    assert not (brain / "AGENTS.md").exists()
    assert not (brain / "CLAUDE.md").exists()
    assert (brain / "DOTBRAIN.md").is_file()
    assert b"\r\n" not in (brain / "DOTBRAIN.md").read_bytes()
    for sub in ("adr", "designs", "docs"):
        assert (brain / sub).is_dir()
        assert (brain / sub / "README.md").is_file(), \
            f"dotbrain-owned README.md not synced to .brain/{sub}/"
    # the agents/ skill-config dir is retired and no longer seeded
    assert not (brain / "agents").exists()
    assert not (brain / "site").exists()


@pytest.mark.parametrize("create_missing", [True, False])
def test_seed_brain_preserves_existing_site_files(dotbrain_home: Path, tmp_path: Path, create_missing: bool):
    brainspace = tmp_path / "brainspace"
    brain = brainspace / ".brain"
    (brain / "site").mkdir(parents=True)
    for name in ("configure.md", "index.md", "site.yaml"):
        (brain / "site" / name).write_bytes(f"Existing {name}\r\n".encode())
    before = {path.name: path.read_bytes() for path in (brain / "site").iterdir()}

    changed = brainspaces.seed_brain(brainspace, dotbrain_home, create_missing=create_missing)

    assert {path.name: path.read_bytes() for path in (brain / "site").iterdir()} == before
    assert not any(path.startswith("site/") for path in changed)


def test_seed_brain_ignores_data_root_templates(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    shutil.rmtree(dotbrain_home / "templates")
    brainspaces.seed_brain(brainspace, dotbrain_home)
    assert (brainspace / ".brain" / "DOTBRAIN.md").is_file()


@pytest.mark.parametrize("create_missing", [True, False])
@pytest.mark.parametrize("legacy", ["agents-only", "claude-only", "dangling-alias"])
def test_seed_brain_preserves_incomplete_legacy_entries(
    dotbrain_home: Path, tmp_path: Path, create_missing: bool, legacy: str
):
    brainspace = tmp_path / "brainspace"
    brain = brainspace / ".brain"
    brain.mkdir(parents=True)
    if legacy == "dangling-alias":
        (brain / "CLAUDE.md").symlink_to("AGENTS.md")
    else:
        name = "AGENTS.md" if legacy == "agents-only" else "CLAUDE.md"
        (brain / name).write_bytes(b"User instructions\r\n")

    for _ in range(2):
        changed = brainspaces.seed_brain(brainspace, dotbrain_home, create_missing=create_missing)
        assert not set(changed).intersection({"AGENTS.md", "CLAUDE.md"})
        if legacy == "dangling-alias":
            assert (brain / "CLAUDE.md").readlink() == Path("AGENTS.md")
            assert not (brain / "AGENTS.md").exists()
        else:
            assert (brain / name).read_bytes() == b"User instructions\r\n"
            other = "CLAUDE.md" if name == "AGENTS.md" else "AGENTS.md"
            assert not (brain / other).exists()
            assert not (brain / other).is_symlink()


def test_seed_brain_does_not_rewrite_unchanged_owned_files(
    dotbrain_home: Path, tmp_path: Path
):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    brainspaces.seed_brain(brainspace, dotbrain_home)
    readme = brainspace / ".brain" / "docs" / "README.md"
    original_mtime = readme.stat().st_mtime_ns

    brainspaces.seed_brain(brainspace, dotbrain_home)

    assert readme.stat().st_mtime_ns == original_mtime


def test_seeded_project_omits_agents_and_preserves_existing_lists(dotbrain_home: Path, monkeypatch):
    from dotbrain import config, runtimes

    monkeypatch.setitem(runtimes.RUNTIMES, "newer", runtimes.Runtime("newer", "newer", "Newer", ".newer", default=True))
    monkeypatch.setitem(runtimes.RUNTIMES, "optin", runtimes.Runtime("optin", "optin", "Opt-in", ".optin"))
    fresh = dotbrain_home / "brainspaces" / "fresh"
    brainspaces.seed_brain(fresh, dotbrain_home)
    assert config.load_project_agents(dotbrain_home, "fresh") == ()
    assert "agents" not in yaml.safe_load((fresh / ".brain/project.yaml").read_text(encoding="utf-8"))
    assert yaml.safe_load((fresh / ".brain/project.yaml").read_text(encoding="utf-8")) == {"version": 3}

    existing = dotbrain_home / "brainspaces" / "existing"
    (existing / ".brain").mkdir(parents=True)
    (existing / ".brain" / "project.yaml").write_text("agents: [codex]\n", encoding="utf-8")
    brainspaces.seed_brain(existing, dotbrain_home)
    assert (existing / ".brain" / "project.yaml").read_text(encoding="utf-8") == "agents: [codex]\n"


def test_unknown_agent_warnings_name_a_project_yaml_typo(dotbrain_home: Path):
    """A typo in project.yaml warns and creates nothing in the Brainspace."""

    brainspace = dotbrain_home / "brainspaces" / "claude-only"
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".brain" / "project.yaml").write_text(
        "agents:" + chr(10) + "  - claude" + chr(10) + "  - custom" + chr(10)
    )

    warnings = brainspaces.unknown_agent_warnings(brainspace, dotbrain_home)

    assert warnings == [f"ignored unknown agent workspace in {brainspace / '.brain' / 'project.yaml'}: custom"]
    assert not (brainspace / ".claude").exists()


def test_sessionstart_hook_emits_nothing_for_a_repo_without_a_brain(tmp_path: Path):
    """A .beads directory alone must not make the hook speak — beads context is a project hook."""

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    (repo / ".beads").mkdir()

    assert hooks.brain_context(cwd=repo) == b""
