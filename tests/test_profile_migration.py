"""Bootstrap merges the retired global settings files into config.yaml version 4."""
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from dotbrain import assets, bootstrap, config, doctor, paths, profile_migration, runtimes


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


def test_existing_selection_without_legacy_entries_is_preserved(tmp_path):
    root = tmp_path / "data"
    write(root / "config.yaml", "version: 4\nsubagents: [existing]\n")
    write(root / "skills/skills.yaml", "global_extra: [collection/example]\n")

    profile_migration.apply(root, profile_migration.plan(root, tmp_path / "user"))

    assert config.load_config(root).subagents == ("existing",)


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
    ({"skills/skills.yaml": "profiles:\n  codex: [~/.a]\n  codex: [~/.b]\n"}, "duplicate"),
    ({"skills/skills.yaml": "- not a mapping\n"}, "mapping"),
    ({"skills/skills.yaml": "global_extra: []\nunknown: 1\n"}, "unknown keys"),
    ({"skills/skills.yaml": "targets:\n  codex: ~/elsewhere/folder\n"}, "does not end in /skills"),
    ({"skills/skills.yaml": "profiles: {hermes: [~/.hermes]}\n"}, "profiles"),
    ({"skills/skills.yaml": "global_extra: [a]\n", "config.yaml": "skills: [b]\n"}, "conflicts"),
    ({"skills/skills.yaml": "global_extra: [a]\n", "config.yaml": "version: 4\nskills: [a, b]\n"}, "conflicts"),
    ({"skills/skills.yaml": "global_extra: [a]\n", "config.yaml": "x: &y 1\n"}, "anchors"),
    ({"agents/agents.yaml": "global: []\n", "agents/claude/a.md": "a", "subagents/claude/b.md": "b"},
     "both agents/ and subagents/"),
    ({"agents/agents.yaml": "global: [a]\n", "subagents/agents.yaml": "global: [b]\n"},
     "both agents/agents.yaml and subagents/agents.yaml"),
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


