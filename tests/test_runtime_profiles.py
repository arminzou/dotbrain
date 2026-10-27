"""Global skill destinations follow runtime homes without touching project links."""
import json
from pathlib import Path

import pytest

from conftest import write_global_config
from dotbrain import assets, config, doctor, subagents


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def configure(root, **settings):
    write(root / "skills/collection/example/SKILL.md", "example")
    write_global_config(root, **{"skills": ["collection/example"], **settings})


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
    configure(root, profiles={runtime: [str(profile)]}, skills=[])
    profile.mkdir(parents=True)
    # A broken marker still identifies a checkout, including a detached worktree.
    (checkout / ".brain").symlink_to(tmp_path / "unavailable", target_is_directory=True)
    old = profile / "skills/example"
    old.parent.mkdir()
    old.symlink_to(root / "skills/collection/example", target_is_directory=True)

    result = assets.link_global(root, "skills", runtime, user_home=user)
    assert len(result.warnings) == 1
    assert f"profiles.{runtime}" in result.warnings[0]

    assert old.is_symlink()
    assert old.resolve() == (root / "skills/collection/example").resolve()
    assert (user / folder / "skills").is_dir()


def test_default_home_redirected_into_checkout_is_rejected(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    checkout = tmp_path / "checkout"
    configure(root, skills=[])
    profile = checkout / ".claude"
    profile.mkdir(parents=True)
    (checkout / ".brain").touch()
    user.mkdir()
    (user / ".claude").symlink_to(profile, target_is_directory=True)
    old = profile / "skills/example"
    old.parent.mkdir()
    old.symlink_to(root / "skills/collection/example", target_is_directory=True)

    result = assets.link_global(root, "skills", "claude-code", user_home=user)
    assert len(result.warnings) == 1
    assert "default claude-code home" in result.warnings[0]

    assert old.is_symlink()


def test_checkout_home_cannot_hide_behind_duplicate_skill_destination(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    profile = tmp_path / "checkout/.claude"
    profile.mkdir(parents=True)
    (profile.parent / ".brain").touch()
    default_skills = user / ".claude/skills"
    default_skills.mkdir(parents=True)
    (profile / "skills").symlink_to(default_skills, target_is_directory=True)
    configure(root, profiles={"claude-code": [str(profile)]})

    result = assets.link_global(root, "skills", "claude", user_home=user)

    assert len(result.warnings) == 1
    assert "profiles.claude-code" in result.warnings[0]
    assert (default_skills / "example").is_symlink()


@pytest.mark.parametrize("command", ["bootstrap", "skills"])
def test_rejected_profile_does_not_stop_safe_delivery_or_diagnosis(tmp_path, monkeypatch, command):
    from conftest import set_fake_home
    from typer.testing import CliRunner
    from dotbrain.cli import app

    root, user = tmp_path / "data", tmp_path / "user"
    set_fake_home(monkeypatch, user)
    bad = tmp_path / "checkout/.claude"
    good = user / ".claude-work"
    bad.mkdir(parents=True)
    good.mkdir(parents=True)
    (bad.parent / ".brain").touch()
    # Bootstrap must still reach the subsequent global subagent pass.
    configure(root, profiles={"claude-code": [str(bad), str(good)]}, subagents=["custom"])
    write(root / "subagents/codex/custom.toml", 'name = "custom"\n')
    write(root / "subagents/claude/custom.md", "custom")

    args = [command, "--home", str(root), "--json"]
    if command == "skills":
        args[1:1] = ["link", "--scope", "global"]
    result = CliRunner().invoke(app, args)

    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] in ("failure", "partial")
    assert any("profiles.claude-code" in error for target in payload["targets"] for error in target["errors"])
    for directory in (user / ".claude", user / ".codex", good):
        assert (directory / "skills/example").is_symlink()
    assert not (bad / "skills").exists()
    if command == "bootstrap":
        assert (user / ".codex/agents/custom.toml").is_file()

    findings = doctor._check_machine(root, user)
    assert any(f.status == "error" and "profiles.claude-code" in f.message for f in findings)
    for directory in (user / ".claude", good):
        assert any(str(directory) in f.message and "plugin installation" in f.message for f in findings)
    assert any(str(user / ".codex/skills") in f.message and "healthy" in f.message for f in findings)


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


def test_doctor_reports_plugin_installation_for_each_claude_home(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    profile = user / ".claude-work"
    profile.mkdir(parents=True)
    configure(root, profiles={"claude-code": [str(profile)]}, skills=[])
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
        config.load_config(tmp_path)


@pytest.mark.parametrize("runtime,folder,suffix", [("claude-code", ".claude", ".md"), ("codex", ".codex", ".toml")])
def test_global_agents_use_shared_profiles(tmp_path, runtime, folder, suffix):
    root, user = tmp_path / "data", tmp_path / "user"
    profile = user / f"{folder}-work"
    profile.mkdir(parents=True)
    configure(root, profiles={runtime: [str(profile), str(user / "missing")]}, subagents=["custom"])
    write(root / "subagents/claude/custom.md", "custom")
    write(root / "subagents/codex/custom.toml", 'name = "custom"\n')

    result = assets.link_global(root, "agents", user_home=user)

    assert not result.warnings and not result.notices
    for directory in (user / folder, profile):
        dest = directory / f"agents/custom{suffix}"
        assert dest.is_file()
        if runtime == "claude-code":
            assert dest.is_symlink()
        else:
            assert subagents.is_managed_copy(dest)
    assert not (user / "missing").exists()
    for folder_name in (".hermes", ".opencode", ".pi", ".cursor"):
        assert not (user / folder_name / "agents").exists()

    findings = doctor._check_machine(root, user)
    assert any(str(profile / "agents") in f.message and "healthy" in f.message for f in findings)
    (profile / f"agents/custom{suffix}").unlink()
    findings = doctor._check_machine(root, user)
    assert any(f.status == "error" and str(profile / f"agents/custom{suffix}") in f.message for f in findings)


def test_global_packaged_subagent_is_skipped(tmp_path):
    root, user = tmp_path / "data", tmp_path / "user"
    configure(root, subagents=["reviewer"])

    result = assets.link_global(root, "agents", user_home=user)

    assert not result.warnings and "reviewer" in result.notices[0]
    assert not (user / ".codex/agents/dotbrain-reviewer.toml").exists()
    assert any(f.status == "warn" and "packaged subagents: reviewer" in f.message
               for f in doctor._check_machine(root, user))


@pytest.mark.parametrize("redirect", ["home", "destination", "home-with-external-destination"])
def test_global_agents_reject_checkout_paths_and_continue(tmp_path, redirect):
    root, user = tmp_path / "data", tmp_path / "user"
    checkout = tmp_path / "checkout"
    bad, good = user / ".codex-bad", user / ".codex-good"
    checkout.mkdir()
    good.mkdir(parents=True)
    (checkout / ".brain").symlink_to(tmp_path / "unavailable", target_is_directory=True)
    if redirect == "destination":
        bad.mkdir()
        (bad / "agents").symlink_to(checkout, target_is_directory=True)
    else:
        bad.symlink_to(checkout, target_is_directory=True)
        if redirect == "home-with-external-destination":
            (bad / "agents").symlink_to(good / "agents", target_is_directory=True)
    configure(root, profiles={"codex": [str(bad), str(good)]}, subagents=["custom"])
    write(root / "subagents/codex/custom.toml", 'name = "custom"\n')
    write(root / "subagents/claude/custom.md", "custom")

    result = assets.link_global(root, "agents", user_home=user)

    assert len(result.warnings) == 1
    assert "profiles.codex" in result.warnings[0] and "wired checkout" in result.warnings[0]
    assert subagents.is_managed_copy(user / ".codex/agents/custom.toml")
    assert subagents.is_managed_copy(good / "agents/custom.toml")
    assert not (checkout / "custom.toml").exists()
    if redirect != "home-with-external-destination":
        assert not (checkout / "agents/custom.toml").exists()
    assert any(f.status == "error" and "agents" in f.message and "profiles.codex" in f.message
               for f in doctor._check_machine(root, user))
