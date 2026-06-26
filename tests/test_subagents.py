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

        def read_text(self) -> str:
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
        prune_owned_only=True,
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
        prune_owned_only=True,
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
    assert not (brainspace / ".codex" / "agents" / "reviewer.toml").exists()
    assert result.linked == [".claude/reviewer.md"]


def test_link_project_subagents_warns_for_missing_name(dotbrain_home: Path, brainspace: Path):
    result = subagents.link_project_subagents(
        dotbrain_home,
        brainspace,
        (".claude", ".codex"),
        ("missing",),
    )

    assert result.warnings == ["subagent not found: missing"]
