"""OpenCode session hooks: the packaged plugin maps OpenCode events onto `dotbrain hook run`.

Each test drives the real plugin file under Node with a fake OpenCode input and a fake `dotbrain`
on PATH that records every call.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from dotbrain import hooks as hooks_mod

PLUGIN = Path(__file__).resolve().parent.parent / "plugin" / "opencode" / "dotbrain.js"
CONVENTION = "## dotbrain convention\n\nBODY"
BASE = "base prompt"

# Plays `steps` against the plugin's hooks as OpenCode calls them and prints what each request got.
HARNESS = r"""
import { pathToFileURL } from "node:url"
let raw = ""
for await (const chunk of process.stdin) raw += chunk
const { plugin, input, parents, getFails, fastTimers, steps } = JSON.parse(raw)
if (fastTimers) {
  const real = globalThis.setTimeout
  globalThis.setTimeout = (fn, ms, ...rest) => real(fn, Math.min(ms, 300), ...rest)
}
input.client = { session: { get: async ({ path }) => {
  if (getFails) throw new Error("no server")
  return { data: { id: path.id, ...(parents[path.id] ? { parentID: parents[path.id] } : {}) } }
} } }
const hooks = await (await import(pathToFileURL(plugin).href)).default.server(input)
const result = { hooks: Object.keys(hooks).sort(), requests: [], errors: [] }
for (const step of steps) {
  try {
    if (step.op === "message") await hooks["chat.message"]?.({ sessionID: step.session }, { message: {}, parts: [] })
    else if (step.op === "request") {
      const output = { system: [step.system ?? "base prompt"] }
      await hooks["experimental.chat.system.transform"]?.({ sessionID: step.session, model: {} }, output)
      result.requests.push(output.system.slice(1))
    } else if (step.op === "event") await hooks.event?.({ event: { type: step.type, properties: step.properties } })
    else if (step.op === "dispose") await hooks.dispose?.()
  } catch (error) {
    result.errors.push(String(error))
  }
}
process.stdout.write(JSON.stringify(result))
process.exit(0)
"""

# A stand-in `dotbrain`: records `hook run` calls and answers from behavior.json.
FAKE_CLI = r"""
import fs from "node:fs"
const dir = new URL(".", import.meta.url)
const args = process.argv.slice(2)
const event = args[args.indexOf("--event") + 1]
fs.appendFileSync(new URL("calls.log", dir), JSON.stringify({ event, checkout: args[args.indexOf("--checkout") + 1] }) + "\n")
const behavior = JSON.parse(fs.readFileSync(new URL("behavior.json", dir), "utf8"))[event] ?? {}
if (behavior.sleep) await new Promise((resolve) => setTimeout(resolve, behavior.sleep * 1000))
process.stdout.write(behavior.out ?? "")
process.exit(behavior.code ?? 0)
"""


class OpenCode:
    """A fake OpenCode instance for one git checkout, with a recording `dotbrain` on PATH."""

    def __init__(self, tmp_path: Path, node: str):
        self.node, self.tmp = node, tmp_path
        self.checkout = tmp_path / "project"
        self.checkout.mkdir()
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        (self.bin / "fake.mjs").write_text(FAKE_CLI, encoding="utf-8")
        self.log = self.bin / "calls.log"
        self.behave(startup={"out": CONVENTION + "\n\n"}, resume={"out": CONVENTION + "\n\n"},
                    compaction={"out": CONVENTION + " v2\n\n"})
        if sys.platform == "win32":
            (self.bin / "dotbrain.cmd").write_text(f'@"{node}" "{self.bin / "fake.mjs"}" %*\r\n', encoding="utf-8")
        else:
            script = self.bin / "dotbrain"
            script.write_text(f'#!/bin/sh\nexec "{node}" "{self.bin / "fake.mjs"}" "$@"\n', encoding="utf-8")
            script.chmod(0o755)
        # The plugin finds its config directory from its own path; Node needs the module type.
        (tmp_path / "plugins").mkdir()
        shutil.copyfile(PLUGIN, tmp_path / "plugins" / "dotbrain.js")
        (tmp_path / "package.json").write_text('{"type": "module"}\n', encoding="utf-8")
        (tmp_path / "harness.mjs").write_text(HARNESS, encoding="utf-8")
        self.vcs, self.parents, self.get_fails, self.fast_timers = "git", {}, False, False

    def behave(self, **events):
        (self.bin / "behavior.json").write_text(json.dumps(events), encoding="utf-8")

    def play(self, *steps, path=None) -> dict:
        env = {**os.environ, "PATH": str(self.bin) if path is None else path}
        payload = {"plugin": str(self.tmp / "plugins" / "dotbrain.js"), "parents": self.parents,
                   "getFails": self.get_fails, "fastTimers": self.fast_timers, "steps": list(steps),
                   "input": {"directory": str(self.checkout), "worktree": str(self.checkout),
                             "project": {"vcs": self.vcs} if self.vcs else {}}}
        done = subprocess.run([self.node, str(self.tmp / "harness.mjs")], input=json.dumps(payload),
                              capture_output=True, encoding="utf-8", env=env, check=True, timeout=60)
        result = json.loads(done.stdout)
        assert result["errors"] == []
        return result

    def calls(self, expected: int = 0) -> list[str]:
        """Events the fake CLI saw, once ``expected`` of them arrived (detached runs land later)."""
        deadline = time.monotonic() + 15
        while self._read() < expected and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(0.2)  # room for an unexpected extra call to show up
        lines = self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []
        records = [json.loads(line) for line in lines]
        assert {r["checkout"] for r in records} <= {str(self.checkout)}
        return sorted(r["event"] for r in records)

    def _read(self) -> int:
        return len(self.log.read_text(encoding="utf-8").splitlines()) if self.log.exists() else 0


@pytest.fixture
def opencode(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    return OpenCode(tmp_path, node)


def created(session, parent=None):
    info = {"id": session, **({"parentID": parent} if parent else {})}
    return {"op": "event", "type": "session.created", "properties": {"info": info}}


def message(session):
    return {"op": "message", "session": session}


def request(session=None, system=None):
    return {"op": "request", "session": session, **({"system": system} if system else {})}


def event(kind, session):
    return {"op": "event", "type": kind, "properties": {"sessionID": session}}


def test_heading_matches_the_cli():
    assert f'const HEADING = "{hooks_mod.CONVENTION_HEADING}"' in PLUGIN.read_text(encoding="utf-8")


def test_startup_runs_once_and_every_request_gets_the_convention(opencode):
    out = opencode.play(created("s1"), message("s1"), request("s1"), request("s1"), message("s1"), request("s1"),
                        request(), request("s1", system=f"{BASE}\n{CONVENTION}"))
    assert out["requests"] == [[CONVENTION], [CONVENTION], [CONVENTION], [], []]
    assert opencode.calls(1) == ["startup"]


def test_a_session_not_seen_created_resumes(opencode):
    out = opencode.play(message("old"), request("old"), request("never-messaged"))
    assert out["requests"] == [[CONVENTION], []]
    assert opencode.calls(1) == ["resume"]


def test_compaction_refreshes_the_convention(opencode):
    out = opencode.play(created("s1"), message("s1"), event("session.compacted", "s1"), request("s1"),
                        event("session.compacted", "unseen"))
    assert out["requests"] == [[CONVENTION + " v2"]]
    assert opencode.calls(2) == ["compaction", "startup"]


def test_failed_compaction_keeps_the_cached_convention(opencode):
    opencode.behave(startup={"out": CONVENTION}, compaction={"out": "partial", "code": 1})
    out = opencode.play(created("s1"), message("s1"), event("session.compacted", "s1"), request("s1"))
    assert out["requests"] == [[CONVENTION]]


def test_idle_pushes_in_the_background_and_dispose_ends_each_root_session_once(opencode):
    opencode.play(created("s1"), message("s1"), message("s2"), event("session.idle", "s1"),
                  event("session.idle", "s1"), event("session.idle", "unseen"), {"op": "dispose"}, {"op": "dispose"})
    # Never a waiting full sync after the start: turn ends push, exit schedules one sync per session.
    assert opencode.calls(6) == ["resume", "session-end", "session-end", "startup", "turn-end", "turn-end"]


def test_children_get_no_convention_and_no_sync(opencode):
    opencode.parents = {"unseen-child": "s1"}
    out = opencode.play(created("s1"), message("s1"), created("c1", parent="s1"), message("c1"), request("c1"),
                        message("unseen-child"), request("unseen-child"), event("session.idle", "c1"),
                        event("session.compacted", "unseen-child"), {"op": "dispose"})
    assert out["requests"] == [[], []]
    assert opencode.calls(2) == ["session-end", "startup"]


def test_unwired_checkout_stays_silent(opencode):
    opencode.behave(startup={"out": ""})
    out = opencode.play(created("s1"), message("s1"), request("s1"), request("s1"), event("session.idle", "s1"))
    assert out["requests"] == [[], []]
    # Sync is the CLI's decision: turn ends still reach it.
    assert opencode.calls(2) == ["startup", "turn-end"]


def test_non_git_project_gets_no_session_hooks(opencode):
    opencode.vcs = None
    out = opencode.play(created("s1"), message("s1"), request("s1"), {"op": "dispose"})
    assert out["hooks"] == ["config"]
    assert opencode.calls() == []


def test_missing_cli_is_a_silent_no_op(opencode, tmp_path):
    out = opencode.play(created("s1"), message("s1"), request("s1"), event("session.idle", "s1"), {"op": "dispose"},
                        path=str(tmp_path / "empty"))
    assert out["requests"] == [[]]
    assert opencode.calls() == []


@pytest.mark.parametrize("startup", [{"out": CONVENTION, "code": 1}, {"out": CONVENTION, "sleep": 5}])
def test_cli_failures_fail_open(opencode, startup):
    opencode.fast_timers = True  # the 12 s cap, shortened
    opencode.behave(startup=startup)
    out = opencode.play(created("s1"), message("s1"), request("s1"), message("s1"), request("s1"))
    assert out["requests"] == [[], []]
    assert opencode.calls(1) == ["startup"]  # a failed start is not retried every request


def test_session_lookup_failure_counts_as_a_root_session(opencode):
    opencode.get_fails = True
    out = opencode.play(message("s1"), request("s1"))
    assert out["requests"] == [[CONVENTION]]
    assert opencode.calls(1) == ["resume"]
