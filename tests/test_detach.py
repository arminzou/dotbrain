"""Machine delivery removal never reaches project checkouts or foreign entries."""
import json
import subprocess

import pytest
from typer.testing import CliRunner

from conftest import set_fake_home
from dotbrain import assets, bootstrap, cursor, doctor, hermes, opencode, owned_copy, runtimes, skills, workflows
from dotbrain.cli import app


@pytest.mark.parametrize("runtime", tuple(assets.HOME_DELIVERY))
def test_legacy_detach_all_ends_first_run(dotbrain_home, fake_home, monkeypatch, runtime):
    run = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name in assets.HOME_DELIVERY)
    module = assets.HOME_DELIVERY[runtime]
    directory = dotbrain_home if runtime == "cursor" else runtimes.user_dir(runtimes.find(runtime), fake_home)
    assert not assets.link_global(dotbrain_home, "skills", runtime, user_home=fake_home, run=run).warnings
    assert module.owned(directory)
    marker = dotbrain_home / ".cache/bootstrap-complete"
    assert not marker.exists()

    detached = workflows.detach_runtime(dotbrain_home, "all", home=fake_home, run=run)
    assert detached.status == "success", detached
    assert marker.is_file()
    result = bootstrap.prepare(dotbrain_home, home=fake_home, run=run)
    assert result.status == "success", result
    for name, adapter in assets.HOME_DELIVERY.items():
        receiver = dotbrain_home if name == "cursor" else runtimes.user_dir(runtimes.find(name), fake_home)
        assert not adapter.owned(receiver)
        assert f"dotbrain bootstrap --runtime {name}" in str(result)


