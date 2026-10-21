from __future__ import annotations

from pathlib import Path
import tomllib

import pytest
import yaml

from dotbrain import subagents


CLAUDE_AGENTS = Path("plugin/agents")


def _claude_agent(role: str) -> tuple[dict, str]:
    _, frontmatter, body = (CLAUDE_AGENTS / f"{role}.md").read_text(encoding="utf-8").split("---", 2)
    return yaml.safe_load(frontmatter), body.strip()


@pytest.mark.parametrize("role", sorted(subagents.PROJECT_BASELINE))
def test_packaged_role_is_one_definition_on_both_runtimes(role: str):
    """Claude Code reads plugin/agents; Codex gets a delivered TOML copy of the same role."""
    fields, body = _claude_agent(role)
    codex = tomllib.loads(subagents.packaged_body(role, "codex"))
    assert codex["description"] == fields["description"]
    assert codex["model_reasoning_effort"] == fields["effort"]
    if role != "researcher":  # Codex reads through the shell, so its tool rules differ.
        assert codex["developer_instructions"].strip() == body
    # The operator's model choice wins in both runtimes.
    assert "model" not in codex and "model" not in fields


@pytest.mark.parametrize("role", [r for r in subagents.PROJECT_BASELINE if r != "researcher"])
def test_claude_roles_reach_a_shell_on_every_platform_and_never_nest(role: str):
    """Windows without Git Bash offers only PowerShell; plugin agents ignore permissionMode, hooks,
    and mcpServers, so the tool allowlist is the only capability lever."""
    fields, _ = _claude_agent(role)
    tools = {tool.strip() for tool in fields["tools"].split(",")}
    assert {"Bash", "PowerShell"} <= tools
    assert "Agent" not in tools
    assert not {"memory", "skills", "maxTurns", "permissionMode", "hooks", "mcpServers"} & set(fields)


def test_researcher_can_read_and_search_but_not_write_or_delegate():
    fields, _ = _claude_agent("researcher")
    assert {tool.strip() for tool in fields["tools"].split(",")} == {"Read", "Grep", "Glob", "WebSearch", "WebFetch"}
    codex = tomllib.loads(subagents.packaged_body("researcher", "codex"))
    assert codex["sandbox_mode"] == "read-only"
    assert codex["features"] == {"shell_tool": True, "multi_agent": False}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_load_global_subagents_missing_file_is_empty(tmp_path: Path):
    assert subagents.load_global_subagents(tmp_path) == ()


def test_load_global_subagents_reads_and_dedupes(tmp_path: Path):
    _write(
        tmp_path / "agents" / "agents.yaml",
        "global:\n  - reviewer\n  - reviewer\n  - helper\n",
    )
    assert subagents.load_global_subagents(tmp_path) == ("reviewer", "helper")


def test_load_global_config_merges_target_overrides_and_dedupes(tmp_path: Path):
    _write(
        tmp_path / "agents" / "agents.yaml",
        "targets:\n"
        "  claude-code: ~/.claude-work/agents\n"
        "global:\n"
        "  - reviewer\n"
        "  - reviewer\n"
        "  - helper\n",
    )

    config = subagents.load_global_config(tmp_path)

    assert config.targets == {
        "claude-code": "~/.claude-work/agents",
        "codex": "~/.codex/agents",
    }
    assert config.global_names == ("reviewer", "helper")


def test_load_global_config_rejects_invalid_targets(tmp_path: Path):
    _write(
        tmp_path / "agents" / "agents.yaml",
        "targets:\n  - not-a-mapping\n",
    )

    try:
        subagents.load_global_config(tmp_path)
    except ValueError as exc:
        assert "targets must be a mapping of runtime -> destination" in str(exc)
    else:
        raise AssertionError("expected invalid targets to raise ValueError")


def test_private_source_defines_own_agents_but_never_overrides_packaged(dotbrain_home: Path):
    _write(dotbrain_home / "agents" / "claude" / "custom.md", "claude-private")
    _write(dotbrain_home / "agents" / "codex" / "custom.toml", "codex-private")
    _write(dotbrain_home / "agents" / "claude" / "reviewer.md", "claude-override")
    _write(dotbrain_home / "agents" / "codex" / "reviewer.toml", "codex-override")

    custom = subagents._resolve_subagent_files(dotbrain_home, "custom")
    assert custom["claude-code"].read_text() == "claude-private"
    assert custom["codex"].read_text() == "codex-private"

    # A same-named private file never replaces a packaged subagent.
    packaged = subagents._resolve_subagent_files(dotbrain_home, "reviewer")
    assert set(packaged) == {"codex"}
    assert "codex-override" not in packaged["codex"].read_text()


