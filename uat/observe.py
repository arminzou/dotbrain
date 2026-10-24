"""Observations the journeys make from outside the model: event streams, hook calls, fingerprints.

Pure functions only, so the no-credential run checks them without launching a runtime.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from collections import Counter


def nonce(label: str) -> str:
    """A value no model can guess and no file outside the sandbox holds."""
    return f"UAT-{label}-{secrets.token_hex(8)}"


def json_events(stdout: str) -> list[dict]:
    """The JSON objects of a headless run's event stream, one per line; other lines are ignored."""
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def opencode_tool_calls(events: list[dict]) -> list[str]:
    """Tool names from `opencode run --format json`: one `tool_use` event per finished tool part."""
    return [str((event.get("part") or {}).get("tool")) for event in events if event.get("type") == "tool_use"]


def opencode_answer(events: list[dict]) -> str:
    """The text the model produced, from the stream's `text` events."""
    return "\n".join(str((event.get("part") or {}).get("text", "")) for event in events if event.get("type") == "text")


def pi_tool_calls(events: list[dict]) -> list[str]:
    """Tool names from `pi -p --mode json`: one `tool_execution_start` event per tool call."""
    return [str(event.get("toolName")) for event in events if event.get("type") == "tool_execution_start"]


def pi_answer(events: list[dict]) -> str:
    """The text of the assistant's finished messages, from the stream's `message_end` events."""
    messages = [event.get("message") or {} for event in events if event.get("type") == "message_end"]
    return "\n".join(str(part.get("text", "")) for message in messages if message.get("role") == "assistant"
                     for part in message.get("content") or [] if part.get("type") == "text")
def cursor_tool_calls(events: list[dict]) -> list[str]:
    """Tool names from `agent -p --output-format stream-json`: one `tool_call` event with subtype `started`
    per call (a `completed` one follows), its `tool_call` object keyed by the tool, such as `readToolCall`."""
    return [next(iter(event.get("tool_call") or {}), "?") for event in events
            if event.get("type") == "tool_call" and event.get("subtype") == "started"]


def cursor_answer(events: list[dict]) -> str:
    """The text the model produced: the closing `result` event carries the whole run's text."""
    return "\n".join(str(event.get("result", "")) for event in events if event.get("type") == "result")


# A shim log line holds the argv the adapter passed, quoted or not: hook run --event <event> --checkout <path>
_HOOK_EVENT = re.compile(r'\bhook"?\s+"?run"?\s.*?--event"?\s+"?([a-z-]+)')


def hook_events(log: str) -> Counter:
    """How often each event reached `dotbrain hook run`, from the recording shim's log."""
    return Counter(match.group(1) for match in map(_HOOK_EVENT.search, log.splitlines()) if match)


def fingerprint(roots, skip=()) -> dict[str, tuple[int, int]]:
    """Every path below ``roots`` with its size and mtime; directories as ``(-1, 0)``. Missing roots add nothing.

    Paths in ``skip``, and everything below them, are left out: runtime binaries an auto-update may replace.
    """
    skipped = {os.path.normcase(os.path.abspath(path)) for path in skip}
    kept = lambda top, name: os.path.normcase(os.path.abspath(os.path.join(top, name))) not in skipped  # noqa: E731
    seen: dict[str, tuple[int, int]] = {}
    for root in roots:
        for top, dirs, files in os.walk(root):
            seen[top] = (-1, 0)
            dirs[:] = [name for name in dirs if kept(top, name)]
            for name in files:
                if not kept(top, name):
                    continue
                path = os.path.join(top, name)
                try:
                    stat = os.lstat(path)
                except OSError:
                    continue  # removed while walking: the next fingerprint shows it
                seen[path] = (stat.st_size, stat.st_mtime_ns)
    return seen


def changed(before: dict, after: dict) -> list[str]:
    """Paths added, removed, or modified between two fingerprints."""
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
