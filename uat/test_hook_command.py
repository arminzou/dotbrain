"""No-model hook journey: run each runtime's configured session hooks in a fresh container.

Per runtime the container gets the clean install (the plugin runtimes install from a local marketplace),
``prepare.py`` delivers and wires a scratch project, and the hook command is read from the runtime's
delivered config, then run under the container's ``sh`` exactly as configured. No model, login or credential.

Where the runtime's hook is plugin code rather than a shell command (OpenCode, Pi, Hermes), the delivered
file is checked for the argv it spawns and for its timeout, and that argv is run as the plugin would.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import time
from dataclasses import dataclass

import pytest

import backends
import evidence
from conftest import CREDENTIAL_VARS, REPO
from observe import nonce
from prepare import PENDING


@dataclass
class Hooks:
    start: str  # the session-start command line
    start_seconds: float  # the runtime's own limit for it
    end: str  # the session-end command line (a full home sync)
    env: dict[str, str]


def _find(backend, *args) -> str:
    return backend.run(["find", *args]).stdout.split("\n")[0]


def _config_hooks(backend, path, start_key, end_key, *, nested) -> Hooks:
    """Hook commands from a JSON config. ``nested``: Claude/Codex layout, with a ``hooks`` list per matcher."""
    config = json.loads(backend.read(path))["hooks"]
    entries = {key: (config[key][0]["hooks"][0] if nested else config[key][0]) for key in (start_key, end_key)}
    return Hooks(entries[start_key]["command"], entries[start_key]["timeout"], entries[end_key]["command"], {})


def delivered_hooks(backend, name) -> Hooks:
    checkout = backend.checkout
    if name in ("claude", "codex"):
        cache = {"claude": "/root/.claude/plugins/cache", "codex": "/root/.codex/plugins/cache"}[name]
        path = _find(backend, cache, "-path", "*/hooks/hooks.json")
        assert path, f"no hooks.json delivered under {cache}"
        return _config_hooks(backend, path, "SessionStart", "SessionEnd", nested=True)
    if name == "cursor":
        hooks = _config_hooks(backend, "/root/.cursor/hooks.json", "sessionStart", "sessionEnd", nested=False)
        hooks.env = {"CURSOR_PROJECT_DIR": checkout}  # what Cursor sets for its hooks
        return hooks
    # Plugin code: the delivered file builds the spawned argv, names the events its start and end paths send,
    # and holds the start timeout. All three are read from it, so a changed flag or event mapping fails.
    path, seconds_pattern, scale, start_event, end_event = {
        "opencode": ("/root/.config/opencode/plugins/dotbrain.js", r"START_TIMEOUT_MS = ([\d_]+)", 1000,
                     r'created\.has\(sessionID\) \? "(\w[\w-]*)"', r'busy\.has\(id\) \? "turn-end" : "([\w-]+)"'),
        "pi": ("/root/.pi/agent/extensions/dotbrain/index.js", r"START_TIMEOUT_MS = ([\d_]+)", 1000,
               r'startup: "([\w-]+)"', r'run\("([\w-]+)", ctx\.cwd, END_TIMEOUT_MS'),
        "hermes": ("/root/.hermes/plugins/dotbrain/__init__.py", r"START_TIMEOUT = (\d+)", 1,
                   r'"([\w-]+)" if is_first_turn', r'_hook_run\("([\w-]+)", END_TIMEOUT'),
    }[name]
    source = backend.read(path)
    template = re.search(r'\[(?:exe, )?("hook", [^\]]*)\]', source)
    assert template, f"{path} builds no `hook` argv"
    seconds = int(re.search(seconds_pattern, source).group(1).replace("_", "")) / scale

    def command(event_pattern):
        event = re.search(event_pattern, source)
        assert event, f"{path} has no call matching {event_pattern}"
        slots = {"event": event.group(1), "checkout": checkout, "_checkout()": checkout}
        argv = [item.strip('"') if item.startswith('"') else slots[item] for item in template.group(1).split(", ")]
        return shlex.join(["dotbrain", *argv])  # what the plugin spawns, no shell

    return Hooks(command(start_event), seconds, command(end_event), {})


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    pytest.importorskip("testcontainers", reason="install the uat group: uv sync --group uat")
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("install uv")
    if problem := backends.docker_problem():
        pytest.skip(problem)
    return backends.container_image(REPO, uv, tmp_path_factory.getbasetemp().parent, CREDENTIAL_VARS)


@pytest.fixture(params=[r.name for r in evidence.RUNTIMES])
def container(request, image):
    """A fresh container with the runtime installed and a scratch project delivered and wired."""
    name = request.param
    tag, digest = image
    rt = evidence.runtime(name)
    request.node.user_properties += [("runtime", name), ("backend", "container"), ("image_digest", digest)]
    backend = backends.ContainerBackend(tag)
    request.addfinalizer(backend.teardown)  # registered before the container exists
    backend.start()
    backend.put_dir(REPO, (".claude-plugin", "plugin"), evidence.MARKETPLACE)
    if reason := backend.unavailable(name, rt.binary):
        pytest.skip(reason)
    backend.install_plugin(rt.plugin_steps)
    request.node.user_properties.append(("runtime_version", backend.version(rt.binary)))
    convention_nonce = nonce("convention")
    prepared = backend.run([backend.python, backend.prepare, "--runtime", name, "--checkout", backend.checkout,
                            "--convention-nonce", convention_nonce, "--reference-nonce", nonce("reference")],
                           timeout=300)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    return name, backend, convention_nonce


def test_configured_hook_prints_convention_and_syncs_home(container):
    name, backend, convention_nonce = container
    hooks = delivered_hooks(backend, name)

    # The configured session-start command, as the runtime hands it to the shell. The data root's remote is
    # unroutable (TEST-NET-1), so a hook that waited on the network would run to the runtime's limit.
    started = time.monotonic()
    start = backend.run(["sh", "-c", hooks.start], env=hooks.env, timeout=hooks.start_seconds)
    elapsed = time.monotonic() - started
    assert start.returncode == 0, start.stdout + start.stderr
    assert elapsed < hooks.start_seconds, f"{hooks.start} took {elapsed:.1f} s of {hooks.start_seconds} s"
    assert convention_nonce in start.stdout, start.stdout[-2000:]
    # The convention ends in its marker; Cursor wraps it in JSON, so the marker closes the string there.
    assert re.search(rf"{re.escape(convention_nonce)}\s*(\\n)*\W*\s*$", start.stdout), start.stdout[-500:]

    # Home sync via the configured session-end command: it commits the pending change locally while the
    # push fails, leaving the data root ahead of its upstream.
    end = backend.run(["sh", "-c", hooks.end], env=hooks.env, timeout=60)
    assert end.returncode == 0, end.stdout + end.stderr
    git = lambda *args: backend.run(["git", "-C", backend.data_root, *args]).stdout.strip()  # noqa: E731
    deadline = time.monotonic() + 60
    while not (committed := git("log", "--format=%s", "--", PENDING)) and time.monotonic() < deadline:
        time.sleep(1)
    assert committed, "session-end recorded no commit of the pending change"
    assert int(git("rev-list", "--count", "@{upstream}..HEAD")) >= 1
