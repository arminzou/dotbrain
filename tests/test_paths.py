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


def test_brainspace_and_brainspace_link_targets(dotbrain_home: Path):
    assert paths.brainspace(dotbrain_home, "example") == dotbrain_home / "brainspaces" / "example"
    targets = paths.brainspace_link_targets(dotbrain_home, "example")
    assert set(targets) == set(paths.BRAINSPACE_LINKS)
    assert targets[".brain"] == dotbrain_home / "brainspaces" / "example" / ".brain"
    assert targets[".beads"] == dotbrain_home / "brainspaces" / "example" / ".beads"
    assert targets[".claude"] == dotbrain_home / "brainspaces" / "example" / ".claude"
    assert targets[".codex"] == dotbrain_home / "brainspaces" / "example" / ".codex"


def test_data_dir_prefers_brainspaces_with_legacy_fallback(tmp_path: Path):
    root = tmp_path / "dotbrain"
    # Fresh root with neither dir defaults to brainspaces/.
    assert paths.data_dir(root) == root / "brainspaces"
    assert paths.brainspace(root, "p") == root / "brainspaces" / "p"

    # Legacy-only root resolves to projects/ for back-compat.
    (root / "projects").mkdir(parents=True)
    assert paths.data_dir(root) == root / "projects"
    assert paths.brainspace(root, "p") == root / "projects" / "p"

    # When both exist (mid-migration), brainspaces/ wins.
    (root / "brainspaces").mkdir(parents=True)
    assert paths.data_dir(root) == root / "brainspaces"
    assert paths.brainspace(root, "p") == root / "brainspaces" / "p"


def test_archive_paths_use_top_level_archive_root(tmp_path: Path):
    root = tmp_path / "dotbrain"
    assert paths.archive_root(root) == root / "archive"
    assert paths.archived_brainspace(root, "example") == root / "archive" / "example"
    assert paths.legacy_archive_root(root) == root / "brainspaces" / ".archive"
    assert paths.legacy_archived_brainspace(root, "example") == root / "brainspaces" / ".archive" / "example"


def test_disconnected_repo_is_not_wired(disconnected_adopter_repo: Path):
    assert paths.is_wired(disconnected_adopter_repo) is False
    assert not (paths.EXCLUDE_ENTRIES[0] in paths.exclude_entries(disconnected_adopter_repo))


def test_repo_is_wired_after_brainspace_link_symlinks_created(disconnected_adopter_repo: Path, brainspace: Path):
    # Model what the wire port will automate: link each Brainspace link into the Brainspace.
    for link in paths.BRAINSPACE_LINKS:
        (disconnected_adopter_repo / link).symlink_to(brainspace / link)
    assert paths.is_wired(disconnected_adopter_repo) is True