@pytest.mark.parametrize("runtime", runtimes.RUNTIMES)
def test_detach_removes_only_owned_delivery(runtime, dotbrain_home, fake_home, tmp_path, monkeypatch):
    set_fake_home(monkeypatch, fake_home)
    for variable in ("HERMES_HOME", "XDG_CONFIG_HOME", "PI_CODING_AGENT_DIR"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(hermes.shutil, "which", lambda _: None)
    rt = runtimes.find(runtime)
    directory = runtimes.user_dir(rt, fake_home)
    module = assets.HOME_DELIVERY.get(runtime)
    receiver = module.skills_dir(directory) if rt.home_env else fake_home / rt.workspace / "skills"
    source = dotbrain_home / "skills/misc/discovery-test"
    receiver.mkdir(parents=True)
    (receiver / "owned").symlink_to(source, target_is_directory=True)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (receiver / "foreign").symlink_to(foreign, target_is_directory=True)
    (receiver / "user-file").write_text("keep")
    other = directory / "plugins/other"
    other.mkdir(parents=True)
    (other / "data").write_text("keep")
    checkout = tmp_path / "checkout/.cursor/skills"
    checkout.mkdir(parents=True)
    (checkout / "owned").symlink_to(source, target_is_directory=True)
    legacy = dotbrain_home / ".cache/skills/legacy"
    legacy.mkdir(parents=True)
    (checkout / "legacy").symlink_to(legacy, target_is_directory=True)
    if rt.home_env:
        module.deliver(directory, run=lambda *a, **kw: None)
    elif runtime == "cursor":
        cursor.deliver(dotbrain_home, receiver, (), scopes=(fake_home,), global_scope=True)
        bundle = cursor.plugin_dir(dotbrain_home)
        (receiver / "bundle").symlink_to(bundle / "skills", target_is_directory=True)
        cursor.reconcile_hooks(fake_home)
        hooks = fake_home / ".cursor/hooks.json"
        data = json.loads(hooks.read_text())
        data["hooks"].setdefault("sessionStart", []).append({"command": "foreign"})
        hooks.write_text(json.dumps(data))
    else:
        marketplace = directory / "plugins/dotbrain"
        marketplace.mkdir()
        (marketplace / "data").write_text("marketplace")

    result = workflows.detach_runtime(dotbrain_home, runtime, home=fake_home)
    assert (dotbrain_home / ".cache/bootstrap-complete").is_file()
    assert result.status == "success"
    assert result.targets[0].changes
    if runtime == "hermes":
        assert "not on PATH" in result.targets[0].findings[0]["message"]
    assert not (receiver / "owned").is_symlink()
    assert (receiver / "foreign").is_symlink()
    assert (receiver / "user-file").read_text() == "keep"
    assert (other / "data").read_text() == "keep"
    assert (checkout / "owned").is_symlink()
    assert (checkout / "legacy").is_dir()
    if runtime == "cursor":
        assert not bundle.exists()
        assert not (receiver / "bundle").is_symlink()
        assert json.loads(hooks.read_text())["hooks"] == {"sessionStart": [{"command": "foreign"}]}
    elif runtime == "opencode":
        assert not opencode.plugin_file(directory).exists()
        assert not opencode.packaged_dir(directory).exists()
    elif rt.home_env:
        assert not module.plugin_dir(directory).exists()
    else:
        assert (marketplace / "data").read_text() == "marketplace"
        assert "plugin" in result.targets[0].findings[0]["message"]
    again = workflows.detach_runtime(dotbrain_home, runtime, home=fake_home)
    assert again.status == "success"
    assert again.targets[0].changes == []
    assert "nothing to remove" in again.targets[0].findings[-1]["message"]


@pytest.mark.parametrize("runtime", ("hermes", "opencode", "pi", "cursor"))
def test_detach_preserves_foreign_delivery(runtime, dotbrain_home, fake_home, monkeypatch):
    set_fake_home(monkeypatch, fake_home)
    for variable in ("HERMES_HOME", "XDG_CONFIG_HOME", "PI_CODING_AGENT_DIR"):
        monkeypatch.delenv(variable, raising=False)
    module = assets.HOME_DELIVERY[runtime]
    directory = runtimes.user_dir(runtimes.find(runtime), fake_home)
    bundle = (opencode.packaged_dir(directory) if runtime == "opencode" else
              module.plugin_dir(dotbrain_home if runtime == "cursor" else directory))
    bundle.mkdir(parents=True)
    (bundle / "foreign").write_text("keep")
    if runtime == "opencode":
        plugin = opencode.plugin_file(directory)
        plugin.parent.mkdir(parents=True)
        plugin.write_text("foreign")
    result = workflows.detach_runtime(dotbrain_home, runtime, home=fake_home)
    assert result.status == "success"
    assert not result.targets[0].changes
    assert (bundle / "foreign").read_text() == "keep"
    if runtime == "opencode":
        assert plugin.read_text() == "foreign"


@pytest.mark.parametrize("failure", (None, FileNotFoundError(), subprocess.CalledProcessError(1, "hermes")))
def test_hermes_disable_is_best_effort(dotbrain_home, fake_home, monkeypatch, failure):
    directory = fake_home / "relocated"
    monkeypatch.setenv("HERMES_HOME", str(directory))
    monkeypatch.setattr(hermes.shutil, "which", lambda _: "hermes")
    target = hermes.plugin_dir(directory)
    target.mkdir(parents=True)
    (target / owned_copy.MARKER).touch()
    calls = []

    def run(argv, **kwargs):
        assert target.exists()  # Hermes needs the plugin present when disabling it.
        calls.append((argv, kwargs))
        if failure:
            raise failure

    result = workflows.detach_runtime(dotbrain_home, "hermes", home=fake_home, run=run)
    assert result.status == "success"
    assert not target.exists()
    assert calls[0][0] == ["hermes", "plugins", "disable", "dotbrain"]
    assert calls[0][1]["env"]["HERMES_HOME"] == str(directory)
    assert bool(result.targets[0].findings) == bool(failure)


def test_detach_all_json_and_required_runtime(dotbrain_home, fake_home, monkeypatch):
    set_fake_home(monkeypatch, fake_home)
    for variable in ("HERMES_HOME", "XDG_CONFIG_HOME", "PI_CODING_AGENT_DIR"):
        monkeypatch.delenv(variable, raising=False)
    runner = CliRunner()
    missing = runner.invoke(app, ["detach", "--json"])
    assert missing.exit_code == 2
    assert "runtime" in json.loads(missing.stdout)["errors"][0]
    result = runner.invoke(app, ["detach", "--runtime", "all", "--home", str(dotbrain_home), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["command"] == "detach"
    assert data["status"] == "success"
    assert {t["data"]["runtime"] for t in data["targets"]} == set(runtimes.RUNTIMES)
    assert all(t["scope"] == "global" and t["changes"] == [] for t in data["targets"])
    text = runner.invoke(app, ["detach", "--runtime", "all", "--home", str(dotbrain_home)])
    assert text.exit_code == 0
    assert all(rt.label in text.stdout for rt in runtimes.RUNTIMES.values())


def test_detach_cursor_receiver_and_empty_hooks(dotbrain_home, fake_home, tmp_path):
    dest = fake_home / ".cursor/skills"
    dest.mkdir(parents=True)
    (dest / "owned").symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)
    cursor.reconcile_hooks(fake_home)
    result = workflows.detach_runtime(dotbrain_home, "cursor", home=fake_home)
    assert result.status == "success"
    assert not (dest / "owned").is_symlink()
    assert not (fake_home / ".cursor/hooks.json").exists()


@pytest.mark.parametrize("runtime", ("hermes", "opencode", "pi", "cursor"))
def test_detach_opts_machine_out_until_explicit_bootstrap(runtime, dotbrain_home, fake_home, monkeypatch):
    set_fake_home(monkeypatch, fake_home)
    for variable in ("HERMES_HOME", "XDG_CONFIG_HOME", "PI_CODING_AGENT_DIR"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name == runtime)
    rt = runtimes.find(runtime)
    [receiver] = assets.global_targets((rt,), "skills", fake_home, explicit=True, errors=[],
                                       dotbrain_home=dotbrain_home)[rt.key]
    config = dotbrain_home / "config.yaml"
    config.write_text("skills: [misc/discovery-test]\n", encoding="utf-8")
    before = config.read_bytes()
    run = lambda *args, **kwargs: None

    def opted_in():
        return (cursor.global_delivery(dotbrain_home) if runtime == "cursor" else
                assets.HOME_DELIVERY[runtime].owned(runtimes.user_dir(rt, fake_home)))

    assert not assets.link_global(dotbrain_home, "skills", runtime, user_home=fake_home, run=run).warnings
    assert opted_in()
    assert workflows.detach_runtime(dotbrain_home, runtime, home=fake_home, run=run).status == "success"
    assert not opted_in()
    later = bootstrap.link_global_skills(dotbrain_home, home=fake_home)
    assert not later.warnings
    assert later.notices == [f"{rt.label} is installed; run `dotbrain bootstrap --runtime {runtime}` to deliver dotbrain to it"]
    assert not opted_in()
    assert not list(receiver.iterdir())
    findings = [f for f in doctor._check_machine(dotbrain_home, fake_home)
                if runtime in f.message or str(receiver) in f.message]
    assert [(f.status, f.message) for f in findings] == [
        ("info", f"{rt.label} is installed; run `dotbrain bootstrap --runtime {runtime}` to deliver dotbrain to it")]
    explicit = assets.link_global(dotbrain_home, "skills", runtime, user_home=fake_home, run=run)
    assert not explicit.warnings
    assert opted_in()
    assert list(receiver.iterdir())
    if runtime == "cursor":
        assert cursor.hook_state(fake_home) == "current"
    assert config.read_bytes() == before


@pytest.mark.parametrize("destination", ("symlinked-parent", "sibling-worktree", "profile"))
@pytest.mark.parametrize("marker", ("file", "directory", "dangling-link"))
def test_detach_skips_receivers_that_reach_project_checkouts(destination, marker, dotbrain_home, fake_home, tmp_path, monkeypatch):
    set_fake_home(monkeypatch, fake_home)
    checkout = tmp_path / "checkout"
    receiver = checkout / (".codex/skills" if destination == "symlinked-parent" else "nested/runtime/.codex/skills")
    receiver.mkdir(parents=True)
    link = receiver / "owned"
    link.symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)
    brain = checkout / ".brain"
    if marker == "file":
        brain.touch()
    elif marker == "directory":
        brain.mkdir()
    else:
        brain.symlink_to(tmp_path / "missing-brain", target_is_directory=True)
    if destination == "symlinked-parent":
        (fake_home / ".codex").symlink_to(checkout / ".codex", target_is_directory=True)
    else:
        project = dotbrain_home / "brainspaces/example"
        (project / ".brain").mkdir(parents=True)
        main = tmp_path / "main" if destination == "sibling-worktree" else checkout
        main.mkdir(exist_ok=True)
        (project / ".repo").write_text(str(main))
        (dotbrain_home / "config.yaml").write_text(f"profiles:\n  codex: [{receiver.parent.as_posix()}]\n")
    safe = fake_home / ".claude/skills"
    safe.mkdir(parents=True)
    (safe / "owned").symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)

    result = workflows.detach_runtime(dotbrain_home, "all", home=fake_home)

    assert result.status == "partial"
    codex = next(t for t in result.targets if t.data["runtime"] == "codex")
    assert codex.status == "failure"
    assert codex.changes == []
    assert link.is_symlink() and link.is_dir()
    assert any("inside a wired checkout" in error for error in codex.errors)
    assert not (safe / "owned").is_symlink()


