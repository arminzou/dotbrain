"""Bootstrap merges the retired global settings files into config.yaml version 4."""
import subprocess
from pathlib import Path

import pytest
import yaml

from dotbrain import assets, bootstrap, config, doctor, profile_migration


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def no_git(*args, **kwargs):
    return subprocess.CompletedProcess(args, 0)


def legacy_root(tmp_path):
    """A data root in the previous layout, with global delivery already in the user's homes."""
    root, user = tmp_path / "data", tmp_path / "user"
    (root / ".git").mkdir(parents=True)
    write(root / "config.yaml", "# my settings\nversion: 3\nsync:\n  enabled: false # keep\n")
    write(root / "skills/skills.yaml",
          "version: 1\n"
          "targets:\n  claude-code: ~/.claude/skills\n  codex: ~/.codex-work/skills\n"
          "profiles:\n  claude-code: [~/.claude-work]\n"
          "global_extra:\n  - collection/example\n")
    write(root / "skills/collection/example/SKILL.md", "example")
    write(root / "agents/agents.yaml", "targets:\n  codex: ~/.codex/agents\nglobal: [custom, reviewer]\n")
    write(root / "agents/claude/custom.md", "custom")
    write(root / "agents/codex/custom.toml", 'name = "custom"\n')
    for home in (".claude", ".claude-work", ".codex", ".codex-work"):
        (user / home).mkdir(parents=True)
    (user / ".claude/agents").mkdir()
    (user / ".claude/agents/custom.md").symlink_to(root / "agents/claude/custom.md")
    return root, user


def delivered(user):
    return sorted(path.relative_to(user).as_posix() for path in user.rglob("*")
                  if path.is_symlink() or path.is_file())


def test_bootstrap_merges_retired_files_once(tmp_path):
    root, user = legacy_root(tmp_path)

    first = bootstrap.prepare(root, home=user, run=no_git)

    assert first.status == "success", first
    logs = "\n".join(first.targets[0].changes)
    assert "dropped targets.claude-code" in logs and "dropped targets.codex" in logs
    assert "converted targets.codex to profiles.codex: [~/.codex-work]" in logs
    assert "dropped packaged subagents reviewer" in logs
    text = (root / "config.yaml").read_text()
    assert text.startswith("# my settings\nversion: 4\n") and "enabled: false # keep" in text
    cfg = config.load_config(root)
    assert cfg.version == 4 and cfg.sync.enabled is False
    assert cfg.profiles == {"claude-code": ["~/.claude-work"], "codex": ["~/.codex-work"]}
    assert cfg.skills == ("collection/example",) and cfg.subagents == ("custom",)
    assert not (root / "skills/skills.yaml").exists() and not (root / "agents").exists()
    assert (root / "subagents/claude/custom.md").is_file()
    [backup] = (root / ".cache/config-backups").iterdir()
    assert (backup / "skills/skills.yaml").read_text().startswith("version: 1\ntargets:")
    assert (backup / "agents/agents.yaml").read_text().endswith("global: [custom, reviewer]\n")
    assert (backup / "config.yaml").read_text().startswith("# my settings\nversion: 3\n")

    # Global delivery reaches the same homes and resolves to the renamed sources.
    for home in (".claude", ".claude-work", ".codex", ".codex-work"):
        assert (user / home / "skills/example").is_symlink()
    claude_agent = user / ".claude/agents/custom.md"
    assert claude_agent.resolve() == (root / "subagents/claude/custom.md").resolve()
    assert (user / ".codex/agents/custom.toml").is_file()
    assert not (user / ".codex/agents/dotbrain-reviewer.toml").exists()

    before, files = snapshot(root), delivered(user)
    second = bootstrap.prepare(root, home=user, run=no_git)
    assert second.status == "success" and not second.targets[0].changes
    assert profile_migration.plan(root, user) is None
    assert snapshot(root) == before and delivered(user) == files


def test_missing_config_is_seeded_from_template_with_merged_settings(tmp_path):
    root = tmp_path / "data"
    write(root / "skills/skills.yaml", "global_extra: [collection/example]\n")

    profile_migration.apply(root, profile_migration.plan(root, tmp_path / "user"))

    text = (root / "config.yaml").read_text()
    assert "# dotbrain global settings" in text
    assert config.load_config(root).skills == ("collection/example",)


