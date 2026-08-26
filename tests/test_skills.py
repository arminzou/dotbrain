"""Tests for the ``skills`` module: global config, project manifest, and symlink linking."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dotbrain import adopter_repos, resource_loader, skills

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


# ---------------------------------------------------------------------------
# Global config
# ---------------------------------------------------------------------------


def test_discover_skills_finds_all(dotbrain_home: Path):
    found = skills.discover_skills(dotbrain_home / "skills")
    assert found == [
        "brain/build-context",
        "brain/close-design",
        "brain/find-unknowns",
        "brain/grill-decisions",
        "brain/iterate-design",
        "brain/operate-execution",
        "brain/review-architecture",
        "brain/to-design",
        "brain/to-issues",
        "brain/triage-public",
        "brain/wire-brain",
        "brain/write-skills",
        "misc/discovery-test",
    ]


def test_discover_skills_skips_node_modules(dotbrain_home: Path):
    nm = dotbrain_home / "skills" / "frontend" / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "SKILL.md").write_text("# temporary fixture\n")
    assert "frontend/node_modules/pkg" not in skills.discover_skills(dotbrain_home / "skills")


def _write_global(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "skills.yaml"
    path.write_text(body)
    return path


def test_load_global_config_parses_current_schema(tmp_path: Path):
    path = _write_global(
        tmp_path,
        "targets:\n"
        "  codex: ~/.codex/skills\n"
        "global_extra:\n"
        "  - misc/x\n",
    )
    config = skills.load_global_config(path)
    assert config.targets == {"claude-code": "~/.claude/skills", "codex": "~/.codex/skills"}
    assert config.global_extra == ("misc/x",)


def test_load_global_config_accepts_legacy_extra_key(tmp_path: Path):
    path = _write_global(
        tmp_path,
        "targets:\n"
        "  codex: ~/.codex/skills\n"
        "global_extra:\n"
        "  - misc/x\n",
    )
    config = skills.load_global_config(path)
    assert config.global_extra == ("misc/x",)


def test_load_global_config_rejects_bad_targets(tmp_path: Path):
    path = _write_global(tmp_path, "targets:\n  - codex\n")
    with pytest.raises(ValueError):
        skills.load_global_config(path)


def test_reconcile_global_config_writes_current_key_names(tmp_path: Path):
    path = _write_global(
        tmp_path,
        "targets:\n"
        "  codex: ~/.codex/skills\n"
        "baseline:\n"
        "  - wrong/skill\n"
        "project_baseline:\n"
        "  - brain/operate-execution\n"
        "extra:\n"
        "  - misc/x\n",
    )
    skills.reconcile_global_config(path)
    text = path.read_text()
    assert "global_baseline:" not in text
    assert "project_baseline:" not in text
    assert "global_extra:\n  - misc/x\n" in text
    assert "\nbaseline:\n" not in text
    assert "\nextra:\n" not in text


def test_render_global_config_empty_global_extra():
    text = skills.render_global_config({"codex": "~/.codex/skills"}, [])
    assert "global_baseline:" not in text
    assert "project_baseline:" not in text
    assert "global_extra: []" in text


# ---------------------------------------------------------------------------
# Per-project link set
# ---------------------------------------------------------------------------


def test_project_link_set_uses_only_operator_selection_and_dedups():
    assert skills.project_link_set(["misc/x", "misc/x"]) == ("misc/x",)


def test_project_link_set_empty_extras_is_empty():
    assert skills.project_link_set([]) == ()


# ---------------------------------------------------------------------------
# Linking (create / prune / collision safety)
# ---------------------------------------------------------------------------

def test_links_operator_selection(dotbrain_home: Path, brainspace: Path):
    result = skills.link_project(
        dotbrain_home, brainspace, (".claude", ".codex"), ("misc/discovery-test",)
    )
    assert not result.warnings
    for workspace in (".claude", ".codex"):
        skills_dir = brainspace / workspace / "skills"
        link = skills_dir / "discovery-test"
        assert link.is_symlink()
        assert link.resolve() == (dotbrain_home / "skills" / "misc" / "discovery-test").resolve()


def test_prunes_stale(dotbrain_home: Path, brainspace: Path):
    skills_dir = brainspace / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    stale = skills_dir / "old-skill"
    stale.symlink_to(dotbrain_home / "skills" / "misc" / "discovery-test")
    result = skills.link_project(
        dotbrain_home, brainspace, (".claude",), ()
    )
    assert not stale.is_symlink()
    assert ".claude/skills/old-skill" in result.pruned


def test_project_collision_warns_and_skips(dotbrain_home: Path, brainspace: Path):
    skills_dir = brainspace / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    real = skills_dir / "discovery-test"
    real.write_text("real file, do not delete")
    result = skills.link_project(dotbrain_home, brainspace, (".claude",), ("misc/discovery-test",))
    assert real.read_text() == "real file, do not delete"
    assert not result.stashed
    assert any("was not created by dotbrain" in warning for warning in result.warnings)


def test_project_linking_preserves_foreign_symlinks(dotbrain_home: Path, brainspace: Path, tmp_path: Path):
    skills_dir = brainspace / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    foreign_target = tmp_path / "foreign"
    foreign_target.mkdir()
    foreign = skills_dir / "foreign"
    foreign.symlink_to(foreign_target)

    skills.link_project(dotbrain_home, brainspace, (".claude",), ())

    assert foreign.is_symlink()
    assert foreign.resolve() == foreign_target.resolve()


def test_project_link_results_reconcile_per_entry_excludes(
    dotbrain_home: Path, brainspace: Path, tmp_path: Path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    linked = skills.link_project(
        dotbrain_home,
        brainspace,
        (".codex",),
        ("misc/discovery-test",),
    )
    adopter_repos.reconcile_link_excludes(repo, linked=linked.linked)
    exclude = repo / ".git" / "info" / "exclude"
    assert "/.codex/skills/discovery-test" in exclude.read_text().splitlines()
    assert "/.codex" not in exclude.read_text().splitlines()
    assert "/.codex/" not in exclude.read_text().splitlines()

    pruned = skills.link_project(dotbrain_home, brainspace, (".codex",), ())
    adopter_repos.reconcile_link_excludes(repo, pruned=pruned.pruned)
    assert "/.codex/skills/discovery-test" not in exclude.read_text().splitlines()


def test_missing_skill_warns(dotbrain_home: Path, brainspace: Path):
    result = skills.link_project(
        dotbrain_home, brainspace, (".claude",), ("misc/does-not-exist",)
    )
    assert any("does-not-exist" in w for w in result.warnings)
    assert not (brainspace / ".claude" / "skills" / "does-not-exist").exists()


def test_link_into_links_an_include_list(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-skills"
    result = skills.link_into(
        dotbrain_home, dest, ("misc/discovery-test",), label="codex"
    )
    assert not result.warnings
    assert (dest / "discovery-test").is_symlink()
    assert result.linked == ["codex/discovery-test"]


def test_link_into_owned_prune_keeps_foreign_links(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-skills"
    dest.mkdir()
    # a stale link into the dotbrain skills tree -> pruned; an unrelated link -> kept.
    (dest / "old").symlink_to(dotbrain_home / "skills" / "misc" / "discovery-test")
    (dest / "foreign").symlink_to(tmp_path / "elsewhere")
    skills.link_into(dotbrain_home, dest, ("misc/discovery-test",), prune_owned_only=True)
    assert (dest / "discovery-test").is_symlink()
    assert not (dest / "old").is_symlink()   # pointed into skills/, not wanted -> pruned
    assert (dest / "foreign").is_symlink()   # foreign link preserved


def test_link_into_removes_legacy_bundled_cache(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-skills"
    dest.mkdir()
    cache = dotbrain_home / ".cache" / "skills" / "brain" / "wire-brain"
    cache.mkdir(parents=True)
    stale = dest / "wire-brain"
    stale.symlink_to(cache)

    skills.link_into(dotbrain_home, dest, (), prune_owned_only=True)

    assert not cache.parents[1].exists()
    assert not stale.exists()


def test_link_into_stashes_real_collision(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-skills"
    dest.mkdir()
    real = dest / "discovery-test"
    real.write_text("real, do not delete")
    result = skills.link_into(dotbrain_home, dest, ("misc/discovery-test",))
    assert (dest / "discovery-test").is_symlink()
    assert result.stashed and result.stashed[0].read_text() == "real, do not delete"


def test_link_into_raises_translated_windows_privilege_error(dotbrain_home: Path, tmp_path: Path, monkeypatch):
    dest = tmp_path / "global-skills"

    def raising_symlink_to(self, target, target_is_directory=False):
        exc = OSError("A required privilege is not held by the client")
        exc.winerror = 1314
        raise exc

    monkeypatch.setattr(Path, "symlink_to", raising_symlink_to)

    with pytest.raises(RuntimeError, match="Developer Mode"):
        skills.link_into(dotbrain_home, dest, ("misc/discovery-test",))

    assert not (dest / "discovery-test").exists()


def test_wire_brain_skill_tracks_current_cli_wiring_model():
    text = resource_loader.resource("skills/brain/wire-brain/SKILL.md").read_text()

    for command in (
        "dotbrain wire",
        "dotbrain wire --all",
        "dotbrain worktrees wire",
        "dotbrain refresh",
        "dotbrain bootstrap",
        "dotbrain doctor",
        "dotbrain unwire",
        "dotbrain beads drop-db",
    ):
        assert command in text

    for phrase in (
        "Expected wiring is derived from project config",
        "beads.mode",
        "agents",
        "skills",
        "subagents",
        "public-tracker",
    ):
        assert phrase in text
