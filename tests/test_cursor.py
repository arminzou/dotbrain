"""Isolated Cursor discovery-path and owned-delivery contracts; no native sessions."""
import json
import shutil
from pathlib import Path

import pytest
import yaml

from dotbrain import assets, claude_plugins, cursor, doctor, resource_loader


def skill(root, name="example"):
    target = root / name
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(f"---\nname: {name}\ndisable-model-invocation: true\n---\nBody\n", encoding="utf-8")
    (target / "reference.md").write_text("Supporting file", encoding="utf-8")
    return target


def test_global_delivery_and_native_invocation_metadata(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    result = assets.link_global(dotbrain_home, "skills", "cursor", user_home=user)
    assert not result.warnings
    assert cursor.state(dotbrain_home) == "current"
    visible = cursor.discovered(user)
    with resource_loader.plugin_tree() as source:
        for name in cursor.sources(dotbrain_home, ()):
            delivered = user / ".cursor/skills" / name
            assert visible[name] == {delivered.resolve()}
            assert (delivered / "SKILL.md").read_bytes() == (source / "skills" / name / "SKILL.md").read_bytes()
            policy = yaml.safe_load((source / "skills" / name / "agents/openai.yaml").read_text(encoding="utf-8"))
            frontmatter = yaml.safe_load((delivered / "SKILL.md").read_text(encoding="utf-8").split("---")[1])
            assert frontmatter.get("disable-model-invocation", False) is not (policy.get("policy") or {}).get("allow_implicit_invocation", True)
    assert (user / ".cursor/skills/run-execution/references/cursor.md").is_file()
    assert not (user / ".cursor/agents").exists()
    assert not (user / ".cursor/hooks.json").exists()
    assert assets.link_global(dotbrain_home, "skills", "cursor", user_home=user).linked == []
    assert not doctor._check_cursor_skills(dotbrain_home, (), (user,))


@pytest.mark.parametrize("relative", cursor.ROOTS[1:])
def test_existing_discovery_avoids_another_link(dotbrain_home, tmp_path, relative):
    user = tmp_path / "user"
    source = skill(dotbrain_home / "skills")
    existing = user / relative / "example"
    existing.parent.mkdir(parents=True)
    existing.symlink_to(source, target_is_directory=True)
    result = cursor.deliver(dotbrain_home, user / ".cursor/skills", ("example",), scopes=(user,))
    assert not result.warnings
    assert not (user / ".cursor/skills/example").exists()
    assert cursor.discovered(user)["example"] == {source.resolve()}


def test_global_selected_update_prune_and_foreign_entries(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    source = skill(dotbrain_home / "skills")
    config = dotbrain_home / "skills/skills.yaml"
    config.write_text("global_extra: [example]\n", encoding="utf-8")
    assets.link_global(dotbrain_home, "skills", "cursor", user_home=user)
    dest = user / ".cursor/skills/example"
    assert (dest / "reference.md").read_text() == "Supporting file"
    (source / "reference.md").write_text("Updated")
    assert (dest / "reference.md").read_text() == "Updated"
    foreign = skill(user / ".cursor/skills", "foreign")
    bundle = cursor.plugin_dir(dotbrain_home)
    (bundle / "skills/run-execution/SKILL.md").write_text("damaged")
    assert cursor.state(dotbrain_home) == "stale"
    assert any("stale" in f.message for f in doctor._check_home_plugin(assets.runtimes.find("cursor"), dotbrain_home))
    config.write_text("global_extra: []\n", encoding="utf-8")
    result = assets.link_global(dotbrain_home, "skills", "cursor", user_home=user)
    assert ".cursor/skills/example" in result.pruned
    assert not dest.exists() and foreign.is_dir()
    assert cursor.state(dotbrain_home) == "current"
    (bundle / "skills/obsolete").mkdir()
    (bundle / "skills/obsolete/SKILL.md").write_text("obsolete")
    assert cursor.state(dotbrain_home) == "stale"
    assets.link_global(dotbrain_home, "skills", "cursor", user_home=user)
    assert not (bundle / "skills/obsolete").exists()


def test_foreign_collision_and_duplicate_diagnosis(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    skill(dotbrain_home / "skills")
    first = skill(user / ".claude/skills")
    second = skill(user / ".codex/skills")
    result = cursor.deliver(dotbrain_home, user / ".cursor/skills", ("example",), scopes=(user,))
    assert any("foreign or duplicate skill example" in warning for warning in result.warnings)
    assert not (user / ".cursor/skills/example").exists()
    messages = [f.message for f in doctor._check_cursor_skills(dotbrain_home, ("example",), (user,))]
    assert any("duplicate skill example" in message for message in messages)
    assert any("foreign skill example" in message for message in messages)
    shutil.rmtree(second)
    second.symlink_to(first, target_is_directory=True)
    assert not any("duplicate" in f.message for f in doctor._check_cursor_skills(dotbrain_home, (), (user,)))


def test_foreign_bundle_is_preserved_and_diagnosed(dotbrain_home, tmp_path):
    target = cursor.plugin_dir(dotbrain_home)
    target.mkdir(parents=True)
    (target / "mine").write_text("keep")
    result = assets.link_global(dotbrain_home, "skills", "cursor", user_home=tmp_path / "user")
    assert result.warnings
    assert [p.name for p in target.iterdir()] == ["mine"]
    assert not (tmp_path / "user/.cursor/skills/run-execution").exists()
    findings = doctor._check_home_plugin(assets.runtimes.find("cursor"), dotbrain_home)
    assert any("not dotbrain's" in f.message for f in findings)


def test_reconciliation_preserves_links_into_an_unowned_cursor_cache(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    foreign = skill(cursor.plugin_dir(dotbrain_home), "mine")
    receiver = user / ".cursor/skills"
    receiver.mkdir(parents=True)
    link = receiver / "mine"
    link.symlink_to(foreign, target_is_directory=True)
    result = cursor.deliver(dotbrain_home, receiver, (), scopes=(user,))
    assert not result.pruned
    assert link.is_symlink() and link.resolve() == foreign.resolve()
    assert (link / "reference.md").read_text() == "Supporting file"
    assert not cursor.owned(dotbrain_home)


@pytest.mark.parametrize("project_scope", [False, True])
@pytest.mark.parametrize("already_delivered", [False, True])
def test_enabled_claude_plugin_supplies_packaged_skills(dotbrain_home, tmp_path, project_scope, already_delivered):
    user = tmp_path / "user"
    checkout = tmp_path / "checkout"
    scopes = (checkout, user) if project_scope else (user,)
    receiver = (checkout if project_scope else user) / ".cursor/skills"
    if already_delivered:
        cursor.deliver(dotbrain_home, receiver, (), scopes=scopes)
        assert (receiver / "run-execution").is_symlink()
    installation = user / ".claude/plugins/cache/dotbrain"
    with resource_loader.plugin_tree() as source:
        shutil.copytree(source / "skills", installation / "skills")
    registry = user / ".claude/plugins/installed_plugins.json"
    registry.write_text(json.dumps({"plugins": {"dotbrain@dotbrain": [
        {"scope": "user", "installPath": str(installation)}]}}), encoding="utf-8")
    settings = user / ".claude/settings.json"
    settings.write_text(json.dumps({"enabledPlugins": {"dotbrain@dotbrain": True}}), encoding="utf-8")

    result = cursor.deliver(dotbrain_home, receiver, (), scopes=scopes)
    assert not result.warnings
    assert not list(receiver.iterdir())
    visible = cursor.discovered(*scopes)
    for name in cursor.sources(dotbrain_home, ()):
        assert visible[name] == {(installation / "skills" / name).resolve()}
    assert not doctor._check_cursor_skills(dotbrain_home, (), scopes)
    assert (installation / "skills/run-execution/references/cursor.md").is_file()

    # A separate copy is a native duplicate even when it came from the same plugin source.
    shutil.copytree(installation / "skills/run-execution", receiver / "run-execution")
    findings = doctor._check_cursor_skills(dotbrain_home, (), scopes)
    assert any("duplicate skill run-execution" in f.message for f in findings)
    assert not cursor.deliver(dotbrain_home, receiver, (), scopes=scopes).pruned
    assert (receiver / "run-execution").is_dir()


@pytest.mark.parametrize("enabled", [False, None])
def test_disabled_or_unselected_claude_plugin_is_not_discovered(dotbrain_home, tmp_path, enabled):
    user = tmp_path / "user"
    installation = user / ".claude/plugins/cache/example"
    skill(installation / "skills")
    (user / ".claude/plugins/installed_plugins.json").write_text(json.dumps({"plugins": {
        "example@market": {"installPath": str(installation)}}}), encoding="utf-8")
    (user / ".claude/settings.json").write_text(json.dumps({"enabledPlugins": {
        "example@market": enabled}}), encoding="utf-8")
    assert "example" not in cursor.discovered(user)
    assert not cursor.deliver(dotbrain_home, user / ".cursor/skills", (), scopes=(user,)).warnings
    assert (user / ".cursor/skills/run-execution").is_symlink()


@pytest.mark.parametrize(("entries", "user_enabled", "project_enabled", "local_enabled", "expected"), [
    (("user",), False, True, None, None),
    (("project",), True, None, None, None),
    (("project",), None, True, None, "project"),
    (("local",), None, None, True, "local"),
    (("user", "project", "local"), True, True, None, "project"),
    (("user", "local", "project"), True, True, None, "local"),
    (("user", "project"), True, False, None, None),
    (("user", "project"), False, True, None, "project"),
    (("user",), True, None, False, None),
    (("user", "unrelated"), True, True, None, "user"),
    (("unrelated",), False, True, None, None),
    (("user",), True, False, True, "user"),
    (("project", "user"), True, True, False, None),
    (("user", "second-user"), True, None, None, "user"),
    (("project", "local"), None, None, True, "project"),
])
def test_cursor_plugin_scope_selection(tmp_path, entries, user_enabled, project_enabled, local_enabled, expected):
    user, checkout = tmp_path / "user", tmp_path / "checkout"
    installs = []
    for name in entries:
        entry = {"scope": "user" if name == "second-user" else name, "installPath": str(tmp_path / name)}
        if name in ("project", "local", "unrelated"):
            entry.update(scope="local" if name == "local" else "project",
                         projectPath=str((checkout if name != "unrelated" else tmp_path / "other").resolve()))
        installs.append(entry)
    registry = user / ".claude/plugins/installed_plugins.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"plugins": {"example@market": installs}}), encoding="utf-8")
    for scope, filename, enabled in ((user, "settings.json", user_enabled),
                                     (checkout, "settings.json", project_enabled),
                                     (checkout, "settings.local.json", local_enabled)):
        if enabled is None:
            continue
        path = scope / ".claude" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"enabledPlugins": {"example@market": enabled}}), encoding="utf-8")
    assert claude_plugins.enabled_installs((checkout, user)) == (
        [("example@market", tmp_path / expected)] if expected else [])


@pytest.mark.parametrize("disabled", [False, True])
def test_cursor_plugin_selection_across_workspaces(tmp_path, disabled):
    user, first, second = (tmp_path / name for name in ("user", "first", "second"))
    registry = user / ".claude/plugins/installed_plugins.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"plugins": {"example@market": [
        {"scope": "user", "installPath": str(tmp_path / "user-install")},
        {"scope": "project", "projectPath": str(second.resolve()), "installPath": str(tmp_path / "project-install")}
    ]}}), encoding="utf-8")
    (user / ".claude/settings.json").write_text(json.dumps({"enabledPlugins": {"example@market": True}}), encoding="utf-8")
    settings = second / ".claude/settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"enabledPlugins": {"example@market": not disabled}}), encoding="utf-8")
    assert claude_plugins.enabled_installs((first, second, user)) == (
        [] if disabled else [("example@market", tmp_path / "user-install")])


