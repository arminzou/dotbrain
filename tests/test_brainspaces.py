"""Tests for brainspaces.py: Brain seeding, agent-workspace seeding, and offboarding helpers."""

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


def test_ensure_control_gitignore_seeds_and_is_idempotent(tmp_path: Path):
    brainspaces.ensure_control_gitignore(tmp_path)
    lines = (tmp_path / ".gitignore").read_text().splitlines()
    for expected in brainspaces.CONTROL_GITIGNORE_LINES:
        assert expected in lines
    brainspaces.ensure_control_gitignore(tmp_path)
    assert (tmp_path / ".gitignore").read_text().splitlines() == lines


def test_seed_brain_creates_skeleton(dotbrain_root: Path, tmp_path: Path):
    control = tmp_path / "control"
    control.mkdir()
    brainspaces.seed_brain(control, dotbrain_root)
    brain = control / ".brain"
    assert (brain / "AGENTS.md").is_file()
    assert (brain / "CLAUDE.md").is_symlink()
    assert (brain / "DOTBRAIN.md").is_file()
    for sub in ("adr", "prd", "agents", "docs"):
        assert (brain / sub).is_dir()
        assert (brain / sub / "README.md").is_file(), \
            f"dotbrain-owned README.md not hydrated to .brain/{sub}/"
    # domain.md and triage-labels.md are no longer seeded
    assert not (brain / "agents" / "domain.md").exists()
    assert not (brain / "agents" / "triage-labels.md").exists()


def test_seed_brain_ignores_data_root_templates(dotbrain_root: Path, tmp_path: Path):
    control = tmp_path / "control"
    control.mkdir()
    shutil.rmtree(dotbrain_root / "templates")
    brainspaces.seed_brain(control, dotbrain_root)
    assert (control / ".brain" / "AGENTS.md").is_file()


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


def test_ensure_codex_config(tmp_path: Path):
    created = tmp_path / "config.toml"
    assert brainspaces.ensure_codex_config(created) is None
    assert "hooks = true" in created.read_text()

    disabled = tmp_path / "disabled.toml"
    disabled.write_text("[features]\n")
    assert "does not explicitly enable hooks" in brainspaces.ensure_codex_config(disabled)


def test_seed_agent_workspaces_writes_hooks(dotbrain_root: Path, fake_home: Path, tmp_path: Path):
    control = tmp_path / "control"
    control.mkdir()
    warnings = brainspaces.seed_agent_workspaces(control, dotbrain_root, fake_home)
    warnings_again = brainspaces.seed_agent_workspaces(control, dotbrain_root, fake_home)
    assert warnings == []
    assert warnings_again == []
    bootstrap = "dotbrain hook session-start"
    claude = json.loads((control / ".claude" / "settings.json").read_text())
    claude_commands = [h["command"] for e in claude["hooks"]["SessionStart"] for h in e["hooks"]]
    assert claude_commands == [bootstrap]
    codex = json.loads((control / ".codex" / "hooks.json").read_text())
    assert set(codex["hooks"]) == {"SessionStart"}
    codex_commands = [h["command"] for e in codex["hooks"]["SessionStart"] for h in e["hooks"]]
    assert codex_commands == [bootstrap]
    assert "hooks = true" in (control / ".codex" / "config.toml").read_text()


def test_seed_agent_workspaces_honors_project_agents_and_preserves_existing_unlisted(
    dotbrain_root: Path, fake_home: Path
):
    control = dotbrain_root / "projects" / "claude-only"
    control.mkdir(parents=True)
    (control / "project.yaml").write_text(
        "agents:\n"
        "  - claude\n"
        "  - custom\n"
    )
    existing_codex = control / ".codex" / "keep.txt"
    existing_codex.parent.mkdir(parents=True)
    existing_codex.write_text("keep\n")

    warnings = brainspaces.seed_agent_workspaces(control, dotbrain_root, fake_home)

    assert (control / ".claude" / "settings.json").is_file()
    assert not (control / ".codex" / "hooks.json").exists()
    assert existing_codex.read_text() == "keep\n"
    assert warnings == [f"ignored unknown agent workspace in {control / 'project.yaml'}: custom"]


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

    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
    with resource_loader.resource_file("scripts/brain-sessionstart.sh") as script:
        result = subprocess.run(
            ["bash", str(script)],
            cwd=repo,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    assert result.stdout == ""
    assert result.stderr == ""
    assert not bd_log.exists()
