"""Tests for the pure path/contract helpers."""

from __future__ import annotations

from pathlib import Path

from dotbrain import paths


def test_contract_constants_stay_in_lockstep():
    assert paths.BRAINSPACE_LINKS == (".brain", ".beads", ".claude", ".codex")
    assert paths.EXCLUDE_ENTRIES == ("/.brain", "/.beads", "/.claude", "/.codex")
    # Every Brainspace link has a matching anchored exclude entry, in order.
    assert tuple(f"/{link}" for link in paths.BRAINSPACE_LINKS) == paths.EXCLUDE_ENTRIES
    assert paths.ADOPTER_POINTER.startswith("@.brain/CLAUDE.md")


def test_brainspace_and_control_link_targets(dotbrain_root: Path):
    assert paths.brainspace(dotbrain_root, "example") == dotbrain_root / "projects" / "example"
    targets = paths.control_link_targets(dotbrain_root, "example")
    assert set(targets) == set(paths.BRAINSPACE_LINKS)
    assert targets[".brain"] == dotbrain_root / "projects" / "example" / ".brain"


def test_disconnected_repo_is_not_wired(disconnected_adopter_repo: Path):
    assert paths.is_wired(disconnected_adopter_repo) is False
    assert not (paths.EXCLUDE_ENTRIES[0] in paths.exclude_entries(disconnected_adopter_repo))


def test_repo_is_wired_after_control_link_symlinks_created(
    disconnected_adopter_repo: Path, brainspace: Path
):
    # Model what the wire port will automate: link each Brainspace link into the Brainspace.
    for link in paths.BRAINSPACE_LINKS:
        (disconnected_adopter_repo / link).symlink_to(brainspace / link)
    assert paths.is_wired(disconnected_adopter_repo) is True