def test_detach_prunes_global_skills_under_symlinked_home_ancestor(dotbrain_home, tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    home = alias / "home"
    receiver = home / ".codex/skills"
    receiver.mkdir(parents=True)
    link = receiver / "owned"
    link.symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)

    result = workflows.detach_runtime(dotbrain_home, "codex", home=home)

    assert result.status == "success"
    assert result.targets[0].changes == ["removed codex/owned"]
    assert not link.is_symlink()
    assert not [f for f in result.targets[0].findings if f["severity"] == "warning"]


@pytest.mark.parametrize("runtime", ("hermes", "opencode", "pi", "cursor"))
def test_project_doctor_does_not_request_home_delivery_after_detach(runtime, dotbrain_home, fake_home, tmp_path, monkeypatch):
    from dotbrain import projects

    set_fake_home(monkeypatch, fake_home)
    for variable in ("HERMES_HOME", "XDG_CONFIG_HOME", "PI_CODING_AGENT_DIR"):
        monkeypatch.delenv(variable, raising=False)
    rt = runtimes.find(runtime)
    run = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", "")
    assert not assets.link_global(dotbrain_home, "skills", runtime, user_home=fake_home, run=run).warnings
    assert workflows.detach_runtime(dotbrain_home, runtime, home=fake_home, run=run).status == "success"
    checkout = tmp_path / "checkout"
    (checkout / rt.workspace).mkdir(parents=True)
    project = dotbrain_home / "brainspaces/example"
    (project / ".brain").mkdir(parents=True)
    (project / ".brain/project.yaml").write_text(
        f"agents: [{runtime}]\nbeads:\n  mode: none\nskills: [misc/discovery-test]\n", encoding="utf-8")
    target = projects.ProjectTarget("example", project, checkout)

    findings = doctor._check_project(target, dotbrain_home, run, home=fake_home)

    assert not [f for f in findings if "not delivered" in f.message or "hook entries" in f.message]
    assert not [f for f in findings if "bootstrap" in f.suggestion or "--scope global" in f.suggestion]
    assert any("delivery is missing" in f.message for f in findings)  # Project resources still checked.
    assert [(f.status, f.message) for f in findings if "is declared but not set up" in f.message] == [
        ("info", f"{rt.label} is declared but not set up on this machine; "
         f"run `dotbrain bootstrap --runtime {runtime}` to set it up.")]


