"""Tests for brainspaces.py: Brain seeding, workspace preparation, and offboarding helpers."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

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


def test_seed_agent_workspaces_leaves_session_start_to_plugin(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()
    warnings = brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, fake_home)
    warnings_again = brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, fake_home)
    assert warnings == []
    assert warnings_again == []
    assert (brainspace / ".claude").is_dir()
    assert (brainspace / ".codex").is_dir()
    assert not (brainspace / ".claude" / "settings.json").exists()
    assert not (brainspace / ".codex" / "hooks.json").exists()
    assert not (brainspace / ".codex" / "config.toml").exists()


def test_seed_agent_workspaces_honors_project_agents_and_preserves_existing_unlisted(
    dotbrain_home: Path, fake_home: Path
):
    brainspace = dotbrain_home / "brainspaces" / "claude-only"
    (brainspace / ".brain").mkdir(parents=True)
    (brainspace / ".brain" / "project.yaml").write_text(
        "agents:\n"
        "  - claude\n"
        "  - custom\n"
    )
    existing_codex = brainspace / ".codex" / "keep.txt"
    existing_codex.parent.mkdir(parents=True)
    existing_codex.write_text("keep\n")

    warnings = brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, fake_home)

    assert (brainspace / ".claude").is_dir()
    assert not (brainspace / ".claude" / "settings.json").exists()
    assert not (brainspace / ".codex" / "hooks.json").exists()
    assert existing_codex.read_text() == "keep\n"
    assert warnings == [f"ignored unknown agent workspace in {brainspace / '.brain' / 'project.yaml'}: custom"]


def test_sessionstart_bootstrap_script_does_not_invoke_bd(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    (repo / ".beads").mkdir()

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    bd_log = tmp_path / "bd.log"
    (fake_bin / "bd").write_text(
        "#!/usr/bin/env bash\n"
        f"echo bd >> {bd_log}\n"
        "echo SHOULD_NOT_RUN_BD\n"
    )
    (fake_bin / "dotbrain").write_text("#!/usr/bin/env bash\nexit 0\n")
    (fake_bin / "bd").chmod(0o755)
    (fake_bin / "dotbrain").chmod(0o755)

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    with resource_loader.resource_file("scripts/brain-sessionstart.sh") as script:
        result = subprocess.run(
            [resource_loader.resolve_bash(), str(script)],
            cwd=repo,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    assert result.stdout == ""
    assert result.stderr == ""
    assert not bd_log.exists()
