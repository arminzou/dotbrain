"""Cursor shell adapter and protocol contracts, without native sessions or user homes."""
import io
import json
import shlex
import subprocess

import pytest
from typer.testing import CliRunner

from dotbrain import cursor, doctor, hooks, resource_loader
from dotbrain.cli import app


@pytest.mark.parametrize("windows", [False, True])
def test_native_entries(windows):
    entries = cursor.hook_entries(windows=windows)
    assert list(entries) == ["sessionStart", "stop", "sessionEnd"]
    for native, event in zip(entries, ("startup", "turn-end", "session-end")):
        checkout = '$env:CURSOR_PROJECT_DIR' if windows else '"$CURSOR_PROJECT_DIR"'
        assert entries[native] == [{
            "command": f"dotbrain hook run --event {event} --checkout {checkout} --format json",
            "timeout": 15 if native == "sessionStart" else 5}]


def test_merge_reinstall_replace_and_remove(tmp_path):
    path = tmp_path / ".cursor/hooks.json"
    path.parent.mkdir()
    foreign = {"command": "my-hook", "timeout": 7}
    data = {"version": 1, "custom": True, "hooks": {"stop": [foreign], "other": [{"command": "other"}]}}
    path.write_text(json.dumps(data))
    assert cursor.hook_state(tmp_path) == "foreign"
    assert cursor.reconcile_hooks(tmp_path).linked == ["cursor/hooks.json"]
    installed = json.loads(path.read_text())
    assert installed["hooks"]["stop"] == [foreign, *cursor.hook_entries()["stop"]]
    assert installed["custom"] is True
    assert cursor.hook_state(tmp_path) == "current"
    before = path.read_bytes()
    assert not cursor.reconcile_hooks(tmp_path).linked
    assert path.read_bytes() == before
    installed["hooks"]["stop"].extend([{"command": "dotbrain hook stop"}] * 2)
    path.write_text(json.dumps(installed))
    assert cursor.hook_state(tmp_path) == "stale"
    assert any("stale" in f.message for f in doctor._check_cursor_hooks(tmp_path))
    cursor.reconcile_hooks(tmp_path)
    assert cursor.hook_state(tmp_path) == "current"
    cursor.reconcile_hooks(tmp_path, remove=True)
    assert json.loads(path.read_text()) == data
    assert not cursor.reconcile_hooks(tmp_path, remove=True).pruned


def test_remove_only_empty_file(tmp_path):
    assert not cursor.reconcile_hooks(tmp_path, remove=True).pruned
    assert not (tmp_path / ".cursor").exists()
    cursor.reconcile_hooks(tmp_path)
    assert cursor.reconcile_hooks(tmp_path, remove=True).pruned == ["cursor/hooks.json"]
    assert not (tmp_path / ".cursor/hooks.json").exists()


@pytest.mark.parametrize("body", ["{", "[]", '{"hooks": []}', '{"hooks": {"stop": {}}}',
                                '{"hooks": {"stop": [null]}}', '{"hooks": {"stop": [{"command": 4}]}}'])
def test_malformed_hooks_never_rewritten(tmp_path, body):
    path = tmp_path / ".cursor/hooks.json"
    path.parent.mkdir()
    path.write_text(body)
    for remove in (False, True):
        assert cursor.reconcile_hooks(tmp_path, remove=remove).warnings
        assert path.read_text() == body
    assert cursor.hook_state(tmp_path) == "malformed"
    assert any("malformed" in f.message for f in doctor._check_cursor_hooks(tmp_path))


def test_missing_and_foreign_diagnosis(tmp_path):
    assert any("missing" in f.message for f in doctor._check_cursor_hooks(tmp_path))
    path = tmp_path / ".cursor/hooks.json"
    path.parent.mkdir()
    path.write_text('{"hooks": {"stop": [{"command": "echo dotbrain-other"}]}}')
    assert any("foreign" in f.message for f in doctor._check_cursor_hooks(tmp_path))


def test_write_failure_warns(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise PermissionError("read only")
    monkeypatch.setattr(type(tmp_path), "write_text", fail)
    assert cursor.reconcile_hooks(tmp_path).warnings


@pytest.mark.parametrize("command", ["session-start", "stop", "session-end"])
@pytest.mark.parametrize("version", ["2026.10", ""])
def test_claude_protocol_is_silent_under_cursor(monkeypatch, command, version):
    monkeypatch.setenv("CURSOR_VERSION", version)
    def unexpected(*args, **kwargs):
        pytest.fail("imported plugin hook ran under Cursor")
    monkeypatch.setattr(hooks, "handle_event", unexpected)
    monkeypatch.setattr(hooks, "payload_field", unexpected)
    result = CliRunner().invoke(app, ["hook", command])
    assert result.exit_code == 0 and result.output == ""


@pytest.mark.parametrize("wired", [False, True])
def test_generated_events_repeat_without_context_duplication(tmp_path, monkeypatch, wired):
    checkout = tmp_path / "checkout with spaces"
    checkout.mkdir()
    with resource_loader.resource_file("templates/brain/DOTBRAIN.md") as source:
        body = source.read_bytes()
    if wired:
        (checkout / ".brain").mkdir()
        (checkout / ".brain/DOTBRAIN.md").write_bytes(body)
    monkeypatch.setattr(hooks, "repo_root", lambda cwd: checkout if cwd == checkout else None)
    monkeypatch.setenv("CURSOR_VERSION", "test")
    monkeypatch.chdir(tmp_path)  # user hooks do not run in the checkout
    calls = []
    monkeypatch.setattr(hooks, "start_sync", lambda **kwargs: calls.append(kwargs))
    for native, entries in cursor.hook_entries(windows=False).items():
        argv = shlex.split(entries[0]["command"].replace('"$CURSOR_PROJECT_DIR"', f'"{checkout.as_posix()}"'))[1:]
        outputs = [CliRunner().invoke(app, argv) for _ in range(2)]
        assert all(result.exit_code == 0 for result in outputs)
        assert outputs[0].stdout_bytes == outputs[1].stdout_bytes
        if native == "sessionStart" and wired:
            text = json.loads(outputs[0].stdout_bytes)["additional_context"]
            assert text == hooks.brain_context(checkout).decode()
            assert text.endswith(body.decode() + "\n\n")
            assert len(text.strip().encode("utf-16-le")) // 2 < 10_000
            assert text.count(hooks.CONVENTION_HEADING) == 1
        else:
            assert outputs[0].stdout_bytes == b""
    assert calls == ([{"wait": 10, "checkout": checkout}] * 2 +
                     [{"push_only": True, "checkout": checkout}] * 2 + [{"checkout": checkout}] * 2)


@pytest.mark.parametrize("failure", [OSError("missing executable"), subprocess.TimeoutExpired("sync", 10)])
def test_startup_sync_failure_keeps_complete_context(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(hooks, "sync_home", lambda checkout: tmp_path)
    def launch(*args):
        raise failure
    monkeypatch.setattr(hooks, "_launch_detached", launch)
    monkeypatch.setattr(hooks, "brain_context", lambda cwd: b"COMPLETE END")
    output = io.BytesIO()
    monkeypatch.setattr(hooks.sys, "stdout", io.TextIOWrapper(output, encoding="utf-8"))
    hooks.handle_event("startup", tmp_path, "json")
    assert json.loads(output.getvalue()) == {"additional_context": "COMPLETE END"}