@pytest.mark.parametrize("runtime,key", (("claude", "claude-code"), ("codex", "codex")))
def test_detach_includes_profile_homes(runtime, key, dotbrain_home, fake_home, tmp_path):
    profile = tmp_path / "profile"
    receiver = profile / "skills"
    receiver.mkdir(parents=True)
    (receiver / "owned").symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)
    (receiver / "foreign").write_text("keep")
    (dotbrain_home / "config.yaml").write_text(f"profiles:\n  {key}: [{profile.as_posix()}]\n")

    result = workflows.detach_runtime(dotbrain_home, runtime, home=fake_home)

    assert result.status == "success"
    assert result.targets[0].changes == [f"removed {runtime}/owned"]
    assert not (receiver / "owned").is_symlink()
    assert (receiver / "foreign").read_text() == "keep"
    assert workflows.detach_runtime(dotbrain_home, runtime, home=fake_home).targets[0].changes == []


@pytest.mark.parametrize("explicit", (True, False))
def test_project_doctor_informs_only_about_explicit_unset_runtimes(explicit, dotbrain_home, fake_home, monkeypatch):
    from dotbrain import projects

    set_fake_home(monkeypatch, fake_home)
    monkeypatch.setattr(runtimes, "installed", lambda rt: False)
    project = dotbrain_home / "brainspaces/example"
    (project / ".brain").mkdir(parents=True)
    declaration = f"agents: [{', '.join(runtimes.RUNTIMES)}, claude-code]\n" if explicit else ""
    (project / ".brain/project.yaml").write_text(declaration + "beads:\n  mode: none\n")
    target = projects.ProjectTarget("example", project, None)
    run = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", "")

    findings = doctor._check_project(target, dotbrain_home, run, home=fake_home)

    assert [(f.status, f.message) for f in findings if "is declared but not set up" in f.message] == [
        ("info", f"{rt.label} is declared but not set up on this machine; "
         f"run `dotbrain bootstrap --runtime {rt.name}` to set it up.")
        for rt in runtimes.RUNTIMES.values() if explicit]


