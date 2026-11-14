from __future__ import annotations

from pathlib import Path

import pytest

from dotbrain import subagents


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_load_global_subagents_missing_file_is_empty(tmp_path: Path):
    assert subagents.load_global_subagents(tmp_path) == ()


def test_load_global_subagents_reads_config_yaml_and_dedupes(tmp_path: Path):
    _write(tmp_path / "config.yaml", "version: 4\nsubagents:\n  - helper\n  - helper\n  - other\n")
    assert subagents.load_global_subagents(tmp_path) == ("helper", "other")


def test_private_source_defines_custom_agents(dotbrain_home: Path):
    _write(dotbrain_home / "subagents" / "claude" / "custom.md", "claude-private")
    _write(dotbrain_home / "subagents" / "codex" / "custom.toml", "codex-private")

    custom = subagents._resolve_subagent_files(dotbrain_home, "custom")
    assert custom["claude-code"].read_text() == "claude-private"
    assert custom["codex"].read_text() == "codex-private"


def test_custom_subagent_with_packaged_prefix_is_rejected(dotbrain_home: Path, brainspace: Path):
    _write(dotbrain_home / "subagents" / "codex" / "dotbrain-mine.toml", "x")
    result = subagents.link_project_subagents(dotbrain_home, brainspace, (".codex",), ("dotbrain-mine",))
    assert result.warnings and "reserved for retired packaged subagents" in result.warnings[0]
    assert not (brainspace / ".codex" / "agents" / "dotbrain-mine.toml").exists()


def test_link_files_into_prunes_only_owned_links(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-agents"
    dest.mkdir()
    _write(dotbrain_home / "subagents" / "claude" / "reviewer.md", "reviewer")
    _write(dotbrain_home / "subagents" / "claude" / "helper.md", "helper")
    files = [dotbrain_home / "subagents" / "claude" / "reviewer.md"]

    (dest / "old.md").symlink_to(dotbrain_home / "subagents" / "claude" / "helper.md")
    (dest / "foreign.md").symlink_to(tmp_path / "foreign.md")

    result = subagents.link_files_into(
        dotbrain_home,
        dest,
        files,
        label="claude-code",
    )

    assert (dest / "reviewer.md").is_symlink()
    assert not (dest / "old.md").exists()
    assert (dest / "foreign.md").is_symlink()
    assert result.linked == ["claude-code/reviewer.md"]
    assert result.pruned == ["claude-code/old.md"]


def test_link_files_into_leaves_foreign_regular_file(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-agents"
    dest.mkdir()
    _write(dotbrain_home / "subagents" / "claude" / "reviewer.md", "reviewer")
    (dest / "manual.md").write_text("keep me")

    result = subagents.link_files_into(
        dotbrain_home,
        dest,
        [dotbrain_home / "subagents" / "claude" / "reviewer.md"],
        label="claude-code",
    )

    assert (dest / "manual.md").read_text() == "keep me"
    assert result.pruned == []


def test_link_project_subagents_links_matching_runtime(dotbrain_home: Path, brainspace: Path):
    _write(dotbrain_home / "subagents" / "claude" / "custom.md", "claude")
    _write(dotbrain_home / "subagents" / "codex" / "custom.toml", "codex")

    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude", ".codex"),
        ("custom",),
    )

    assert (brainspace / ".claude" / "agents" / "custom.md").is_symlink()
    assert subagents.is_managed_copy(brainspace / ".codex" / "agents" / "custom.toml")
    assert result.linked == [".claude/agents/custom.md", ".codex/agents/custom.toml"]


def test_link_project_subagents_routes_only_existing_runtime(dotbrain_home: Path, brainspace: Path):
    _write(dotbrain_home / "subagents" / "claude" / "custom.md", "claude")

    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude",),
        ("custom",),
    )

    assert (brainspace / ".claude" / "agents" / "custom.md").is_symlink()
    assert result.linked == [".claude/agents/custom.md"]


def test_project_subagent_collision_warns_and_skips(dotbrain_home: Path, brainspace: Path):
    _write(dotbrain_home / "subagents" / "claude" / "custom.md", "custom")
    collision = brainspace / ".claude" / "agents" / "custom.md"
    _write(collision, "project-owned")

    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude",),
        ("custom",),
    )

    assert collision.read_text() == "project-owned"
    assert not result.stashed
    assert any("was not created by dotbrain" in warning for warning in result.warnings)


def test_link_project_subagents_warns_for_missing_name(dotbrain_home: Path, brainspace: Path):
    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude", ".codex"),
        ("missing",),
    )

    assert result.warnings == ["subagent not found: missing"]


@pytest.mark.parametrize("runtime,suffix", [("claude-code", ".md"), ("codex", ".toml")])
def test_retire_only_exact_generated_agents(tmp_path, runtime, suffix):
    original = (Path(__file__).parent / "fixtures/retired-agents" / f"{runtime}{suffix}").read_text(encoding="utf-8")
    target = tmp_path / "agents"
    generated = target / f"dotbrain-verifier{suffix}"
    _write(generated, original)
    foreign = target / f"dotbrain-foreign{suffix}"
    _write(foreign, "user-owned")
    custom = target / f"custom{suffix}"
    _write(custom, "custom")
    result = subagents.retire_packaged(target, runtime, label="agents")
    assert result.pruned == [f"agents/{generated.name}"]
    assert not generated.exists()
    assert foreign.read_text() == "user-owned" and custom.read_text() == "custom"
    assert len(result.notices) == 1 and str(foreign) in result.notices[0]
    assert not subagents.retire_packaged(target, runtime, label="agents").pruned

    _write(generated, original + "\nUser modification\n")
    result = subagents.retire_packaged(target, runtime, label="agents")
    assert not result.pruned and generated.read_text(encoding="utf-8") == original + "\nUser modification\n"
    assert any(str(generated) in notice for notice in result.notices)
    generated.unlink()
    source = tmp_path / f"private{suffix}"
    _write(source, original)
    generated.symlink_to(source)
    assert not subagents.retire_packaged(target, runtime, label="agents").pruned
    assert generated.is_symlink() and source.read_text(encoding="utf-8") == original
