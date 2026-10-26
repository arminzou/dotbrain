"""Bootstrap config migration preserves delivery and the operator's original text."""
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from dotbrain import assets, bootstrap, doctor, profile_migration, runtimes, skills, subagents


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def destinations(root, user):
    cfg = skills.load_global_config(root / "skills/skills.yaml")
    result = {}
    for kind, current in (("skills", cfg), ("agents", subagents.load_global_config(root))):
        errors = []
        result[kind] = assets.global_targets(current.targets, runtimes.select("all"), kind, user,
                                             explicit=False, errors=errors, dotbrain_home=root,
                                             profiles=cfg.profiles)
        assert errors == []
    return result


def test_bootstrap_migrates_once_with_byte_exact_backup(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    original = (
        "# personal settings\r\nversion: 1\r\n"
        "targets: # old defaults\r\n"
        "  # keep this explanation\r\n"
        "  claude-code: ~/.claude/skills # Claude\r\n"
        "  codex: '~\\.codex\\skills' # Codex\r\n"
        "global_extra: [collection/example] # keep selection\r\n"
        "future_setting: {enabled: true}\r\n"
    )
    path = root / "skills/skills.yaml"
    write(path, original)
    write(root / "skills/collection/example/SKILL.md", "example")
    before = destinations(root, user)
    result = bootstrap.ensure_data_root(root, user_home=user,
                                        run=lambda *args, **kwargs: subprocess.CompletedProcess(args, 0))

    assert destinations(root, user) == before
    data = yaml.safe_load(path.read_bytes())
    assert data == {"version": 1, "profiles": {}, "global_extra": ["collection/example"],
                    "future_setting": {"enabled": True}}
    for comment in ("# personal settings", "# old defaults", "# keep this explanation",
                    "# Claude", "# Codex", "# keep selection"):
        assert comment.encode() in path.read_bytes()
    assert path.read_bytes().replace(b"\r\n", b"").count(b"\n") == 0
    backups = list((root / ".cache/config-backups").glob("*.yaml"))
    assert len(backups) == 1 and backups[0].read_bytes() == original.encode()
    assert sum("migrated skills/skills.yaml" in log for log in result.logs) == 1
    second = bootstrap.ensure_data_root(root, user_home=user)
    assert not any("migrated" in log for log in second.logs)
    assert len(list(backups[0].parent.iterdir())) == 1


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("text", [
    "", "# empty", "---\n# empty\n...\n", "{}",
    "{version: 1, global_extra: []}",
    "  version: 1\n  global_extra: []\n",
    "version: 1\nglobal_extra: []\n...",
])
def test_profiles_initialization_preserves_yaml_layout(tmp_path, text, newline):
    root = tmp_path / "data"
    path = root / "skills/skills.yaml"
    write(path, text.replace("\n", newline))
    migration = profile_migration.plan(root, tmp_path / "user")
    assert migration is not None
    profile_migration.apply(root, migration)
    assert skills.load_global_config(path).profiles == {}
    assert profile_migration.plan(root, tmp_path / "user") is None


@pytest.mark.parametrize("override", [None, "CODEX_HOME", "CLAUDE_CONFIG_DIR"])
def test_custom_profiles_and_agents_only_targets_do_not_change_delivery(tmp_path, monkeypatch, override):
    root, user = tmp_path / "data", tmp_path / "user"
    (user / ".codex-work").mkdir(parents=True)
    (user / ".codex-agents-only").mkdir()
    if override:
        monkeypatch.setenv(override, str(user / ".relocated"))
    path = root / "skills/skills.yaml"
    write(path, "targets:\n  claude-code: ~/.claude/skills\n"
                "  codex: ~/.codex-work/old-skills\n"
                "profiles:\n  codex: [~/.codex-work, ~/.missing-profile, ~/.codex-work]\n"
                "global_extra: []\n")
    agents = root / "agents/agents.yaml"
    agent_text = "targets:\n  codex: ~/.codex-agents-only/agents\nglobal: []\n"
    write(agents, agent_text)
    before = destinations(root, user)
    migration = profile_migration.plan(root, user)
    profile_migration.apply(root, migration)
    assert destinations(root, user) == before
    assert agents.read_text() == agent_text
    assert skills.load_global_config(path).profiles["codex"] == [
        "~/.codex-work", "~/.missing-profile", "~/.codex-work"]
    assert yaml.safe_load(path.read_text())["targets"] == {"codex": "~/.codex-work/old-skills"}
    assert not (user / ".missing-profile").exists()
    skill_paths = before["skills"]["codex"]
    assert user / ".codex-agents-only/skills" not in skill_paths
    result = assets.link_global(root, "agents", "codex", user_home=user)
    assert "both skills and agents" in result.notices[0]
    assert "retained" in result.notices[0]


@pytest.mark.parametrize("target", ["absolute", "windows", "flow", "anchor", "duplicate", "multiline"])
def test_ambiguous_default_targets_are_retained(tmp_path, target):
    root, user = tmp_path / "data", tmp_path / "user"
    path = root / "skills/skills.yaml"
    value = str(user / ".codex/skills").replace("\\", "/")
    texts = {
        "absolute": f"targets:\n  codex: '{value}'\n",
        "windows": "targets:\n  codex: 'C:\\OtherMachine\\.codex\\skills'\n",
        "flow": "targets: {codex: ~/.codex/skills} # inline\n",
        "anchor": "targets:\n  codex: &default ~/.codex/skills\nfuture: *default\n",
        "duplicate": "targets:\n  codex: ~/.codex/skills\n  codex: ~/.codex/skills\n",
        "multiline": "targets:\n  codex:\n    # retain this\n    ~/.codex/skills\n",
    }
    write(path, texts[target])
    migration = profile_migration.plan(root, user)
    assert migration.updated.startswith(migration.original)
    before = destinations(root, user)
    profile_migration.apply(root, migration)
    assert destinations(root, user) == before
    assert yaml.safe_load(path.read_text())["targets"] == yaml.safe_load(texts[target])["targets"]


@pytest.mark.parametrize("filename,text", [
    ("skills/skills.yaml", "targets: [broken]\n"),
    ("skills/skills.yaml", "targets: {codex: [broken}\n"),
    ("skills/skills.yaml", "profiles: {hermes: [~/.hermes]}\n"),
    ("skills/skills.yaml", "false\n"),
    ("skills/skills.yaml", "global_extra: [missing/skill]\n"),
    ("agents/agents.yaml", "targets: [broken]\n"),
    ("agents/agents.yaml", "global: [missing-agent]\n"),
])
def test_invalid_configuration_leaves_entire_home_unchanged(tmp_path, filename, text):
    root = tmp_path / "data"
    write(root / "skills/skills.yaml", "version: 1\n")
    write(root / filename, text)
    before = snapshot(root)
    with pytest.raises((ValueError, yaml.YAMLError)):
        bootstrap.ensure_data_root(root, user_home=tmp_path / "user",
                                    run=lambda *args, **kwargs: pytest.fail("preflight ran git"))
    assert snapshot(root) == before


def test_unsafe_profile_leaves_configuration_unchanged(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    checkout = tmp_path / "checkout"
    (checkout / ".codex").mkdir(parents=True)
    (checkout / ".brain").mkdir()
    write(root / "skills/skills.yaml", yaml.safe_dump({
        "targets": {"codex": "~/.codex/skills"},
        "profiles": {"codex": [str(checkout / ".codex")]},
    }))
    before = snapshot(root)
    with pytest.raises(ValueError, match="wired checkout"):
        bootstrap.ensure_data_root(root, user_home=user)
    assert snapshot(root) == before


@pytest.mark.parametrize("interruption", ["replace", "edited"])
def test_interrupted_write_retains_current_file_and_recovery_copy(tmp_path, monkeypatch, interruption):
    root = tmp_path / "data"
    path = root / "skills/skills.yaml"
    write(path, "version: 1\n")
    migration = profile_migration.plan(root, tmp_path / "user")
    if interruption == "replace":
        def fail(*args):
            raise OSError("simulated replacement failure")
        monkeypatch.setattr(os, "replace", fail)
        expected = migration.original
    else:
        write(path, "version: 1\n# edited meanwhile\n")
        expected = path.read_bytes()
    with pytest.raises((OSError, ValueError)):
        profile_migration.apply(root, migration)
    assert path.read_bytes() == expected
    assert not list(path.parent.glob(".skills-*.tmp"))
    backup, = (root / ".cache/config-backups").glob("*.yaml")
    assert backup.read_bytes() == migration.original


def test_doctor_recommends_bootstrap_without_writing(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    write(root / "skills/skills.yaml", "targets:\n  codex: ~/.codex/skills\n")
    before = snapshot(root)
    findings = doctor._check_machine(root, user)
    assert any("profile configuration can be migrated" in f.message and
               "dotbrain bootstrap" in f.suggestion for f in findings)
    assert snapshot(root) == before


def test_current_config_keeps_safe_delivery_when_agents_config_is_invalid(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    write(root / "skills/skills.yaml", "profiles: {}\nglobal_extra: [collection/example]\n")
    write(root / "skills/collection/example/SKILL.md", "example")
    write(root / "agents/agents.yaml", "targets: [invalid]\n")
    result = bootstrap.prepare(root, home=user,
                               run=lambda *args, **kwargs: subprocess.CompletedProcess(args, 0))
    assert result.status == "partial"
    assert (user / ".codex/skills/example").is_symlink()
    assert any("targets must be a mapping" in error for target in result.targets for error in target.errors)


@pytest.mark.parametrize("runtime,directory,filename", [
    ("claude", ".claude", "claude/custom.md"),
    ("codex", ".codex", "codex/custom.toml"),
])
def test_migration_allows_agents_defined_only_for_selected_runtime(tmp_path, runtime, directory, filename):
    root, user = tmp_path / "data", tmp_path / "user"
    write(root / "skills/skills.yaml", "global_extra: [collection/example]\n")
    write(root / "skills/collection/example/SKILL.md", "example")
    write(root / "agents/agents.yaml", "global: [custom]\n")
    write(root / "agents" / filename, 'description = "custom"\n')
    assert not assets.link_global(root, "agents", runtime, user_home=user).warnings

    findings = doctor._check_machine(root, user)
    result = bootstrap.prepare(root, runtime, home=user,
                               run=lambda *args, **kwargs: subprocess.CompletedProcess(args, 0))
    assert result.status == "success", result
    assert not any("global profile migration:" in finding.message for finding in findings)
    assert yaml.safe_load((root / "skills/skills.yaml").read_text())["profiles"] == {}
    assert (user / directory / "skills/example").is_symlink()
    assert (user / directory / "agents" / Path(filename).name).is_file()


def test_config_symlink_is_preserved(tmp_path):
    root = tmp_path / "data"
    source = root / "shared/config.yaml"
    write(source, "version: 1\n")
    path = root / "skills/skills.yaml"
    path.parent.mkdir()
    path.symlink_to(source)
    profile_migration.apply(root, profile_migration.plan(root, tmp_path / "user"))
    assert path.is_symlink()
    assert yaml.safe_load(source.read_text()) == {"version": 1, "profiles": {}}