@pytest.mark.parametrize("runtime", ("hermes", "opencode", "pi"))
def test_relocated_checkout_home_preserved_during_detach(runtime, dotbrain_home, fake_home, tmp_path, monkeypatch):
    rt = runtimes.find(runtime)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    monkeypatch.setenv(rt.home_env, str(checkout / "nested/runtime"))
    directory = runtimes.user_dir(rt, fake_home)
    module = assets.HOME_DELIVERY[runtime]
    module.deliver(directory, run=lambda *args, **kwargs: None)  # delivered before the folder became a checkout
    (checkout / ".brain").touch()
    before = {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()}
    safe = fake_home / ".claude/skills"
    safe.mkdir(parents=True)
    (safe / "owned").symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)

    result = workflows.detach_runtime(dotbrain_home, "all", home=fake_home)

    target = next(t for t in result.targets if t.data["runtime"] == runtime)
    assert result.status == "partial"
    assert target.status == "failure" and not target.changes
    assert len(target.errors) == 1
    assert rt.home_env in target.errors[0] and "inside a wired checkout" in target.errors[0]
    assert {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()} == before
    assert not (safe / "owned").is_symlink()


@pytest.mark.parametrize("runtime", ("hermes", "opencode", "pi"))
def test_bootstrap_skips_owned_copy_in_relocated_checkout_home(runtime, dotbrain_home, fake_home, tmp_path, monkeypatch):
    rt = runtimes.find(runtime)
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".brain").symlink_to(tmp_path / "missing-brain", target_is_directory=True)
    monkeypatch.setenv(rt.home_env, str(checkout / "nested/runtime"))
    directory = runtimes.user_dir(rt, fake_home)

    (dotbrain_home / "config.yaml").write_text("skills: [misc/discovery-test]\n")

    explicit = bootstrap.link_global_skills(dotbrain_home, runtime, home=fake_home)

    assert len(explicit.warnings) == 1
    assert rt.home_env in explicit.warnings[0] and "inside a wired checkout" in explicit.warnings[0]
    assert not directory.exists()  # Explicit setup must not create the owned copy.
    # An existing owned copy opts an unfiltered bootstrap in, but must still be left alone.
    module = assets.HOME_DELIVERY[runtime]
    bundle = opencode.packaged_dir(directory) if runtime == "opencode" else module.plugin_dir(directory)
    bundle.mkdir(parents=True)
    (bundle / owned_copy.MARKER).touch()
    result = bootstrap.link_global_skills(dotbrain_home, home=fake_home)

    assert len(result.warnings) == 1 and rt.home_env in result.warnings[0]
    assert list(bundle.iterdir()) == [bundle / owned_copy.MARKER]
    assert (fake_home / ".claude/skills/discovery-test").is_symlink()
    assert not (tmp_path / "global-skills").exists()


def _cursor_home_in_checkout(fake_home, tmp_path):
    """~/.cursor linked into a wired checkout's .cursor; returns that real folder."""
    checkout = tmp_path / "checkout"
    (checkout / ".cursor").mkdir(parents=True)
    (fake_home / ".cursor").symlink_to(checkout / ".cursor", target_is_directory=True)
    return checkout


def test_detach_leaves_cursor_hooks_in_a_checkout_home(dotbrain_home, fake_home, tmp_path):
    checkout = _cursor_home_in_checkout(fake_home, tmp_path)
    assert cursor.reconcile_hooks(fake_home).linked  # dotbrain entries land in the checkout's hooks.json
    (checkout / ".brain").touch()
    before = {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()}

    result = workflows.detach_runtime(dotbrain_home, "cursor", home=fake_home)

    target = result.targets[0]
    assert target.status == "failure" and not target.changes
    assert any("~/.cursor" in error and "inside a wired checkout" in error for error in target.errors)
    assert {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()} == before


def test_bootstrap_writes_no_cursor_hooks_into_a_checkout_home(dotbrain_home, fake_home, tmp_path):
    checkout = _cursor_home_in_checkout(fake_home, tmp_path)
    (checkout / ".brain").touch()

    (dotbrain_home / "config.yaml").write_text("skills: [misc/discovery-test]\n")

    result = bootstrap.link_global_skills(dotbrain_home, "cursor", home=fake_home)

    assert any("~/.cursor" in warning and "inside a wired checkout" in warning for warning in result.warnings)
    assert not (checkout / ".cursor/hooks.json").exists()
    assert list((checkout / ".cursor").iterdir()) == []
    assert not (tmp_path / "global-skills").exists()