def test_packaged_subagent_reaches_codex_prefixed_and_claude_through_the_plugin(dotbrain_home: Path):
    resolved = subagents._resolve_subagent_files(dotbrain_home, "reviewer")

    assert set(resolved) == {"codex"}
    assert resolved["codex"] == dotbrain_home / ".cache" / "agents" / "codex" / "dotbrain-reviewer.toml"
    assert tomllib.loads(resolved["codex"].read_text(encoding="utf-8"))["name"] == "dotbrain-reviewer"
    assert subagents.plugin_delivered("reviewer", "claude-code")
    assert not subagents.plugin_delivered("custom", "claude-code")


def test_link_files_into_prunes_only_owned_links(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-agents"
    dest.mkdir()
    _write(dotbrain_home / "agents" / "claude" / "reviewer.md", "reviewer")
    _write(dotbrain_home / "agents" / "claude" / "helper.md", "helper")
    files = [dotbrain_home / "agents" / "claude" / "reviewer.md"]

    (dest / "old.md").symlink_to(dotbrain_home / "agents" / "claude" / "helper.md")
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
    _write(dotbrain_home / "agents" / "claude" / "reviewer.md", "reviewer")
    (dest / "manual.md").write_text("keep me")

    result = subagents.link_files_into(
        dotbrain_home,
        dest,
        [dotbrain_home / "agents" / "claude" / "reviewer.md"],
        label="claude-code",
    )

    assert (dest / "manual.md").read_text() == "keep me"
    assert result.pruned == []


def test_link_project_subagents_links_matching_runtime(dotbrain_home: Path, brainspace: Path):
    _write(dotbrain_home / "agents" / "claude" / "custom.md", "claude")
    _write(dotbrain_home / "agents" / "codex" / "custom.toml", "codex")

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
    _write(dotbrain_home / "agents" / "claude" / "custom.md", "claude")

    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude",),
        ("custom",),
    )

    assert (brainspace / ".claude" / "agents" / "custom.md").is_symlink()
    assert result.linked == [".claude/agents/custom.md"]


def test_packaged_subagents_leave_claude_to_the_plugin_and_prune_old_deliveries(dotbrain_home: Path, brainspace: Path):
    claude_dir = brainspace / ".claude" / "agents"
    codex_dir = brainspace / ".codex" / "agents"
    # Earlier deliveries: a Claude link into the packaged cache and an unprefixed Codex copy.
    old_cache = dotbrain_home / ".cache" / "agents" / "claude" / "implementer.md"
    _write(old_cache, "old")
    claude_dir.mkdir(parents=True)
    (claude_dir / "implementer.md").symlink_to(old_cache)
    _write(codex_dir / "reviewer.toml", subagents.GENERATED_NOTICE + "\n" + subagents.MANAGED_MARKER + "\n\nold\n")

    _write(codex_dir / "dotbrain-explorer.toml", subagents.GENERATED_NOTICE + "\n" + subagents.MANAGED_MARKER + "\n\nold\n")
    result = subagents.link_project_subagents(dotbrain_home, brainspace, (".claude", ".codex"), subagents.PROJECT_BASELINE)

    assert not result.warnings
    assert list(claude_dir.iterdir()) == []
    assert sorted(path.name for path in codex_dir.iterdir()) == [
        f"dotbrain-{name}.toml" for name in sorted(subagents.PROJECT_BASELINE)
    ]
    for name in subagents.PROJECT_BASELINE:
        delivered = codex_dir / f"dotbrain-{name}.toml"
        assert subagents.is_managed_copy(delivered)
        assert tomllib.loads(delivered.read_text(encoding="utf-8"))["name"] == f"dotbrain-{name}"
    assert ".claude/agents/implementer.md" in result.pruned
    assert ".codex/agents/reviewer.toml" in result.pruned
    assert ".codex/agents/dotbrain-explorer.toml" in result.pruned


def test_project_subagent_collision_warns_and_skips(dotbrain_home: Path, brainspace: Path):
    _write(dotbrain_home / "agents" / "claude" / "custom.md", "custom")
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


def test_project_link_set_prepends_core_and_deduplicates() -> None:
    names = subagents.project_link_set(("reviewer", "custom", "verifier"))

    assert names[:4] == ("researcher", "reviewer", "verifier", "worker")
    assert names[-1] == "custom"
    assert names.count("reviewer") == 1
    assert names.count("verifier") == 1


def test_project_baseline_has_packaged_files_for_each_runtime(tmp_path: Path) -> None:
    plugin_agents = Path("plugin/agents")
    for name in subagents.PROJECT_BASELINE:
        resolved = subagents._resolve_subagent_files(tmp_path, name)
        assert set(resolved) == {"codex"}
        assert (plugin_agents / f"{name}.md").read_text(encoding="utf-8").startswith(f"---\nname: {name}\n")
