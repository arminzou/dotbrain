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
import shutil

import pytest

import backends
from conftest import CREDENTIAL_VARS, REPO
from evidence import MARKETPLACE, RUNTIMES, Runtime

ROLES = ("researcher", "reviewer", "verifier", "worker")
SKILLS = sorted(path.name for path in (REPO / "plugin" / "skills").iterdir() if (path / "SKILL.md").is_file())
# Runtimes omit skills only the user may invoke.
LISTED_SKILLS = [name for name in SKILLS
                 if "disable-model-invocation: true" not in (REPO / "plugin" / "skills" / name / "SKILL.md").read_text("utf-8")]
HOOKS = ("SessionStart", "Stop", "SessionEnd")
# What each listing must show for the claim in its row; keyed by (runtime, argv[:3]).
PLUGIN_NAMES = {"claude": ("dotbrain", *HOOKS), "codex": ("dotbrain",), "opencode": ("dotbrain",),
                "hermes": ("dotbrain",)}


def expected(rt: Runtime, argv: tuple[str, ...], proves: str) -> list[str]:
    if argv[:3] == ("opencode", "agent", "list"):
        return []  # built-in agents only: dotbrain delivers none to OpenCode
    if proves == "plugin-hooks":
        return list(PLUGIN_NAMES[rt.name])
    if proves == "skills":
        return LISTED_SKILLS
    if proves == "agents":  # Claude Code's /context lists both tables
        return [f"dotbrain-{role}" for role in ROLES] + LISTED_SKILLS
    raise AssertionError(f"no expectation for {proves}")


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
    if reason := box.unavailable(rt.name, rt.binary, rt.plugin_steps):
        pytest.skip(reason)

    def run(*argv, cwd=None):
        return box.run(list(argv), cwd=cwd, timeout=300)

    def ok(*argv, cwd=None):
        done = run(*argv, cwd=cwd)
        assert done.returncode == 0, f"{' '.join(argv)} -> {done.returncode}\n{done.stdout}\n{done.stderr}"
        return done.stdout

    request.node.user_properties.append(("runtime_version", ok(rt.binary, "--version").splitlines()[0].strip()))
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
    ok("dotbrain", "refresh", cwd=checkout)

    failures = []
    for listing in rt.listings:
        done = run(*listing.argv, cwd=checkout)
        text = done.stdout + done.stderr
        if done.returncode:
            failures.append(f"{' '.join(listing.argv)} exited {done.returncode}\n{text[-2000:]}")
            continue
        missing = [name for name in expected(rt, listing.argv, listing.proves) if name not in text]
        if missing:
            failures.append(f"{' '.join(listing.argv)} ({listing.proves}) lacks {missing}\n{text[-3000:]}")
    assert not failures, "\n\n".join(failures)
