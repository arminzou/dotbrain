"""Tests for the ``skills`` module: global config, project manifest, and symlink linking."""

from __future__ import annotations

from pathlib import Path

import pytest

from dotbrain import skills

BASE = skills.project_baseline()


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
        "brain/enter-main-agent",
        "brain/grill-decisions",
        "brain/operate-execution",
        "brain/review-architecture",
        "brain/to-issues",
        "brain/to-prd",
        "brain/triage-public",
        "brain/wire-brain",
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
        "global_baseline:\n"
        "  - brain/wire-brain\n"
        "project_baseline:\n"
        "  - brain/operate-execution\n"
        "global_extra:\n"
        "  - misc/x\n",
    )
    config = skills.load_global_config(path)
    assert config.targets == {"claude-code": "~/.claude/skills", "codex": "~/.codex/skills"}
    assert config.project_baseline == skills.PROJECT_BASELINE
    assert config.global_extra == ("misc/x",)
    assert config.linked == ("brain/wire-brain", "misc/x")


def test_load_global_config_accepts_legacy_extra_key(tmp_path: Path):
    path = _write_global(
        tmp_path,
        "targets:\n"
        "  codex: ~/.codex/skills\n"
        "baseline:\n"
        "  - brain/wire-brain\n"
        "global_extra:\n"
        "  - brain/wire-brain\n"
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
    text = skills.render_global_config({"codex": "~/.codex/skills"}, [], project_baseline=())
    assert "global_baseline:" not in text
    assert "project_baseline:" not in text
    assert "global_extra: []" in text


# ---------------------------------------------------------------------------
# Required core (packaged) and per-project link set
# ---------------------------------------------------------------------------


def test_required_core_comes_from_packaged_resource():
    assert skills.GLOBAL_BASELINE == ("brain/wire-brain",)
    assert "brain/operate-execution" in skills.PROJECT_BASELINE
    assert skills.project_baseline() == skills.PROJECT_BASELINE


def test_project_link_set_prepends_required_core():
    assert skills.project_link_set(["misc/discovery-test"]) == BASE + ("misc/discovery-test",)


def test_project_link_set_drops_required_from_extras_and_dedups():
    # An operator can't re-add a required skill, and duplicates collapse.
    assert skills.project_link_set(["brain/operate-execution", "misc/x", "misc/x"]) == BASE + ("misc/x",)


def test_project_link_set_empty_extras_is_required_core():
    assert skills.project_link_set([]) == BASE


# ---------------------------------------------------------------------------
# Linking (create / prune / collision safety)
# ---------------------------------------------------------------------------

_SKILL_PATH = {
    "operate-execution": "brain/operate-execution",
    "enter-main-agent": "brain/enter-main-agent",
    "triage-public": "brain/triage-public",
    "discovery-test": "misc/discovery-test",
}


def test_links_baseline_and_extra(dotbrain_home: Path, brainspace: Path):
    skill_paths = skills.project_baseline(dotbrain_home) + ("misc/discovery-test",)
    result = skills.link_project(dotbrain_home, brainspace, (".claude", ".codex"), skill_paths)
    assert not result.warnings
    for workspace in (".claude", ".codex"):
        skills_dir = brainspace / workspace / "skills"
        for name, path in _SKILL_PATH.items():
            link = skills_dir / name
            assert link.is_symlink()
            assert link.resolve() == (dotbrain_home / "skills" / path).resolve()


def test_prunes_stale(dotbrain_home: Path, brainspace: Path):
    skills_dir = brainspace / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    stale = skills_dir / "old-skill"
    stale.symlink_to("../nowhere")
    result = skills.link_project(
        dotbrain_home, brainspace, (".claude",), skills.project_baseline(dotbrain_home)
    )
    assert not stale.is_symlink()
    assert ".claude/old-skill" in result.pruned


def test_collision_moved_not_deleted(dotbrain_home: Path, brainspace: Path):
    skills_dir = brainspace / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    real = skills_dir / "operate-execution"
    real.write_text("real file, do not delete")
    result = skills.link_project(dotbrain_home, brainspace, (".claude",), ("brain/operate-execution",))
    assert (skills_dir / "operate-execution").is_symlink()
    assert result.stashed
    moved = result.stashed[0]
    assert moved.parent.name == ".tmp"
    assert moved.read_text() == "real file, do not delete"


def test_missing_skill_warns(dotbrain_home: Path, brainspace: Path):
    result = skills.link_project(
        dotbrain_home, brainspace, (".claude",), ("brain/does-not-exist",)
    )
    assert any("does-not-exist" in w for w in result.warnings)
    assert not (brainspace / ".claude" / "skills" / "does-not-exist").exists()


def test_link_into_links_an_include_list(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-skills"
    result = skills.link_into(
        dotbrain_home, dest, ("brain/wire-brain", "misc/discovery-test"), label="codex"
    )
    assert not result.warnings
    assert (dest / "wire-brain").resolve() == (dotbrain_home / "skills" / "brain" / "wire-brain").resolve()
    assert (dest / "discovery-test").is_symlink()
    assert result.linked == ["codex/wire-brain", "codex/discovery-test"]


def test_link_into_owned_prune_keeps_foreign_links(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-skills"
    dest.mkdir()
    # a stale link into the dotbrain skills tree -> pruned; an unrelated link -> kept.
    (dest / "old").symlink_to(dotbrain_home / "skills" / "misc" / "discovery-test")
    (dest / "foreign").symlink_to(tmp_path / "elsewhere")
    skills.link_into(dotbrain_home, dest, ("brain/wire-brain",), prune_owned_only=True)
    assert (dest / "wire-brain").is_symlink()
    assert not (dest / "old").is_symlink()   # pointed into skills/, not wanted -> pruned
    assert (dest / "foreign").is_symlink()   # foreign link preserved


def test_link_into_stashes_real_collision(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "global-skills"
    dest.mkdir()
    real = dest / "wire-brain"
    real.write_text("real, do not delete")
    result = skills.link_into(dotbrain_home, dest, ("brain/wire-brain",))
    assert (dest / "wire-brain").is_symlink()
    assert result.stashed and result.stashed[0].read_text() == "real, do not delete"
