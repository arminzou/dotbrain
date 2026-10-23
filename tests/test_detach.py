"""Machine delivery removal never reaches project checkouts or foreign entries."""
import json
import subprocess

import pytest
from typer.testing import CliRunner

from conftest import set_fake_home
from dotbrain import assets, cursor, hermes, opencode, owned_copy, runtimes, skills, workflows
from dotbrain.cli import app


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


def test_detach_configured_receiver_and_empty_hooks(dotbrain_home, fake_home, tmp_path):
    dest = tmp_path / "custom-skills"
    dest.mkdir()
    (dest / "owned").symlink_to(dotbrain_home / "skills/misc/discovery-test", target_is_directory=True)
    (dotbrain_home / "skills/skills.yaml").write_text(f"targets:\n  cursor: {dest.as_posix()}\n")
    cursor.reconcile_hooks(fake_home)
    result = workflows.detach_runtime(dotbrain_home, "cursor", home=fake_home)
    assert result.status == "success"
    assert not (dest / "owned").is_symlink()
    assert not (fake_home / ".cursor/hooks.json").exists()
