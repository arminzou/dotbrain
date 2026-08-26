"""Tests for brainspaces.py: Brain seeding, workspace preparation, and offboarding helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dotbrain import hooks
from dotbrain import brainspaces, resource_loader


# --------------------------------------------------------------------------- pure helpers


# --------------------------------------------------------------------------- mutators


def test_seed_brain_creates_skeleton(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    brainspaces.seed_brain(brainspace, dotbrain_home)
    brain = brainspace / ".brain"
    assert (brain / "AGENTS.md").is_file()
    assert (brain / "CLAUDE.md").is_symlink()
    assert (brain / "DOTBRAIN.md").is_file()
    assert b"\r\n" not in (brain / "DOTBRAIN.md").read_bytes()
    for sub in ("adr", "designs", "docs"):
        assert (brain / sub).is_dir()
        assert (brain / sub / "README.md").is_file(), \
            f"dotbrain-owned README.md not hydrated to .brain/{sub}/"
    # the agents/ skill-config dir is retired and no longer seeded
    assert not (brain / "agents").exists()


def test_seed_brain_ignores_data_root_templates(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    shutil.rmtree(dotbrain_home / "templates")
    brainspaces.seed_brain(brainspace, dotbrain_home)
    assert (brainspace / ".brain" / "AGENTS.md").is_file()


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


def test_ensure_json_hook_adds_and_dedupes(tmp_path: Path):
    file = tmp_path / "settings.json"
    brainspaces.ensure_json_hook(file, "SessionStart", "do-thing")
    brainspaces.ensure_json_hook(file, "SessionStart", "do-thing")  # idempotent on command
    brainspaces.ensure_json_hook(file, "SessionStart", "other", "startup", "msg")
    data = json.loads(file.read_text())
    entries = data["hooks"]["SessionStart"]
    commands = [h["command"] for e in entries for h in e["hooks"]]
    assert commands == ["do-thing", "other"]
    assert entries[1]["matcher"] == "startup"
    assert entries[1]["hooks"][0]["statusMessage"] == "msg"


def test_seed_agent_workspaces_skips_a_repo_backed_brainspace(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    """A repo-backed Brainspace links from the code repo, so a workspace here would be dead."""

    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    (brainspace / ".repo").write_text("~/repos/projects/thing", encoding="utf-8")

    warnings = brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, fake_home)

    assert warnings == []
    assert not (brainspace / ".claude").exists()
    assert not (brainspace / ".codex").exists()


def test_seed_agent_workspaces_serves_a_brain_only_brainspace(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    """With no repo there is nowhere else for its links to live."""

    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    (brainspace / ".repo").write_text("(brain-only)", encoding="utf-8")

    warnings = brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, fake_home)
    warnings_again = brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, fake_home)

    assert warnings == []
    assert warnings_again == []
    assert (brainspace / ".claude").is_dir()
    assert (brainspace / ".codex").is_dir()
    assert not (brainspace / ".claude" / "settings.json").exists()
    assert not (brainspace / ".codex" / "hooks.json").exists()


def test_seed_agent_workspaces_warns_on_an_unknown_agent(dotbrain_home: Path, fake_home: Path):
    """A typo in project.yaml warns whether or not anything gets created."""

    brainspace = dotbrain_home / "brainspaces" / "claude-only"
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".brain" / "project.yaml").write_text(
        "agents:" + chr(10) + "  - claude" + chr(10) + "  - custom" + chr(10)
    )

    warnings = brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, fake_home)

    assert warnings == [f"ignored unknown agent workspace in {brainspace / '.brain' / 'project.yaml'}: custom"]
    assert not (brainspace / ".claude").exists()


def test_sessionstart_hook_emits_nothing_for_a_repo_without_a_brain(tmp_path: Path):
    """A .beads directory alone must not make the hook speak — beads context is a project hook."""

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    (repo / ".beads").mkdir()

    assert hooks.brain_context(cwd=repo) == b""
