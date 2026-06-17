"""Tests for the pure path/contract helpers."""

from __future__ import annotations

from pathlib import Path

from dotbrain import paths


def test_contract_constants_stay_in_lockstep():
    assert paths.CONTROL_LINKS == (".brain", ".beads", ".claude", ".codex")
    assert paths.EXCLUDE_ENTRIES == ("/.brain", "/.beads", "/.claude", "/.codex")
    # Every control link has a matching anchored exclude entry, in order.
    assert tuple(f"/{link}" for link in paths.CONTROL_LINKS) == paths.EXCLUDE_ENTRIES
    assert paths.ADOPTER_POINTER.startswith("@.brain/CLAUDE.md")


def test_control_root_and_control_link_targets(dotbrain_root: Path):
    assert paths.control_root(dotbrain_root, "example") == dotbrain_root / "projects" / "example"
    targets = paths.control_link_targets(dotbrain_root, "example")
    assert set(targets) == set(paths.CONTROL_LINKS)
    assert targets[".brain"] == dotbrain_root / "projects" / "example" / ".brain"


def test_disconnected_repo_is_not_wired(disconnected_adopter_repo: Path):
    assert paths.is_wired(disconnected_adopter_repo) is False
    assert not (paths.EXCLUDE_ENTRIES[0] in paths.exclude_entries(disconnected_adopter_repo))


def test_repo_is_wired_after_control_link_symlinks_created(
    disconnected_adopter_repo: Path, control_root: Path
):
    # Model what the wire port will automate: link each control link into the control root.
    for link in paths.CONTROL_LINKS:
        (disconnected_adopter_repo / link).symlink_to(control_root / link)
    assert paths.is_wired(disconnected_adopter_repo) is True