def test_changed_config_during_pending_cleanup_is_refused_without_writes(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    write(root / paths.GLOBAL_MIGRATION_PENDING, "version: 4\nskills: [a]\n")
    write(root / "config.yaml", "version: 4\nskills: [b]\n")
    before = snapshot(root)

    with pytest.raises(ValueError, match="differs from the unfinished migration"):
        profile_migration.plan(root, user)

    assert snapshot(root) == before
    assert assets.link_global(root, "skills", user_home=user).warnings


def test_locked_retirement_preserves_settings_and_retries(tmp_path, monkeypatch):
    root, user = legacy_root(tmp_path)
    real_unlink = Path.unlink

    def locked(path, *args, **kwargs):
        if path == root / "subagents/agents.yaml":
            raise PermissionError(32, "file is in use")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", locked)
    with pytest.raises(ValueError, match="settings are preserved"):
        profile_migration.apply(root, profile_migration.plan(root, user))
    assert config.load_config(root).skills == ("collection/example",)
    assert config.load_config(root).subagents == ("custom",)
    assert (root / "subagents/agents.yaml").is_file()
    assert assets.link_global(root, "skills", user_home=user).warnings
    assert any("subagents/agents.yaml" in f.message for f in doctor._check_machine(root, user))
    monkeypatch.setattr(Path, "unlink", real_unlink)

    profile_migration.apply(root, profile_migration.plan(root, user))
    assert config.load_config(root).subagents == ("custom",)
    assert profile_migration.plan(root, user) is None


@pytest.mark.parametrize("step", ["pending", "before-config", "config", "rename", "stage-link",
                                  "link", "skills", "agents", "complete"])
def test_process_interruption_retries_without_losing_selections_or_links(tmp_path, step):
    root, user = legacy_root(tmp_path)
    # Exit without exception cleanup: retry must reconstruct its state in a new process.
    script = r'''
import os
import subprocess
import sys
from pathlib import Path
from dotbrain import bootstrap, paths, profile_migration, runtimes
root, user, step = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
runtimes.installed = lambda rt: False
def stop(event):
    if step == event:
        os._exit(77)
replace, unlink, symlink = os.replace, Path.unlink, Path.symlink_to
def interrupted_replace(src, dst):
    dst = Path(dst)
    if dst == root / 'config.yaml':
        stop('before-config')
    replace(src, dst)
    if dst == root / paths.GLOBAL_MIGRATION_PENDING:
        stop('pending')
    elif dst == root / 'config.yaml':
        stop('config')
    elif dst == root / 'subagents':
        stop('rename')
    elif dst == user / '.claude/agents/custom.md':
        stop('link')
def interrupted_unlink(path, *args, **kwargs):
    unlink(path, *args, **kwargs)
    if path == root / 'skills/skills.yaml':
        stop('skills')
    elif path == root / 'subagents/agents.yaml':
        stop('agents')
    elif path == root / paths.GLOBAL_MIGRATION_PENDING:
        stop('complete')
def interrupted_symlink(path, *args, **kwargs):
    symlink(path, *args, **kwargs)
    if path.name.startswith('.custom.md.') and path.name.endswith('.dotbrain-tmp'):
        stop('stage-link')
os.replace, Path.unlink, Path.symlink_to = interrupted_replace, interrupted_unlink, interrupted_symlink
result = bootstrap.prepare(root, 'codex', home=user,
    run=lambda *a, **kw: subprocess.CompletedProcess(a, 0))
raise AssertionError(result)
'''
    stopped = subprocess.run([sys.executable, "-c", script, str(root), str(user), step],
                             capture_output=True, text=True, timeout=30)
    assert stopped.returncode == 77, stopped.stderr
    result = bootstrap.prepare(root, "codex", home=user, run=no_git)

    assert result.status == "success", result
    cfg = config.load_config(root)
    assert cfg.version == 4
    assert cfg.skills == ("collection/example",) and cfg.subagents == ("custom",)
    assert cfg.profiles == {"claude-code": ["~/.claude-work"], "codex": ["~/.codex-work"]}
    assert (user / ".claude/agents/custom.md").read_text() == "custom"
    assert (user / ".codex/skills/example").is_symlink()
    assert not any((root / name).exists() for name in paths.PENDING_MIGRATION_FILES)
    assert profile_migration.plan(root, user) is None
    before = snapshot(root)
    assert bootstrap.prepare(root, "codex", home=user, run=no_git).status == "success"
    assert snapshot(root) == before


@pytest.mark.parametrize("operation", ["symlink", "replace"])
def test_filtered_bootstrap_retries_failed_relink(tmp_path, monkeypatch, operation):
    root, user = legacy_root(tmp_path)
    link = user / ".claude/agents/custom.md"
    foreign = link.with_name(".custom.md.dotbrain-tmp")
    foreign.write_text("operator file", encoding="utf-8")
    real_symlink, real_replace = Path.symlink_to, profile_migration.os.replace

    def denied_symlink(path, *args, **kwargs):
        if path.name.startswith(".custom.md.") and path.name.endswith(".dotbrain-tmp"):
            raise PermissionError("symlink denied")
        return real_symlink(path, *args, **kwargs)

    def denied_replace(src, dst):
        if Path(dst) == link:
            raise PermissionError("replacement denied")
        return real_replace(src, dst)

    with monkeypatch.context() as patch:
        if operation == "symlink":
            patch.setattr(Path, "symlink_to", denied_symlink)
        else:
            patch.setattr(profile_migration.os, "replace", denied_replace)
        failed = bootstrap.prepare(root, "codex", home=user, run=no_git)
    assert failed.status == "failure", failed
    assert link.is_symlink()  # still discoverable even though the source directory moved

    retry = bootstrap.prepare(root, "codex", home=user, run=no_git)
    assert retry.status == "success", retry
    assert link.read_text() == "custom"
    assert link.resolve() == (root / "subagents/claude/custom.md").resolve()
    assert foreign.read_text(encoding="utf-8") == "operator file"
    assert profile_migration.plan(root, user) is None


def test_filtered_bootstrap_repoints_other_runtime_links(tmp_path):
    root, user = legacy_root(tmp_path)
    link = user / ".claude/agents/custom.md"

    result = bootstrap.prepare(root, "codex", home=user, run=no_git)

    assert result.status == "success", result
    assert link.is_symlink() and link.read_text() == "custom"
    assert link.resolve() == (root / "subagents/claude/custom.md").resolve()


def test_filtered_bootstrap_repoints_profiles_already_in_config(tmp_path):
    root, user = legacy_root(tmp_path)
    write(root / "config.yaml", "version: 3\nprofiles: {claude-code: [~/.claude-config]}\n")
    write(root / "skills/skills.yaml", "global_extra: [collection/example]\n")
    link = user / ".claude-config/agents/custom.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(root / "agents/claude/custom.md")

    result = bootstrap.prepare(root, "codex", home=user, run=no_git)

    assert result.status == "success", result
    assert link.read_text() == "custom"
    assert link.resolve() == (root / "subagents/claude/custom.md").resolve()


@pytest.mark.parametrize("runtime,value,hint", [
    ("hermes", "~/hermes-skills", "set HERMES_HOME=<home> instead; global skills then go to <home>/skills"),
    ("opencode", "~/oc", "set XDG_CONFIG_HOME=<home> instead; global skills then go to <home>/opencode/dotbrain/skills"),
    ("pi", "~/pi", "set PI_CODING_AGENT_DIR=<home> instead"),
    ("cursor", "~/cursor-skills", "Cursor global skills always go to"),
])
def test_custom_target_of_other_runtime_is_dropped_with_replacement(tmp_path, runtime, value, hint):
    root = tmp_path / "data"
    write(root / "skills/skills.yaml", f"targets:\n  {runtime}: {value}\nglobal_extra: [a]\n")

    logs = profile_migration.apply(root, profile_migration.plan(root, tmp_path / "user"))

    [line] = [line for line in logs if f"dropped targets.{runtime}" in line]
    assert value in line and hint in line
    assert config.load_config(root).skills == ("a",) and config.load_config(root).profiles == {}


def test_default_target_of_other_runtime_is_dropped(tmp_path, monkeypatch):
    monkeypatch.delenv("HERMES_HOME", raising=False)
    root = tmp_path / "data"
    write(root / "skills/skills.yaml", "targets:\n  hermes: ~/.hermes/skills\n")

    logs = profile_migration.apply(root, profile_migration.plan(root, tmp_path / "user"))

    assert any("dropped targets.hermes" in line for line in logs)
    assert not (root / "skills/skills.yaml").exists()


def test_other_runtime_target_is_dropped_when_its_home_is_rejected(tmp_path, monkeypatch):
    root, user = legacy_root(tmp_path)
    unsafe = tmp_path / "checkout/.hermes"
    (unsafe.parent / ".brain").mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(unsafe))
    write(root / "skills/skills.yaml", "targets: {hermes: ~/old-global-skills}\n")

    result = bootstrap.prepare(root, "codex", home=user, run=no_git)

    assert result.status == "success", result
    assert any("~/old-global-skills" in line and "HERMES_HOME" in line
               for line in result.targets[0].changes)
    errors = []
    targets = assets.global_targets((runtimes.find("hermes"),), "skills", user,
                                    explicit=True, errors=errors, dotbrain_home=root)
    assert targets["hermes"] == () and any("inside a wired checkout" in error for error in errors)
    assert not unsafe.exists()
