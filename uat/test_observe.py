"""The observation helpers, checked without a runtime or credentials."""

from __future__ import annotations

import os

from backends import leaks
from conftest import credential
from observe import (changed, cursor_answer, cursor_tool_calls, fingerprint, hook_events, json_events, nonce,
                     opencode_answer, opencode_tool_calls, pi_answer, pi_tool_calls)

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


# Lines as `pi -p --mode json` writes them, read from @earendil-works/pi-coding-agent 1.4.0 (the pinned
# Pi): dist/modes/print-mode.js writes the session header, then every session event as one JSON line;
# dist/modes/json-event.js strips `message` from `message_update` only. The event types are
# pi-agent-core's AgentEvent (dist/types.d.ts): a tool call is one `tool_execution_start`
# {toolCallId, toolName, args}; a finished message is `message_end` {message: {role, content: [...]}},
# whose assistant `content` holds `text`, `thinking` and `toolCall` parts.
PI_STREAM = "\n".join([
    '{"type":"session","version":3,"id":"s","cwd":"/work/checkout"}',
    '{"type":"agent_start"}',
    '{"type":"message_end","message":{"role":"user","content":[{"type":"text","text":"Reply"}]}}',
    '{"type":"message_update","usage":{},"assistantMessageEvent":{"type":"text_delta","delta":"UAT"}}',
    '{"type":"message_end","message":{"role":"assistant","content":[{"type":"thinking","thinking":"t"},'
    '{"type":"toolCall","id":"c1","name":"read","arguments":{}}]}}',
    '{"type":"tool_execution_start","toolCallId":"c1","toolName":"read","args":{"path":"x"}}',
    '{"type":"tool_execution_end","toolCallId":"c1","toolName":"read","result":{},"isError":false}',
    '{"type":"message_end","message":{"role":"assistant","content":[{"type":"text","text":"UAT-convention-1"}]}}',
    '{"type":"agent_end","messages":[]}',
    '{"type":"agent_settled","aborted":false}',
])


def test_pi_event_stream_yields_tool_calls_and_answer():
    events = json_events(PI_STREAM)
    assert pi_tool_calls(events) == ["read"]
    assert pi_answer(events) == "UAT-convention-1"
# Lines as `agent -p --output-format stream-json` writes them, read from the print-mode writer in
# Cursor CLI 2026.10.22-27dcf5f's bundle (4525.index.js): assistant text is buffered and flushed before
# each tool call; each call writes `tool_call` `started` then `completed`; `result` closes with all the text.
CURSOR_STREAM = "\n".join([
    '{"type":"system","subtype":"init","session_id":"s"}',
    '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Reading."}]},"session_id":"s"}',
    '{"type":"tool_call","subtype":"started","call_id":"c","tool_call":{"readToolCall":{"args":{"path":"a"}}},'
    '"session_id":"s","timestamp_ms":1}',
    '{"type":"tool_call","subtype":"completed","call_id":"c","tool_call":{"readToolCall":{"args":{"path":"a"}}},'
    '"session_id":"s","timestamp_ms":2}',
    '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"UAT-convention-1"}]},'
    '"session_id":"s"}',
    '{"type":"result","subtype":"success","is_error":false,"result":"Reading.UAT-convention-1","session_id":"s"}',
])


def test_cursor_stream_yields_tool_calls_and_answer():
    events = json_events(CURSOR_STREAM)
    assert cursor_tool_calls(events) == ["readToolCall"]
    assert cursor_answer(events) == "Reading.UAT-convention-1"


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
    # A skipped path, such as a runtime binary an auto-update replaces, never shows as a change.
    skip = [tmp_path / "new", tmp_path / "keep"]
    before = fingerprint([tmp_path], skip)
    (tmp_path / "new" / "binary").write_text("v2")
    (tmp_path / "keep").write_text("v2")
    assert changed(before, fingerprint([tmp_path], skip)) == []


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


def test_cursor_takes_only_its_own_credential(monkeypatch):
    for name in ("CURSOR_API_KEY", "CURSOR_AUTH_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-other")
    assert credential("cursor") == "set CURSOR_API_KEY or CURSOR_AUTH_TOKEN"
    monkeypatch.setenv("CURSOR_AUTH_TOKEN", "token")
    assert credential("cursor")[1] == {"CURSOR_AUTH_TOKEN": "token"}
    monkeypatch.setenv("CURSOR_API_KEY", "key")
    assert credential("cursor")[1] == {"CURSOR_API_KEY": "key"}
