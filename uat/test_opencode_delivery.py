"""Runtime delivery journeys: skills, the convention before the first request, hook calls, non-blocking sync.

Every journey runs for each runtime in ``ADAPTERS``; an adapter holds what differs per runtime.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from observe import cursor_answer, cursor_tool_calls, hook_events, json_events, opencode_answer, opencode_tool_calls, pi_answer, pi_tool_calls
from prepare import PENDING, SKILL

REPO = Path(__file__).resolve().parent.parent
# A session start waits at most 10 s for sync and the plugin caps its hook at 12 s; the rest is the model.
NON_BLOCKING_SECONDS = 120
CONVENTION_PROMPT = ("Your instructions end with a line naming the UAT convention nonce. Reply with that "
                     "nonce only. Do not call any tools.")


@dataclass(frozen=True)
class Adapter:
    headless: Callable[[str, str], list[str]]  # (model, prompt) -> arguments of a headless JSON-stream run
    tool_calls: Callable[[list[dict]], list[str]]
    answer: Callable[[list[dict]], str]
    skills: list[str] | None = None  # arguments that list discovered skills as JSON without a model call


ADAPTERS = {
    "opencode": Adapter(lambda model, prompt: ["run", "--format", "json", "-m", model, prompt],
                        opencode_tool_calls, opencode_answer, ["debug", "skill"]),
    # Pi has no model-free skill listing. --approve trusts the checkout for this run only, so Pi
    # reads the project skills in .pi/skills without a trust.json entry.
    "pi": Adapter(lambda model, prompt: ["-p", "--mode", "json", "--approve", "--model", model, prompt],
                  pi_tool_calls, pi_answer),
    # Cursor has no model-free skill listing. Print mode refuses an untrusted workspace; without
    # --force shell commands stay unapproved; no --model runs the account's default model; the
    # auto-update would replace the version under test.
    "cursor": Adapter(lambda _model, prompt: ["-p", "--trust", "--disable-auto-update",
                                              "--output-format", "stream-json", prompt],
                      cursor_tool_calls, cursor_answer),
}


@pytest.fixture(params=list(ADAPTERS))
def runtime(request):
    return request.param


def packaged_skills() -> set[str]:
    names = set()
    for skill in (REPO / "plugin" / "skills").glob("*/SKILL.md"):
        match = re.search(r"^name:\s*(\S+)", skill.read_text(encoding="utf-8"), re.M)
        if match:
            names.add(match.group(1))
    return names


def headless(sandbox, runtime, prompt):
    """The run's events and how long it took; it must succeed."""
    started = time.monotonic()
    done = sandbox.runtime(*ADAPTERS[runtime].headless(sandbox.model, prompt))
    elapsed = time.monotonic() - started
    assert done.returncode == 0, done.stderr[-4000:]
    return json_events(done.stdout), elapsed


def wait_for(check, seconds=30):
    deadline = time.monotonic() + seconds
    while not (result := check()) and time.monotonic() < deadline:
        time.sleep(1)
    return result


def git(sandbox, *args):
    return sandbox.backend.run(["git", "-C", sandbox.backend.data_root, *args]).stdout.strip()


def test_packaged_and_synthetic_skills_are_discovered(sandbox, runtime):
    adapter = ADAPTERS[runtime]
    if adapter.skills:
        listed = {skill["name"] for skill in json.loads(sandbox.runtime(*adapter.skills).stdout)}
        assert packaged_skills() | {SKILL} <= listed

    events, _ = headless(sandbox, runtime, f"Use the {SKILL} skill and reply with the UAT reference nonce it leads "
                                           "you to. Then list the name of every skill available to you, one per line.")
    answer = adapter.answer(events)
    assert sandbox.reference_nonce in answer
    assert SKILL in answer and "wire-brain" in answer


def test_convention_arrives_before_the_first_request(sandbox, runtime):
    events, _ = headless(sandbox, runtime, CONVENTION_PROMPT)
    assert sandbox.convention_nonce in ADAPTERS[runtime].answer(events)
    assert ADAPTERS[runtime].tool_calls(events) == []


def test_one_hook_call_per_event(sandbox, runtime):
    headless(sandbox, runtime, "Reply with OK only.")
    # turn-end and session-end are launched detached and may land after the run exits.
    log = lambda: sandbox.backend.read(sandbox.backend.hook_log)  # noqa: E731
    assert wait_for(lambda: {"startup", "turn-end"} <= hook_events(log()).keys()), log()
    time.sleep(3)  # let a duplicate land, if there is one
    calls = hook_events(log())
    assert calls["startup"] == 1 and calls["turn-end"] == 1
    assert all(count == 1 for count in calls.values()), calls


def test_unreachable_remote_does_not_block_and_sync_records_locally(sandbox, runtime):
    events, elapsed = headless(sandbox, runtime, CONVENTION_PROMPT)
    assert elapsed < NON_BLOCKING_SECONDS
    assert sandbox.convention_nonce in ADAPTERS[runtime].answer(events)
    assert wait_for(lambda: git(sandbox, "log", "--format=%s", "--", PENDING)), "no sync commit recorded the change"
    assert int(git(sandbox, "rev-list", "--count", "@{upstream}..HEAD")) >= 1
