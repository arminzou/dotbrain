"""Install and discovery journeys: no model, no credential, no login.

Per runtime, in a fresh container from the suite's image: bootstrap, wire a scratch project with all
four packaged subagents, refresh (Claude Code and Codex install the plugin from a local marketplace),
then run each listing in the runtime's evidence row and check that dotbrain's skills, `dotbrain-<role>`
subagents and plugin/hooks appear where the row says the listing proves them. Every assertion rests on
a real runtime binary reading what the clean install delivered. Runtimes with no listing get the
install journey only. Results are stamped by ``conftest`` (runtime version, image digest, revision).
"""

from __future__ import annotations

import json
import re
import shutil

import pytest

import backends
from conftest import CREDENTIAL_VARS, REPO
from evidence import MARKETPLACE, RUNTIMES

ROLES = ("researcher", "reviewer", "verifier", "worker")
SKILLS = sorted(path.name for path in (REPO / "plugin" / "skills").iterdir() if (path / "SKILL.md").is_file())
# Runtimes omit skills only the user may invoke.
LISTED_SKILLS = [name for name in SKILLS
                 if "disable-model-invocation: true" not in (REPO / "plugin" / "skills" / name / "SKILL.md").read_text("utf-8")]
SELECTED = "uat-probe"  # the scratch project's selected skill: only refresh delivers it
OPENCODE_HOME = "/root/.config/opencode"
PLUGIN_FILE = f"file://{OPENCODE_HOME}/plugins/dotbrain.js"


def problems(argv: tuple[str, ...], text: str) -> list[str]:
    """What the listing fails to show. Every check needs a token only dotbrain's delivery (or the plugin's
    install) produces, in the structure the runtime lists it by: a bare ``dotbrain`` matches paths and echoes.
    Claude Code and Codex list the plugin's own skills too, so their skill checks name only delivered things."""
    missing = []

    def need(found, what):
        if not found:
            missing.append(what)

    if argv[:3] == ("claude", "plugin", "list"):
        need(re.search(r"dotbrain@dotbrain\s+Version: \S+\s+Read from: \S+\s+Scope: user\s+Status: \S+ enabled\b", text),
             "dotbrain@dotbrain installed with status enabled")
    elif argv[:3] == ("claude", "plugin", "details"):
        need(re.search(r"Hooks \(\d+\)\s+SessionStart, Stop, SessionEnd", text), "the SessionStart, Stop, SessionEnd hooks")
    elif argv[:3] == ("claude", "-p", "/context"):
        for role in ROLES:
            need(re.search(rf"\| dotbrain-{role} \| Project \|", text), f"agent dotbrain-{role} from the project")
        need(re.search(rf"\| {SELECTED} \| ", text), f"skill {SELECTED}")
    elif argv[:3] == ("codex", "plugin", "list"):
        need(re.search(r"dotbrain@dotbrain\s+installed, enabled\s+\S+\s+\S+", text), "dotbrain@dotbrain installed, enabled")
    elif argv[:3] == ("codex", "debug", "prompt-input"):
        need(SELECTED in text, f"skill {SELECTED}")
    elif argv[:3] == ("opencode", "debug", "skill"):
        skills = {skill["name"]: skill["location"] for skill in json.loads(text)}
        root = f"{OPENCODE_HOME}/dotbrain/packaged/skills"
        wrong = [n for n in LISTED_SKILLS if not skills.get(n, "").startswith(f"{root}/{n}/")]
        need(not wrong, f"packaged skills under {root}: {wrong}")
        need(SELECTED in skills, f"skill {SELECTED}")
    elif argv[:3] == ("opencode", "debug", "config"):
        config = json.loads(text)
        need(PLUGIN_FILE in config.get("plugin", []), f"plugin {PLUGIN_FILE}")
        need(any(o["spec"] == PLUGIN_FILE and o["scope"] == "global" for o in config.get("plugin_origins", [])),
             "the plugin's global origin")
    elif argv[:3] == ("hermes", "plugins", "list"):
        need(re.search(r"^enabled\s+user\s+\S+\s+dotbrain$", text, re.M), "enabled user plugin dotbrain")
    else:
        raise AssertionError(f"no expectation for {argv}")
    return missing


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    pytest.importorskip("testcontainers", reason="install the uat group: uv sync --group uat")
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("install uv")
    if problem := backends.docker_problem():
        pytest.skip(problem)
    return backends.container_image(REPO, uv, tmp_path_factory.getbasetemp().parent, CREDENTIAL_VARS)


@pytest.mark.parametrize("rt", RUNTIMES, ids=lambda rt: rt.name)
def test_install_and_discovery(rt, image, request):
    tag, digest = image
    request.node.user_properties += [("runtime", rt.name), ("backend", "container"), ("image_digest", digest)]
    box = backends.ContainerBackend(tag)
    request.addfinalizer(box.teardown)  # before start, so a failing start still removes the container
    box.start()
    box.put_dir(REPO, (".claude-plugin", "plugin"), MARKETPLACE)
    if reason := box.unavailable(rt.name, rt.binary):
        pytest.skip(reason)
    box.install_plugin(rt.plugin_steps)

    def run(*argv, cwd=None):
        return box.run(list(argv), cwd=cwd, timeout=300)

    def ok(*argv, cwd=None):
        done = run(*argv, cwd=cwd)
        assert done.returncode == 0, f"{' '.join(argv)} -> {done.returncode}\n{done.stdout}\n{done.stderr}"
        return done.stdout

    request.node.user_properties.append(("runtime_version", box.version(rt.binary)))
    report = json.loads(ok("dotbrain", "bootstrap", "--runtime", rt.name, "--json"))
    skipped = [f["message"] for t in report["targets"] for f in t["findings"] if "skipped" in f["message"]]
    assert not skipped, f"bootstrap delivered nothing: {skipped}"

    checkout = box.checkout
    ok("git", "init", "-q", checkout)
    ok("git", "-C", checkout, "commit", "--allow-empty", "-q", "-m", "seed")
    ok("dotbrain", "wire", "--repo", checkout, "--project", "scratch", "--skip-beads")
    declaration = f"{box.data_root}/brainspaces/scratch/.brain/project.yaml"
    listed = box.read(declaration)
    if "packaged-subagents" not in listed:
        ok("sh", "-c", f"printf 'packaged-subagents:\\n' >> {declaration}"
           + "".join(f" && printf '  - {role}\\n' >> {declaration}" for role in ROLES))
    skill = f"{box.data_root}/skills/scratch/{SELECTED}"  # a private skill the project selects, as prepare.py does
    ok("mkdir", "-p", skill)
    ok("sh", "-c", f"printf -- '---\\nname: {SELECTED}\\ndescription: Probe skill. Use never.\\n---\\n\\nProbe.\\n' > {skill}/SKILL.md"
       f" && printf 'skills:\\n  - scratch/{SELECTED}\\n' >> {declaration}")
    ok("dotbrain", "refresh", cwd=checkout)

    failures = []
    for listing in rt.listings:
        done = run(*listing.argv, cwd=checkout)
        text = done.stdout + done.stderr
        if done.returncode:
            failures.append(f"{' '.join(listing.argv)} exited {done.returncode}\n{text[-2000:]}")
            continue
        missing = problems(listing.argv, text)
        if missing:
            failures.append(f"{' '.join(listing.argv)} ({listing.proves}) lacks {missing}\n{text[-3000:]}")
    assert not failures, "\n\n".join(failures)
