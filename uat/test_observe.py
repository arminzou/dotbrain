"""The observation helpers, checked without a runtime or credentials."""

from __future__ import annotations

import os

from conftest import credential, leaks
from observe import changed, fingerprint, hook_events, json_events, nonce, opencode_answer, opencode_tool_calls

# Lines as `opencode run --format json` writes them: {type, timestamp, sessionID, part}.
STREAM = "\n".join([
    '{"type":"step_start","timestamp":1,"sessionID":"s","part":{"type":"step-start"}}',
    '{"type":"tool_use","timestamp":2,"sessionID":"s","part":{"type":"tool","tool":"read","state":{"status":"completed"}}}',
    "not json",
    '{"type":"text","timestamp":3,"sessionID":"s","part":{"type":"text","text":"UAT-convention-1"}}',
    '{"type":"step_finish","timestamp":4,"sessionID":"s","part":{"type":"step-finish"}}',
])


def test_event_stream_yields_tool_calls_and_answer():
    events = json_events(STREAM)
    assert len(events) == 4
    assert opencode_tool_calls(events) == ["read"]
    assert opencode_answer(events) == "UAT-convention-1"


def test_hook_events_count_only_hook_runs():
    log = "\n".join([
        "bootstrap --runtime opencode",
        '"hook" "run" "--event" "startup" "--checkout" "C:\\sandbox\\checkout"',
        "hook run --event turn-end --checkout /sandbox/checkout",
        '"hook" "run" "--event" "turn-end" "--checkout" "C:\\sandbox\\checkout"',
        "ECHO is off.",
    ])
    assert hook_events(log) == {"startup": 1, "turn-end": 2}


def test_fingerprint_sees_added_modified_and_removed_paths(tmp_path):
    (tmp_path / "keep").write_text("a")
    (tmp_path / "edit").write_text("a")
    (tmp_path / "gone").write_text("a")
    before = fingerprint([tmp_path, tmp_path / "missing"])
    assert changed(before, fingerprint([tmp_path])) == []
    (tmp_path / "edit").write_text("ab")
    (tmp_path / "gone").unlink()
    (tmp_path / "new").mkdir()
    after = fingerprint([tmp_path])
    assert changed(before, after) == sorted(str(tmp_path / name) for name in ("edit", "gone", "new"))


def test_nonces_differ():
    assert nonce("x") != nonce("x")


def test_leaks_finds_a_written_secret(tmp_path):
    (tmp_path / "clean").write_text("nothing")
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "log").write_text("key=sk-secret")
    assert leaks(tmp_path, "sk-secret") == [os.path.join(tmp_path, "deep", "log")]


def test_only_the_named_credential_counts(monkeypatch):
    for name in ("UAT_OPENCODE_MODEL", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://unrelated")
    assert "UAT_OPENCODE_MODEL" in credential("opencode")
    monkeypatch.setenv("UAT_OPENCODE_MODEL", "deepseek/deepseek-chat")
    assert "DEEPSEEK_API_KEY" in credential("opencode")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    assert credential("opencode") == ("deepseek/deepseek-chat", {"DEEPSEEK_API_KEY": "sk-test"})
