from __future__ import annotations

from pathlib import Path

from dotbrain import subagents


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


def test_seed_private_subagents_copies_bundled_examples_once(
    dotbrain_home: Path, monkeypatch
):
    payloads = {
        "agents/claude/reviewer.md": "claude-example",
        "agents/codex/reviewer.toml": "codex-example",
    }

    class FakeResource:
        def __init__(self, text: str):
            self._text = text

        def read_text(self, encoding: str | None = None) -> str:
            return self._text

    def fake_iter(path: str):
        assert path == "agents"
        for rel, text in (
            (Path("claude/reviewer.md"), payloads["agents/claude/reviewer.md"]),
            (Path("codex/reviewer.toml"), payloads["agents/codex/reviewer.toml"]),
        ):
            yield rel, FakeResource(text)

    monkeypatch.setattr(subagents.resource_loader, "iter_resource_files", fake_iter)

    seeded = subagents.seed_private_subagents(dotbrain_home)

    assert [path.relative_to(dotbrain_home) for path in seeded] == [
            Path("agents/claude/reviewer.md"),
            Path("agents/codex/reviewer.toml"),
    ]
    assert (dotbrain_home / "agents" / "claude" / "reviewer.md").read_text() == "claude-example"
    assert (dotbrain_home / "agents" / "codex" / "reviewer.toml").read_text() == "codex-example"

    (dotbrain_home / "agents" / "claude" / "reviewer.md").write_text("my override")
    seeded = subagents.seed_private_subagents(dotbrain_home)

    assert seeded == []
    assert (dotbrain_home / "agents" / "claude" / "reviewer.md").read_text() == "my override"


def test_resolve_subagent_files_prefers_private(dotbrain_home: Path):
    _write(dotbrain_home / "agents" / "claude" / "reviewer.md", "claude-private")
    _write(dotbrain_home / "agents" / "codex" / "reviewer.toml", "codex-private")

    resolved = subagents._resolve_subagent_files(dotbrain_home, "reviewer")

    assert resolved["claude-code"].read_text() == "claude-private"
    assert resolved["codex"].read_text() == "codex-private"


def test_resolve_subagent_files_caches_bundled(dotbrain_home: Path, monkeypatch):
    payloads = {
        "agents/claude/reviewer.md": "claude-bundled",
        "agents/codex/reviewer.toml": "codex-bundled",
    }

    class FakeResource:
        def __init__(self, text: str):
            self._text = text

        def is_file(self) -> bool:
            return True

        def read_text(self, encoding: str | None = None) -> str:
            return self._text

    def fake_resource(path: str):
        if path not in payloads:
            raise FileNotFoundError(path)
        return FakeResource(payloads[path])

    monkeypatch.setattr(subagents.resource_loader, "resource", fake_resource)

    resolved = subagents._resolve_subagent_files(dotbrain_home, "reviewer")

    assert resolved["claude-code"] == dotbrain_home / ".cache" / "agents" / "claude" / "reviewer.md"
    assert resolved["codex"] == dotbrain_home / ".cache" / "agents" / "codex" / "reviewer.toml"
    assert resolved["claude-code"].read_text() == "claude-bundled"
    assert resolved["codex"].read_text() == "codex-bundled"


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
    _write(dotbrain_home / "agents" / "claude" / "reviewer.md", "claude")
    _write(dotbrain_home / "agents" / "codex" / "reviewer.toml", "codex")

    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude", ".codex"),
        ("reviewer",),
    )

    assert (brainspace / ".claude" / "agents" / "reviewer.md").is_symlink()
    assert (brainspace / ".codex" / "agents" / "reviewer.toml").is_symlink()
    assert result.linked == [".claude/reviewer.md", ".codex/reviewer.toml"]


def test_link_project_subagents_routes_only_existing_runtime(dotbrain_home: Path, brainspace: Path):
    _write(dotbrain_home / "agents" / "claude" / "reviewer.md", "claude")

    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude", ".codex"),
        ("reviewer",),
    )

    assert (brainspace / ".claude" / "agents" / "reviewer.md").is_symlink()
    assert (brainspace / ".codex" / "agents" / "reviewer.toml").is_symlink()
    assert result.linked == [".claude/reviewer.md", ".codex/reviewer.toml"]


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

    assert names[:4] == ("implementer", "investigator", "reviewer", "verifier")
    assert names[-1] == "custom"
    assert names.count("reviewer") == 1
    assert names.count("verifier") == 1


def test_project_baseline_has_packaged_files_for_each_runtime(tmp_path: Path) -> None:
    for name in subagents.PROJECT_BASELINE:
        resolved = subagents._resolve_subagent_files(tmp_path, name)
        assert set(resolved) == {"claude-code", "codex"}
