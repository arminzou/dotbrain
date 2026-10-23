"""OpenCode journeys: skills, the convention before the first request, hook calls, non-blocking sync."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from observe import hook_events, json_events, opencode_answer, opencode_tool_calls
from prepare import PENDING, SKILL

RUNTIME = "opencode"
REPO = Path(__file__).resolve().parent.parent
# A session start waits at most 10 s for sync and the plugin caps its hook at 12 s; the rest is the model.
NON_BLOCKING_SECONDS = 120
CONVENTION_PROMPT = ("Your instructions end with a line naming the UAT convention nonce. Reply with that "
                     "nonce only. Do not call any tools.")


def packaged_skills() -> set[str]:
    names = set()
    for skill in (REPO / "plugin" / "skills").glob("*/SKILL.md"):
        match = re.search(r"^name:\s*(\S+)", skill.read_text(encoding="utf-8"), re.M)
        if match:
            names.add(match.group(1))
    return names


def headless(sandbox, prompt):
    """The run's events and how long it took; it must succeed."""
    started = time.monotonic()
    done = sandbox.runtime("run", "--format", "json", "-m", sandbox.model, prompt)
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


def test_packaged_and_synthetic_skills_are_discovered(sandbox):
    listed = {skill["name"] for skill in json.loads(sandbox.runtime("debug", "skill").stdout)}
    assert packaged_skills() | {SKILL} <= listed

    events, _ = headless(sandbox, f"Use the {SKILL} skill and reply with the UAT reference nonce it leads you to. "
                                  "Then list the name of every skill available to you, one per line.")
    answer = opencode_answer(events)
    assert sandbox.reference_nonce in answer
    assert SKILL in answer and "wire-brain" in answer


def test_convention_arrives_before_the_first_request(sandbox):
    events, _ = headless(sandbox, CONVENTION_PROMPT)
    assert sandbox.convention_nonce in opencode_answer(events)
    assert opencode_tool_calls(events) == []


def test_one_hook_call_per_event(sandbox):
    headless(sandbox, "Reply with OK only.")
    # turn-end and session-end are launched detached and may land after the run exits.
    log = lambda: sandbox.backend.read(sandbox.backend.hook_log)  # noqa: E731
    assert wait_for(lambda: {"startup", "turn-end"} <= hook_events(log()).keys()), log()
    time.sleep(3)  # let a duplicate land, if there is one
    calls = hook_events(log())
    assert calls["startup"] == 1 and calls["turn-end"] == 1
    assert all(count == 1 for count in calls.values()), calls


def test_unreachable_remote_does_not_block_and_sync_records_locally(sandbox):
    events, elapsed = headless(sandbox, CONVENTION_PROMPT)
    assert elapsed < NON_BLOCKING_SECONDS
    assert sandbox.convention_nonce in opencode_answer(events)
    assert wait_for(lambda: git(sandbox, "log", "--format=%s", "--", PENDING)), "no sync commit recorded the change"
    assert int(git(sandbox, "rev-list", "--count", "@{upstream}..HEAD")) >= 1
