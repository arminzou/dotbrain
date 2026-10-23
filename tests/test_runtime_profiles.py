"""Global skill destinations follow runtime homes without touching project links."""
import json
from pathlib import Path

import pytest
import yaml

from dotbrain import assets, doctor, skills


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def configure(root, **settings):
    write(root / "skills/collection/example/SKILL.md", "example")
    write(root / "skills/skills.yaml", yaml.safe_dump({
        "version": 1, "global_extra": ["collection/example"], **settings,
    }))


@pytest.mark.parametrize("runtime,folder", [("claude-code", ".claude"), ("codex", ".codex")])
def test_default_and_profile_homes_receive_global_skills(tmp_path, runtime, folder):
    root, user = tmp_path / "data", tmp_path / "user"
    profile = user / f"{folder}-work"
    profile.mkdir(parents=True)
    configure(root, profiles={runtime: [f"~/{folder}-work"]})

    result = assets.link_global(root, "skills", runtime, user_home=user)

    assert not result.warnings and not result.notices
    for directory in (user / folder, profile):
        link = directory / "skills/example"
        assert link.is_symlink()
        assert link.resolve() == (root / "skills/collection/example").resolve()


def test_missing_profile_is_skipped_silently(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    configure(root, profiles={"claude-code": ["~/.claude-elsewhere"]})

    result = assets.link_global(root, "skills", "claude-code", user_home=user)

    assert not result.warnings and not result.notices
    assert (user / ".claude/skills/example").is_symlink()
    assert not (user / ".claude-elsewhere").exists()


@pytest.mark.parametrize("checkout_name", ["checkout", "sibling-worktree"])
@pytest.mark.parametrize("runtime,folder", [("claude-code", ".claude"), ("codex", ".codex")])
def test_checkout_profile_rejected_without_pruning_links(tmp_path, checkout_name, runtime, folder):
    root, user = tmp_path / "data", tmp_path / "user"
    checkout = tmp_path / checkout_name
    profile = checkout / folder
    configure(root, profiles={runtime: [str(profile)]}, global_extra=[])
    profile.mkdir(parents=True)
    # A broken marker still identifies a checkout, including a detached worktree.
    (checkout / ".brain").symlink_to(tmp_path / "unavailable", target_is_directory=True)
    old = profile / "skills/example"
    old.parent.mkdir()
    old.symlink_to(root / "skills/collection/example", target_is_directory=True)

    with pytest.raises(ValueError, match=rf"profiles\.{runtime}"):
        assets.link_global(root, "skills", runtime, user_home=user)

    assert old.is_symlink()
    assert old.resolve() == (root / "skills/collection/example").resolve()
    assert not (user / folder / "skills").exists()


def test_default_home_redirected_into_checkout_is_rejected(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    checkout = tmp_path / "checkout"
    configure(root, global_extra=[])
    profile = checkout / ".claude"
    profile.mkdir(parents=True)
    (checkout / ".brain").touch()
    user.mkdir()
    (user / ".claude").symlink_to(profile, target_is_directory=True)
    old = profile / "skills/example"
    old.parent.mkdir()
    old.symlink_to(root / "skills/collection/example", target_is_directory=True)

    with pytest.raises(ValueError, match="default claude-code home"):
        assets.link_global(root, "skills", "claude-code", user_home=user)

    assert old.is_symlink()


def test_symlinked_home_ancestor_allows_profile_linking(tmp_path):
    root = tmp_path / "data"
    physical_home = tmp_path / "physical/home"
    physical_home.mkdir(parents=True)
    user = tmp_path / "home"
    user.symlink_to(physical_home, target_is_directory=True)
    (user / ".claude-work").mkdir()
    configure(root, profiles={"claude-code": ["~/.claude-work"]})

    result = assets.link_global(root, "skills", "claude-code", user_home=user)

    assert not result.warnings
    assert (physical_home / ".claude/skills/example").is_symlink()
    assert (physical_home / ".claude-work/skills/example").is_symlink()


@pytest.mark.parametrize("runtime,folder", [("claude-code", ".claude"), ("codex", ".codex")])
def test_legacy_default_target_is_ignored_silently(tmp_path, runtime, folder):
    root, user = tmp_path / "data", tmp_path / "user"
    configure(root, targets={runtime: f"~/{folder}/skills"})

    result = assets.link_global(root, "skills", runtime, user_home=user)

    assert not result.warnings and not result.notices
    assert (user / folder / "skills/example").is_symlink()


def test_legacy_custom_target_migrates_parent_to_profile_with_notice(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    profile = user / ".claude-work"
    profile.mkdir(parents=True)
    configure(root, targets={"claude-code": "~/.claude-work/old-folder"})

    result = assets.link_global(root, "skills", "claude-code", user_home=user)

    assert not result.warnings
    assert len(result.notices) == 1
    assert "targets.claude-code" in result.notices[0]
    assert "profiles.claude-code" in result.notices[0]
    assert (user / ".claude/skills/example").is_symlink()
    assert (profile / "skills/example").is_symlink()
    assert not (profile / "old-folder").exists()


def test_doctor_reports_plugin_installation_for_each_claude_home(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    profile = user / ".claude-work"
    profile.mkdir(parents=True)
    configure(root, profiles={"claude-code": [str(profile)]}, global_extra=[])
    plugin = tmp_path / "plugin"
    write(plugin / "hooks/hooks.json", json.dumps({"hooks": {"SessionStart": [{}]}}))
    write(user / ".claude/plugins/installed_plugins.json", json.dumps({
        "plugins": {"dotbrain@dotbrain": [{"installPath": str(plugin)}]},
    }))
    write(profile / "plugins/installed_plugins.json", '{"plugins": {}}')

    findings = doctor._check_machine(root, user)

    assert any(f.status == "ok" and str(user / ".claude") in f.message
               and "SessionStart hook files" in f.message for f in findings)
    assert any(f.status == "warn" and str(profile) in f.message
               and "SessionStart hook files not found" in f.message for f in findings)


@pytest.mark.parametrize("profiles", [
    ["~/.claude-work"], {"hermes": ["~/.hermes-work"]},
    {"claude-code": "~/.claude-work"}, {"codex": [None]}, {"codex": [""]},
])
def test_invalid_or_unsupported_profiles_name_setting(tmp_path, profiles):
    configure(tmp_path, profiles=profiles)

    with pytest.raises(ValueError, match="profiles"):
        skills.load_global_config(tmp_path / "skills/skills.yaml")