def test_cursor_ignores_user_local_enablement_and_project_registries(tmp_path):
    user, checkout = tmp_path / "user", tmp_path / "checkout"
    for scope in (user, checkout):
        registry = scope / ".claude/plugins/installed_plugins.json"
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({"plugins": {"example@market": [
            {"scope": "user", "installPath": str(scope / "installation")}]}}), encoding="utf-8")
        (scope / ".claude/settings.local.json").write_text(
            json.dumps({"enabledPlugins": {"example@market": True}}), encoding="utf-8")
    assert claude_plugins.enabled_installs((checkout, user)) == []


def test_missing_delivery_and_no_agents(dotbrain_home, tmp_path):
    findings = doctor._check_home_plugin(assets.runtimes.find("cursor"), dotbrain_home)
    assert any("not delivered" in f.message for f in findings)
    assert any("delivery is missing" in f.message for f in doctor._check_cursor_skills(dotbrain_home, (), (tmp_path,)))
    with pytest.raises(ValueError, match="no native subagent delivery"):
        assets.link_global(dotbrain_home, "agents", "cursor", user_home=tmp_path)


def test_global_opt_in_and_doctor_survive_bundle_refresh(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    source = skill(dotbrain_home / "skills")
    (dotbrain_home / "skills/skills.yaml").write_text("global_extra: [example]\n", encoding="utf-8")
    assets.link_global(dotbrain_home, "skills", "cursor", user_home=user)
    assert cursor.global_delivery(dotbrain_home)
    (user / ".cursor/skills/example").unlink()
    assert any("skill example delivery is missing" in f.message for f in doctor._check_machine(dotbrain_home, user))
    (cursor.plugin_dir(dotbrain_home) / "skills/stray").write_text("stale")
    assets.link_global(dotbrain_home, "skills", user_home=user)
    assert cursor.global_delivery(dotbrain_home)
    assert cursor.state(dotbrain_home) == "current"
    assert (user / ".claude/skills/example").resolve() == source.resolve()
    assert not (user / ".cursor/skills/example").exists()
    assert not [f for f in doctor._check_machine(dotbrain_home, user) if f.status == "error"]


def test_skill_identity_and_reconciliation_across_roots(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    source = skill(dotbrain_home / "skills")
    source.rename(source.with_name("folder"))
    source = source.with_name("folder")
    receiver = user / ".cursor/skills"
    assert not cursor.deliver(dotbrain_home, receiver, ("folder",), scopes=(user,)).warnings
    assert (receiver / "example").resolve() == source.resolve()
    assert not cursor.deliver(dotbrain_home, receiver, ("folder",), scopes=(user,)).warnings
    elsewhere = user / ".codex/skills/another-folder"
    elsewhere.parent.mkdir(parents=True)
    elsewhere.symlink_to(source, target_is_directory=True)
    assert ".cursor/skills/example" in cursor.deliver(dotbrain_home, receiver, ("folder",), scopes=(user,)).pruned
    assert not (receiver / "example").exists()
    assert cursor.discovered(user)["example"] == {source.resolve()}


def test_packaged_name_collision_fails_before_writes(dotbrain_home, tmp_path):
    skill(dotbrain_home / "skills", "run-execution")
    with pytest.raises(ValueError, match="destination collision"):
        cursor.deliver(dotbrain_home, tmp_path / "receiver", ("run-execution",), scopes=(tmp_path,))
    assert not cursor.owned(dotbrain_home)
    assert not (tmp_path / "receiver").exists()
