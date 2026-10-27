from __future__ import annotations

from pathlib import Path
import tomllib

import pytest
import yaml

from dotbrain import config, resource_loader, subagents


ROLES = config.PACKAGED_ROLES


def _claude_agent(role: str) -> tuple[dict, str]:
    _, frontmatter, body = subagents.packaged_body(role, "claude-code").split("---", 2)
    return yaml.safe_load(frontmatter), body.strip()


@pytest.mark.parametrize("role", ROLES)
def test_packaged_role_is_one_definition_on_both_runtimes(role: str):
    """Claude Code and Codex receive copies of the same role, built from its contract."""
    fields, body = _claude_agent(role)
    codex = tomllib.loads(subagents.packaged_body(role, "codex"))
    assert codex["description"] == fields["description"]
    assert codex["model_reasoning_effort"] == fields["effort"]
    assert codex["developer_instructions"].strip() == body == subagents.role_contract(role).strip()
    # The operator's model choice wins in both runtimes.
    assert "model" not in codex and "model" not in fields


@pytest.mark.parametrize("role", [r for r in ROLES if r != "researcher"])
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
    assert result.warnings and "reserved for packaged subagents" in result.warnings[0]
    assert not (brainspace / ".codex" / "agents" / "dotbrain-mine.toml").exists()


@pytest.mark.parametrize("workspace, runtime, suffix", [(".claude", "claude-code", ".md"), (".codex", "codex", ".toml")])
def test_custom_delivery_never_touches_packaged_entries(dotbrain_home: Path, brainspace: Path, workspace, runtime, suffix):
    target = brainspace / workspace / "agents" / f"dotbrain-reviewer{suffix}"
    body = subagents.managed_text(subagents.packaged_body("reviewer", runtime), suffix)
    _write(target, body)
    result = subagents.link_project_subagents(dotbrain_home, brainspace, (workspace,), ())
    assert not result.pruned
    assert target.read_text() == body


@pytest.mark.parametrize("runtime, suffix", [("claude-code", ".md"), ("codex", ".toml")])
def test_packaged_reconciliation_preserves_foreign_collision_and_custom_file(tmp_path, runtime, suffix):
    target = tmp_path / "agents"
    foreign = target / f"dotbrain-worker{suffix}"
    custom = target / f"custom{suffix}"
    _write(foreign, "user-owned")
    _write(custom, "custom")
    result = subagents.reconcile_packaged(target, ("worker",), runtime, label="agents")
    assert foreign.read_text() == "user-owned" and custom.read_text() == "custom"
    assert len(result.notices) == 1 and str(foreign) in result.notices[0]
    assert not result.linked and not result.pruned


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


def test_packaged_roles_are_real_marked_files_in_both_workspaces(dotbrain_home: Path, brainspace: Path):
    claude_dir = brainspace / ".claude" / "agents"
    codex_dir = brainspace / ".codex" / "agents"
    # An earlier delivery: an unprefixed Codex copy is pruned by custom reconciliation.
    _write(codex_dir / "reviewer.toml", subagents.GENERATED_NOTICE + "\n" + subagents.MANAGED_MARKER + "\n\nold\n")

    result = subagents.link_project_subagents(dotbrain_home, brainspace, (".claude", ".codex"), (), packaged=ROLES)

    assert not result.warnings and not result.notices
    assert sorted(p.name for p in claude_dir.iterdir()) == [f"dotbrain-{r}.md" for r in ROLES]
    assert sorted(p.name for p in codex_dir.iterdir()) == [f"dotbrain-{r}.toml" for r in ROLES]
    for role in ROLES:
        claude = claude_dir / f"dotbrain-{role}.md"
        codex = codex_dir / f"dotbrain-{role}.toml"
        for delivered in (claude, codex):
            assert not delivered.is_symlink() and subagents.is_managed_copy(delivered)
        assert yaml.safe_load(claude.read_text(encoding="utf-8").split("---", 2)[1])["name"] == f"dotbrain-{role}"
        assert tomllib.loads(codex.read_text(encoding="utf-8"))["name"] == f"dotbrain-{role}"
    assert ".codex/agents/reviewer.toml" in result.pruned

    again = subagents.link_project_subagents(dotbrain_home, brainspace, (".claude", ".codex"), (), packaged=ROLES)
    assert not again.linked and not again.pruned


def test_unlisted_packaged_roles_are_pruned_and_foreign_files_reported(dotbrain_home: Path, brainspace: Path):
    workspaces = (".claude", ".codex")
    subagents.link_project_subagents(dotbrain_home, brainspace, workspaces, (), packaged=ROLES)
    foreign = brainspace / ".claude" / "agents" / "dotbrain-mine.md"
    _write(foreign, "---\nname: dotbrain-mine\n---\n")

    result = subagents.link_project_subagents(dotbrain_home, brainspace, workspaces, (), packaged=("worker",))
    assert sorted(result.pruned) == sorted(f"{ws}/agents/dotbrain-{r}{s}" for ws, s in ((".claude", ".md"), (".codex", ".toml"))
                                           for r in ROLES if r != "worker")
    assert any(str(foreign) in notice for notice in result.notices)

    subagents.link_project_subagents(dotbrain_home, brainspace, workspaces, (), packaged=())
    assert [p.name for p in (brainspace / ".claude" / "agents").iterdir()] == ["dotbrain-mine.md"]
    assert list((brainspace / ".codex" / "agents").iterdir()) == []


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


def test_packaged_roles_have_definitions_for_each_runtime() -> None:
    for role in ROLES:
        assert resource_loader.resource(f"agents/claude/dotbrain-{role}.md").read_text(encoding="utf-8").startswith(f"---\nname: dotbrain-{role}\n")
        assert subagents.packaged_body(role, "claude-code").startswith(f"---\nname: dotbrain-{role}\n")


@pytest.mark.parametrize("runtime", ["claude-code", "codex"])
def test_packaged_definition_is_settings_plus_its_role_contract(runtime: str, monkeypatch) -> None:
    """Packaged resources hold settings only, so a contract change reaches the next delivery."""
    directory, suffix = subagents.runtime_spec()[runtime]
    for role in ROLES:
        settings = resource_loader.resource(f"agents/{directory}/dotbrain-{role}{suffix}").read_text(encoding="utf-8")
        assert subagents.role_contract(role).splitlines()[2] not in settings
    contract = 'Changed contract with """quotes""" and a \\path.\n'
    monkeypatch.setattr(subagents, "role_contract", lambda role: contract)
    delivered = subagents.packaged_body("researcher", runtime)
    if runtime == "codex":
        parsed = tomllib.loads(delivered)
        assert parsed["developer_instructions"] == contract
        assert parsed["features"]["multi_agent"] is False
    else:
        assert delivered.endswith(f"---\n\n{contract}")