def test_existing_equal_selection_is_not_a_conflict(tmp_path):
    root = tmp_path / "data"
    write(root / "config.yaml", "version: 3\nskills: [collection/example]\n")
    write(root / "skills/skills.yaml", "global_extra: [collection/example]\n")

    profile_migration.apply(root, profile_migration.plan(root, tmp_path / "user"))

    assert yaml.safe_load((root / "config.yaml").read_text()) == {
        "version": 4, "skills": ["collection/example"], "profiles": {}, "subagents": []}


def test_empty_legacy_directory_is_removed_when_subagents_exists(tmp_path):
    root = tmp_path / "data"
    write(root / "agents/agents.yaml", "global: []\n")
    (root / "agents/claude").mkdir()
    write(root / "subagents/claude/custom.md", "custom")

    profile_migration.apply(root, profile_migration.plan(root, tmp_path / "user"))

    assert not (root / "agents").exists()
    assert (root / "subagents/claude/custom.md").is_file()


@pytest.mark.parametrize("files,reason", [
    ({"skills/skills.yaml": "base: &x [a]\nglobal_extra: *x\n"}, "anchors"),
    ({"agents/agents.yaml": "a: &a {global: [x]}\n<<: *a\n"}, "anchors"),
    ({"skills/skills.yaml": "global_extra: [unclosed\n"}, "unparseable"),
    ({"skills/skills.yaml": "global_extra: []\nglobal_extra: [x]\n"}, "duplicate"),
    ({"skills/skills.yaml": "- not a mapping\n"}, "mapping"),
    ({"skills/skills.yaml": "global_extra: []\nunknown: 1\n"}, "unknown keys"),
    ({"skills/skills.yaml": "targets:\n  hermes: ~/hermes-skills\n"}, "no profile equivalent"),
    ({"skills/skills.yaml": "targets:\n  codex: ~/elsewhere/folder\n"}, "does not end in /skills"),
    ({"skills/skills.yaml": "profiles: {hermes: [~/.hermes]}\n"}, "profiles"),
    ({"skills/skills.yaml": "global_extra: [a]\n", "config.yaml": "skills: [b]\n"}, "conflicts"),
    ({"skills/skills.yaml": "global_extra: [a]\n", "config.yaml": "x: &y 1\n"}, "anchors"),
    ({"agents/agents.yaml": "global: []\n", "agents/claude/a.md": "a", "subagents/claude/b.md": "b"},
     "both agents/ and subagents/"),
])
def test_ambiguous_input_stops_and_changes_nothing(tmp_path, files, reason):
    root = tmp_path / "data"
    (root / ".git").mkdir(parents=True)
    for name, text in files.items():
        write(root / name, text)
    before = snapshot(root)

    with pytest.raises(ValueError, match=reason):
        profile_migration.plan(root, tmp_path / "user")
    result = bootstrap.prepare(root, home=tmp_path / "user", run=no_git)

    assert result.status == "failure"
    assert any("no file was changed" in error for error in result.targets[0].errors)
    assert snapshot(root) == before


def test_delivery_waits_for_migration(tmp_path):
    root, user = legacy_root(tmp_path)
    before = delivered(user)

    result = assets.link_global(root, "skills", user_home=user)

    assert "run dotbrain bootstrap" in result.warnings[0]
    assert delivered(user) == before


def test_doctor_reports_leftover_files_and_refusal_without_writing(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    write(root / "agents/agents.yaml", "global: [custom]\n")
    before = snapshot(root)

    findings = doctor._check_machine(root, user)
    assert any(f.status == "warn" and "agents/agents.yaml" in f.message and "dotbrain bootstrap" in f.suggestion
               for f in findings)
    write(root / "skills/skills.yaml", "unknown: 1\n")
    before = snapshot(root)
    findings = doctor._check_machine(root, user)
    assert any(f.status == "error" and "unknown keys" in f.message for f in findings)
    assert snapshot(root) == before


def test_nothing_reads_retired_files_after_migration(tmp_path):
    root = tmp_path / "data"
    write(root / "config.yaml", "version: 4\nskills: [a]\n")
    (root / "subagents").mkdir()
    assert profile_migration.plan(root, tmp_path / "user") is None
    assert config.load_config(root).skills == ("a",)
    # A stray file left beside the new layout is never parsed for settings.
    write(root / "skills/skills.yaml", "global_extra: [stale]\n")
    assert config.load_config(root).skills == ("a",)
    assert Path(root / "skills/skills.yaml").is_file()