# A safe runtime home whose plugin folder links into a wired checkout: (runtime, linked folder below the home).
LINKED_BELOW_HOME = (("hermes", "plugins"), ("pi", "extensions"), ("opencode", "plugins"), ("opencode", "dotbrain"))


def _linked_below_home(runtime, folder, fake_home, tmp_path):
    checkout = tmp_path / "checkout"
    (checkout / folder).mkdir(parents=True)
    home = runtimes.user_dir(runtimes.find(runtime), fake_home)
    home.mkdir(parents=True, exist_ok=True)
    (home / folder).symlink_to(checkout / folder, target_is_directory=True)
    return checkout, home


def _snapshot(root):
    return {p.relative_to(root): (p.read_bytes() if p.is_file() else None) for p in root.rglob("*")}


@pytest.mark.parametrize("runtime, folder", LINKED_BELOW_HOME)
def test_bootstrap_refuses_writes_through_a_link_below_a_safe_home(runtime, folder, dotbrain_home, fake_home, tmp_path):
    checkout, _ = _linked_below_home(runtime, folder, fake_home, tmp_path)
    (checkout / ".brain").touch()
    before = _snapshot(checkout)

    result = bootstrap.link_global_skills(dotbrain_home, runtime, home=fake_home)

    assert any("inside a wired checkout" in warning for warning in result.warnings)
    assert _snapshot(checkout) == before


@pytest.mark.parametrize("runtime, folder", LINKED_BELOW_HOME)
def test_detach_refuses_deletes_through_a_link_below_a_safe_home(runtime, folder, dotbrain_home, fake_home, tmp_path):
    checkout, home = _linked_below_home(runtime, folder, fake_home, tmp_path)
    assets.HOME_DELIVERY[runtime].deliver(home, run=lambda *args, **kwargs: None)  # before it became a checkout
    (checkout / ".brain").touch()
    before = _snapshot(checkout)
    assert any(path.is_file() for path in (checkout / folder).rglob("*"))

    result = workflows.detach_runtime(dotbrain_home, runtime, home=fake_home)

    target = result.targets[0]
    assert any("inside a wired checkout" in error for error in target.errors)
    assert _snapshot(checkout) == before


def _cursor_hooks_file_in_checkout(fake_home, tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "hooks.json").write_text('{"version": 1, "hooks": {}}\n', encoding="utf-8")
    (fake_home / ".cursor").mkdir()
    (fake_home / ".cursor/hooks.json").symlink_to(checkout / "hooks.json")
    return checkout


def test_bootstrap_refuses_a_cursor_hooks_file_linked_into_a_checkout(dotbrain_home, fake_home, tmp_path):
    checkout = _cursor_hooks_file_in_checkout(fake_home, tmp_path)
    (checkout / ".brain").touch()
    before = _snapshot(checkout)

    result = bootstrap.link_global_skills(dotbrain_home, "cursor", home=fake_home)

    assert any("inside a wired checkout" in warning for warning in result.warnings)
    assert _snapshot(checkout) == before


def test_detach_refuses_a_cursor_hooks_file_linked_into_a_checkout(dotbrain_home, fake_home, tmp_path):
    checkout = _cursor_hooks_file_in_checkout(fake_home, tmp_path)
    assert cursor.reconcile_hooks(fake_home).linked  # entries written through the link, before it became a checkout
    (checkout / ".brain").touch()
    before = _snapshot(checkout)

    result = workflows.detach_runtime(dotbrain_home, "cursor", home=fake_home)

    messages = [f["message"] for f in result.targets[0].findings] + result.targets[0].errors
    assert any("inside a wired checkout" in message for message in messages)
    assert _snapshot(checkout) == before


def test_detach_removes_no_opencode_file_when_its_packaged_copy_is_refused(dotbrain_home, fake_home, tmp_path):
    checkout, home = _linked_below_home("opencode", "dotbrain", fake_home, tmp_path)
    opencode.deliver(home)  # the plugin file lands in the safe home, the packaged copy through the link
    (checkout / ".brain").touch()
    plugin = opencode.plugin_file(home)
    before = plugin.read_bytes()

    result = workflows.detach_runtime(dotbrain_home, "opencode", home=fake_home)

    target = result.targets[0]
    assert any("inside a wired checkout" in error for error in target.errors)
    assert plugin.read_bytes() == before and not target.changes  # nothing removed, so nothing unreported
