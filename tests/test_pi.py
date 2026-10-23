"""Pi delivery: the packaged extension's own logic and the CLI's owned copy in the Pi agent directory."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from dotbrain import __version__, assets, bootstrap, doctor, owned_copy, pi, resource_loader

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugin"


def _global_extra(dotbrain_home: Path, *names: str) -> None:
    listed = "".join(f"  - {name}\n" for name in names)
    (dotbrain_home / "skills/skills.yaml").write_text(f"global_extra:\n{listed}" if names else "global_extra: []\n")


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_extension_hands_pi_the_skills_beside_it(dotbrain_home, tmp_path):
    agent_dir = tmp_path / "user/.pi/agent"
    assets.link_global(dotbrain_home, "skills", "pi", user_home=tmp_path / "user")
    entry = pi.plugin_dir(agent_dir) / "index.js"
    # Load the delivered copy as Pi does, with a stand-in for Pi's extension API.
    script = (
        "const { pathToFileURL } = require('node:url');"
        "import(pathToFileURL(process.argv[1]).href).then(async (mod) => {"
        "  const handlers = {};"
        "  await mod.default({ on: (event, handler) => { handlers[event] = handler; } });"
        "  const result = await handlers.resources_discover({ type: 'resources_discover', cwd: '.', reason: 'startup' });"
        "  console.log(JSON.stringify({ events: Object.keys(handlers), result, version: mod.VERSION }));"
        "});"
    )
    out = subprocess.run(["node", "-e", script, str(entry)], check=True, capture_output=True, text=True).stdout
    reported = json.loads(out)
    assert reported["events"] == ["resources_discover", "session_start", "session_compact", "before_agent_start",
                                  "agent_settled", "session_shutdown"]
    assert [Path(p) for p in reported["result"]["skillPaths"]] == [entry.parent / "skills"]
    assert reported["version"] == __version__


def test_delivered_skills_are_the_sources_with_their_invocation_policy():
    """No forked prose: Pi reads each skill's own SKILL.md, whose flag matches the Codex policy."""
    with resource_loader.plugin_tree() as source:
        skills = sorted((source / "skills").glob("*/SKILL.md"))
    assert skills
    for skill in skills:
        metadata = yaml.safe_load((skill.parent / "agents/openai.yaml").read_text(encoding="utf-8"))
        explicit_only = not (metadata.get("policy") or {}).get("allow_implicit_invocation", True)
        assert _frontmatter(skill).get("disable-model-invocation", False) is explicit_only, skill.parent.name


def test_global_delivery_copies_the_extension_and_links_skills(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    agent_dir = user / ".pi/agent"
    mine = agent_dir / "skills/mine"
    mine.mkdir(parents=True)
    foreign_ext = agent_dir / "extensions/theirs"
    foreign_ext.mkdir(parents=True)
    _global_extra(dotbrain_home, "misc/discovery-test")

    result = assets.link_global(dotbrain_home, "skills", "pi", user_home=user)
    assert result.warnings == []
    assert (agent_dir / "skills/discovery-test").is_symlink()
    copy = pi.plugin_dir(agent_dir)
    assert sorted(p.name for p in copy.iterdir()) == [owned_copy.MARKER, "index.js", "skills"]
    assert (copy / "skills/run-execution/references/pi.md").is_file()
    assert pi.state(agent_dir) == "current"
    # Pi discovers the extension on its own; dotbrain writes no Pi settings.
    assert not (agent_dir / "settings.json").exists()
    assert not (user / ".pi/skills").exists()

    again = assets.link_global(dotbrain_home, "skills", "pi", user_home=user)
    assert again.linked == [] and again.warnings == []

    # A damaged copy is stale despite its marker; update replaces only the owned copy.
    for damage in (lambda: (copy / "index.js").write_text("changed"),
                   lambda: (copy / "skills/stray.txt").write_text("old"),
                   lambda: shutil.rmtree(copy / "skills/run-execution/references")):
        damage()
        assert pi.state(agent_dir) == "stale"
        assert assets.link_global(dotbrain_home, "skills", "pi", user_home=user).linked == ["pi/extensions/dotbrain"]
        assert pi.state(agent_dir) == "current"
    assert not (copy / "skills/stray.txt").exists()

    # Prune removes only dotbrain's skill links; foreign entries stay.
    _global_extra(dotbrain_home)
    pruned = assets.link_global(dotbrain_home, "skills", "pi", user_home=user)
    assert pruned.pruned == ["pi/discovery-test"]
    assert mine.is_dir() and foreign_ext.is_dir()
    assert sorted(p.name for p in (agent_dir / "extensions").iterdir()) == ["dotbrain", "theirs"]


def test_unfiltered_delivery_reaches_pi_only_once_opted_in(dotbrain_home, tmp_path, monkeypatch):
    user = tmp_path / "user"
    agent_dir = tmp_path / "relocated"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(agent_dir))
    _global_extra(dotbrain_home, "misc/discovery-test")
    assert bootstrap.link_global_skills(dotbrain_home, home=user).warnings == []
    assert not agent_dir.exists()

    assert bootstrap.link_global_skills(dotbrain_home, "pi", home=user).warnings == []
    assert not (user / ".pi").exists()
    (pi.plugin_dir(agent_dir) / "index.js").unlink()

    later = bootstrap.link_global_skills(dotbrain_home, home=user)
    assert "delivered global pi/extensions/dotbrain" in later.logs
    assert pi.state(agent_dir) == "current"
    assert (agent_dir / "skills/discovery-test").is_symlink()


