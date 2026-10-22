"""Pi delivery: the packaged extension's own logic and the CLI's owned copy in the Pi agent directory."""

import json
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
    assert reported["events"] == ["resources_discover"]
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


def test_doctor_reports_missing_stale_and_foreign_pi_delivery(dotbrain_home, tmp_path):
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
    assert "pi: dotbrain extension is not delivered" in warnings
    pi.plugin_dir(agent_dir).mkdir()
    warnings = {f.message for f in doctor._check_machine(dotbrain_home, user) if f.status == "warn"}
    assert f"pi: {pi.plugin_dir(agent_dir)} is not dotbrain's extension copy" in warnings


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