def test_foreign_extension_and_skill_collisions_are_left_in_place(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    foreign = pi.plugin_dir(user / ".pi/agent")
    foreign.mkdir(parents=True)
    (foreign / "index.js").write_text("export default function () {}\n")
    result = assets.link_global(dotbrain_home, "skills", "pi", user_home=user)
    assert result.warnings == [f"{foreign} exists and was not created by dotbrain; skipping"]
    assert [p.name for p in foreign.iterdir()] == ["index.js"]
    # Not owned, so not opted in: an unfiltered run leaves Pi alone.
    assert bootstrap.link_global_skills(dotbrain_home, home=user).warnings == []

    own = user / ".pi/agent/skills/discovery-test"
    own.mkdir(parents=True)
    _global_extra(dotbrain_home, "misc/discovery-test")
    collided = assets.link_global(dotbrain_home, "skills", "pi", user_home=user)
    assert f"{own} exists and was not created by dotbrain; skipping" in collided.warnings
    assert own.is_dir() and not own.is_symlink()


def test_pi_has_no_subagent_delivery(dotbrain_home, tmp_path):
    with pytest.raises(ValueError, match="no native subagent delivery"):
        assets.link_global(dotbrain_home, "agents", "pi", user_home=tmp_path)


def test_doctor_reports_stale_pi_but_ignores_unowned_delivery(dotbrain_home, tmp_path):
    user = tmp_path / "user"
    agent_dir = user / ".pi/agent"
    assert not [f for f in doctor._check_machine(dotbrain_home, user) if f.message.startswith("pi:")]

    assets.link_global(dotbrain_home, "skills", "pi", user_home=user)
    findings = doctor._check_machine(dotbrain_home, user)
    assert {f.status for f in findings if f.message.startswith("pi:")} == {"ok"}
    # No packaged-agent demand: Pi has no native subagents.
    assert not [f for f in findings if "pi" in f.message.split(":")[0] and "agents" in f.message]

    (pi.plugin_dir(agent_dir) / "index.js").unlink()
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert f"pi: dotbrain extension copy is stale at {pi.plugin_dir(agent_dir)}" in warnings

    (dotbrain_home / "skills/skills.yaml").write_text(f"targets:\n  pi: {agent_dir / 'skills'}\nglobal_extra: []\n")
    shutil.rmtree(pi.plugin_dir(agent_dir))
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert not [message for message in warnings if message.startswith("pi:")]
    pi.plugin_dir(agent_dir).mkdir()
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert not [message for message in warnings if message.startswith("pi:")]


@pytest.mark.parametrize(("entries", "trusted"), [
    ({}, False),
    ({"{checkout}": True}, True),
    ({"{parent}": True}, True),
    ({"{parent}": True, "{checkout}": False}, False),
    ({"{parent}": False, "{checkout}": True}, True),
    ({"{other}": True}, False),
])
def test_trust_follows_the_nearest_decision(tmp_path, entries, trusted):
    checkout = tmp_path / "repos/app"
    checkout.mkdir(parents=True)
    names = {"{checkout}": str(checkout), "{parent}": str(checkout.parent), "{other}": str(tmp_path / "other")}
    (tmp_path / "trust.json").write_text(json.dumps({names[k]: v for k, v in entries.items()}), encoding="utf-8")
    assert pi.trusted(tmp_path, checkout) is trusted


# Session hooks: the extension maps Pi events onto `dotbrain hook run`. A stand-in `pi` drives the
# handlers; spawn is redirected to a fake CLI, and deliberately hung calls time out quickly.
FAKE_CLI = r"""
const [event] = process.argv.slice(5);
const mode = process.env.FAKE_MODE;
if (mode === "hang") setTimeout(() => {}, 5000);
else if (mode !== "unwired" && !["turn-end", "session-end"].includes(event)) {
  process.stdout.write(`## dotbrain convention\n\nBODY ${event}\n`);
}
if (mode === "fail") process.exitCode = 1;
"""
PI_DRIVER = r"""
const cp = require("node:child_process");
const { syncBuiltinESMExports } = require("node:module");
const { pathToFileURL } = require("node:url");
const [entry, fakeCli, stepsJson] = process.argv.slice(1);
const realSpawn = cp.spawn;
const spawns = [];
cp.spawn = (cmd, args, opts) => {
  const mode = process.env.FAKE_MODE;
  spawns.push({ cmd, args, detached: !!opts.detached, stdio: opts.stdio, windowsHide: opts.windowsHide });
  if (mode === "throw") throw new Error("spawn failed");
  return realSpawn(mode === "missing" ? "dotbrain-test-missing" : process.execPath,
                   mode === "missing" ? args : [fakeCli, ...args], opts);
};
syncBuiltinESMExports();
const timeouts = [];
const realSetTimeout = setTimeout;
globalThis.setTimeout = (fn, ms, ...rest) => {
  timeouts.push(ms);
  // Normal Node startup can exceed 500 ms on a busy parallel test runner.
  return realSetTimeout(fn, process.env.FAKE_MODE === "hang" ? Math.min(ms, 500) : ms, ...rest);
};
import(pathToFileURL(entry).href).then(async (mod) => {
  const handlers = {};
  mod.default({ on: (name, handler) => { handlers[name] = handler; } });
  const results = [];
  for (const [name, fields, cwd, stepMode] of JSON.parse(stepsJson)) {
    process.env.FAKE_MODE = stepMode;  // the fake CLI inherits it
    const event = { type: name, ...fields };
    if (name === "before_agent_start") event.systemPromptOptions = { sections: {} };
    const start = Date.now();
    let returned = null, threw = false;
    try { returned = handlers[name] ? (await handlers[name](event, { cwd })) ?? null : null; } catch { threw = true; }
    results.push({ returned, threw, sections: event.systemPromptOptions?.sections ?? null, ms: Date.now() - start });
  }
  console.log(JSON.stringify({ results, spawns, timeouts }));
});
"""


def _drive(tmp_path, steps, mode="wired"):
    """Run ``steps`` (``(event, fields[, mode])``) through the extension with checkout ``tmp_path``;
    a step's own mode overrides ``mode`` for the CLI calls it makes."""
    fake = tmp_path / "fake-dotbrain.js"
    fake.write_text(FAKE_CLI, encoding="utf-8")
    plan = json.dumps([[step[0], step[1], str(tmp_path), step[2] if len(step) > 2 else mode] for step in steps])
    out = subprocess.run(["node", "-e", PI_DRIVER, str(PLUGIN_ROOT / "index.js"), str(fake), plan],
                         env={**os.environ, "FAKE_MODE": mode}, check=True, capture_output=True, text=True).stdout
    report = json.loads(out)
    assert not any(r["threw"] for r in report["results"])
    for spawn in report["spawns"]:
        assert spawn["cmd"] == "dotbrain" and spawn["args"][:3] == ["hook", "run", "--event"]
        assert spawn["args"][4:] == ["--checkout", str(tmp_path)]
    return report


def _events(report):
    return [(s["args"][3], s["detached"]) for s in report["spawns"]]


def _section(event):
    return {"dotbrain": f"## dotbrain convention\n\nBODY {event}"}


START = ("before_agent_start", {"messageType": "user", "prompt": "hi"})
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@needs_node
def test_each_session_start_reason_runs_its_event_and_refreshes_the_section(tmp_path):
    mapping = {"startup": "startup", "resume": "resume", "new": "clear", "reload": "compaction", "fork": "compaction"}
    steps = [step for reason in mapping for step in (("session_start", {"reason": reason}), START)]
    report = _drive(tmp_path, steps)
    assert _events(report) == [(event, False) for event in mapping.values()]
    assert [r["sections"] for r in report["results"][1::2]] == [_section(e) for e in mapping.values()]
    assert set(report["timeouts"]) == {15_000}


@needs_node
def test_every_run_adds_the_cached_section_without_calling_the_cli_again(tmp_path):
    report = _drive(tmp_path, [("session_start", {"reason": "startup"}), START, START, START])
    assert _events(report) == [("startup", False)]
    runs = report["results"][1:]
    assert [r["sections"] for r in runs] == [_section("startup")] * 3
    assert all(r["returned"] is None for r in runs)  # no message: nothing lands in the history


@needs_node
def test_compaction_refreshes_the_section_without_a_full_sync(tmp_path):
    report = _drive(tmp_path, [("session_start", {"reason": "startup"}), START,
                               ("session_compact", {"reason": "threshold"}), START, START])
    assert _events(report) == [("startup", False), ("compaction", False)]
    assert [r["sections"] for r in report["results"][3:]] == [_section("compaction")] * 2


@needs_node
@pytest.mark.parametrize("mode", ["fail", "hang", "missing", "throw"])
def test_failed_compaction_refresh_keeps_the_convention(tmp_path, mode):
    report = _drive(tmp_path, [("session_start", {"reason": "startup"}),
                               ("session_compact", {"reason": "overflow"}, mode), START])
    assert report["results"][2]["sections"] == _section("startup")
    assert [event for event, _ in _events(report)] == ["startup", "compaction"]


@needs_node
def test_compaction_that_finds_the_checkout_unwired_clears_the_convention(tmp_path):
    report = _drive(tmp_path, [("session_start", {"reason": "startup"}),
                               ("session_compact", {"reason": "manual"}, "unwired"), START])
    assert report["results"][2]["sections"] == {}


@needs_node
def test_unwired_checkout_gets_no_section_but_still_reaches_sync(tmp_path):
    report = _drive(tmp_path, [("session_start", {"reason": "startup"}), START, START,
                               ("agent_settled", {"aborted": False}), ("session_shutdown", {"reason": "quit"})],
                    mode="unwired")
    assert [r["sections"] for r in report["results"][1:3]] == [{}, {}]
    assert _events(report) == [("startup", False), ("turn-end", True), ("session-end", False)]


@needs_node
def test_turn_settlement_pushes_in_the_background_and_never_runs_a_full_sync(tmp_path):
    report = _drive(tmp_path, [("session_start", {"reason": "startup"}), ("agent_end", {"messages": []}),
                               ("agent_settled", {"aborted": False}), ("session_compact", {"reason": "manual"}),
                               ("agent_settled", {"aborted": True})])
    assert _events(report) == [("startup", False), ("turn-end", True), ("compaction", False), ("turn-end", True)]
    for spawn in report["spawns"][1::2]:
        assert spawn["stdio"] == "ignore" and spawn["windowsHide"] is True


@needs_node
def test_background_launch_keeps_detached_hidden_spawn_options(tmp_path):
    report = _drive(tmp_path, [("agent_settled", {"aborted": False})])
    assert len(report["spawns"]) == 1
    assert {key: report["spawns"][0][key] for key in ("detached", "stdio", "windowsHide")} == {
        "detached": True, "stdio": "ignore", "windowsHide": True,
    }


@needs_node
@pytest.mark.parametrize("reason", ["quit", "reload", "new", "resume", "fork"])
def test_only_quit_schedules_a_full_sync(tmp_path, reason):
    report = _drive(tmp_path, [("session_shutdown", {"reason": reason})])
    if reason == "quit":
        assert _events(report) == [("session-end", False)] and report["timeouts"] == [5_000]
    else:
        assert report["spawns"] == []


@needs_node
@pytest.mark.parametrize("mode", ["fail", "hang", "missing", "throw"])
def test_cli_failures_fail_open(tmp_path, mode):
    report = _drive(tmp_path, [("session_start", {"reason": "startup"}), START, ("agent_settled", {"aborted": False}),
                               ("session_shutdown", {"reason": "quit"})], mode=mode)
    assert report["results"][1]["sections"] == {}
    assert [event for event, _ in _events(report)] == ["startup", "turn-end", "session-end"]
    assert report["results"][0]["ms"] < 4000  # bounded: the hung CLI is abandoned
