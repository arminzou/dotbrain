"""Credential confinement, sandbox removal and isolation reporting: fakes and inert markers, no runtime."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

import backends
import conftest
from backends import ContainerBackend, HostBackend, redact, run_process, sanitized, sh_shim_script
from observe import fingerprint

SECRET = "sk-synthetic-uat-secret"


def test_sanitized_drops_credentials_and_live_state_variables():
    env = sanitized({"PATH": "p", "OPENAI_API_KEY": SECRET, "ANTHROPIC_BASE_URL": "u", "XDG_CONFIG_HOME": "x",
                     "DOTBRAIN_HOME": "d", "SystemRoot": "s"})
    assert env == {"PATH": "p", "SystemRoot": "s"}


def test_failed_construction_installs_without_credentials_and_removes_the_sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", SECRET)
    seen = {}

    def failing_install(argv, *, env, **_kwargs):
        seen.update(env)
        raise subprocess.CalledProcessError(1, argv)

    monkeypatch.setattr(backends.subprocess, "run", failing_install)
    root = tmp_path / "sandbox"
    with pytest.raises(subprocess.CalledProcessError):
        HostBackend(root, repo=tmp_path, uv="uv").start()
    assert "UV_TOOL_DIR" in seen and "OPENAI_API_KEY" not in seen
    assert not root.exists()


# How each caller reaches `dotbrain` on PATH: Pi's adapter spawns the bare name without a shell;
# OpenCode's adapter walks PATH with PATHEXT and spawns the file it finds; prepare.py and the
# backends resolve through shutil.which.
_NODE_SPAWNS = {
    "node-shell-free": "const cli = 'dotbrain';",
    "node-pathext": ("const path = require('node:path'); const fs = require('node:fs');"
                     "const cli = process.env.PATH.split(path.delimiter).flatMap((dir) =>"
                     "  process.env.PATHEXT.split(';').map((ext) => path.join(dir, 'dotbrain' + ext)))"
                     "  .find((file) => fs.existsSync(file));"),
}
# Shell syntax, an expandable variable, and a spaced path ending in a backslash must all arrive literally.
_LITERAL_ARGS = ["hook", "run", "--checkout", "C:\\a&echo.INJECTED", "C:\\a^b", "C:\\a%UAT_MARKER% b",
                 "C:\\a b\\", 'say "hi"', ""]


@pytest.mark.skipif(sys.platform != "win32" or shutil.which("node") is None, reason="needs Windows and node")
@pytest.mark.parametrize("caller", [*_NODE_SPAWNS, "python-which"])
def test_shim_passes_arguments_literally_without_credentials_and_logs_once(tmp_path, caller):
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    probe = tmp_path / "probe.py"
    probe.write_text("import json, os, sys\nprint(json.dumps([os.environ.get('OPENAI_API_KEY'), sys.argv[2:]]))\n")
    log = tmp_path / "calls.log"
    backends.build_shim(shim_dir, str(log), sys.executable, ["OPENAI_API_KEY"])
    env = {**os.environ, "PATH": os.pathsep.join([str(shim_dir), os.environ["PATH"]]), "OPENAI_API_KEY": SECRET,
           "UAT_MARKER": "EXPANDED"}
    argv = [str(probe), "--", *_LITERAL_ARGS]  # the probe drops its own path and the separator
    if caller == "python-which":
        done = run_process(["dotbrain", *argv], env=env, cwd=tmp_path, timeout=60)
    else:
        spawning = (_NODE_SPAWNS[caller] + "const c = require('node:child_process').spawn(cli, process.argv.slice(1));"
                    "c.stdout.pipe(process.stdout); c.on('close', (code) => process.exit(code));")
        done = run_process(["node", "-e", spawning, *argv], env=env, cwd=tmp_path, timeout=60)
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [json.dumps([None, _LITERAL_ARGS])]  # nothing else ran or printed
    assert len(log.read_text().splitlines()) == 1 and "hook run --checkout" in log.read_text()


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX sh")
def test_sh_shim_drops_credentials_before_running_dotbrain(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text("import os\nprint(os.environ.get('OPENAI_API_KEY'))\n")
    shim = tmp_path / "dotbrain"
    log = tmp_path / "calls.log"
    shim.write_text(sh_shim_script(log.as_posix(), sys.executable, ["OPENAI_API_KEY"]), encoding="utf-8",
                    newline="\n")
    done = run_process(["sh", str(shim), probe.as_posix()], env={**os.environ, "OPENAI_API_KEY": SECRET},
                       cwd=tmp_path, timeout=60)
    assert done.returncode == 0 and done.stdout.strip() == "None"
    assert probe.as_posix() in log.read_text()


def test_process_output_is_redacted(tmp_path):
    env = {**os.environ, "UAT_PROBE": SECRET}
    printing = "import os, sys; print(os.environ['UAT_PROBE']); print(os.environ['UAT_PROBE'], file=sys.stderr)"
    done = run_process([sys.executable, "-c", printing], env=env, cwd=tmp_path, timeout=60, secrets=[SECRET])
    assert SECRET not in done.stdout + done.stderr and "[redacted]" in done.stdout
    with pytest.raises(AssertionError) as timed_out:
        run_process([sys.executable, "-c", printing + "; sys.stdout.flush(); import time; time.sleep(60)"],
                    env=env, cwd=tmp_path, timeout=3, secrets=[SECRET])
    assert SECRET not in str(timed_out.value)
    assert redact("a sk-x b", ["", "sk-x"]) == "a [redacted] b"


def test_image_build_lock_is_exclusive_and_released(tmp_path):
    lock = tmp_path / "image.lock"
    with backends._locked(lock):
        with pytest.raises(TimeoutError), backends._locked(lock, seconds=0):
            pass
    assert not lock.exists()


def _sandbox_with_leak_and_live_change(tmp_path):
    root, live = tmp_path / "sandbox", tmp_path / "live"
    (root / "logs").mkdir(parents=True)
    (root / "logs" / "run.log").write_text(f"key={SECRET}")
    live.mkdir()
    before = fingerprint([live])
    (live / "touched").write_text("x")
    backend = HostBackend(root, repo=tmp_path, uv="uv")  # the handle to a sandbox, not started here
    return backend, live, before


def test_close_sandbox_reports_every_violation_and_removes_the_sandbox(tmp_path):
    backend, live, before = _sandbox_with_leak_and_live_change(tmp_path)
    problems = conftest.close_sandbox(backend, [SECRET], [live], before)
    assert any(p.startswith("credential written to") for p in problems)
    assert any(p.startswith("live path changed") for p in problems)
    assert not backend.root.exists()


def test_close_sandbox_still_checks_isolation_when_removal_fails(tmp_path, monkeypatch):
    backend, live, before = _sandbox_with_leak_and_live_change(tmp_path)

    def stuck(_root):
        raise PermissionError("held by a running process")

    monkeypatch.setattr(backends, "remove_tree", stuck)
    problems = conftest.close_sandbox(backend, [SECRET], [live], before)
    for prefix in ("credential written to", "sandbox not removed", "live path changed"):
        assert any(p.startswith(prefix) for p in problems), problems


def test_failed_start_whose_own_cleanup_fails_is_removed_by_close(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"

    def partial_build(self, root, *_args):
        (root / "home").mkdir(parents=True)
        raise RuntimeError("install failed")

    real_remove, calls = backends.remove_tree, []

    def flaky_remove(path):
        calls.append(path)
        if len(calls) == 1:
            raise PermissionError("held by a running process")
        real_remove(path)

    monkeypatch.setattr(HostBackend, "_build", partial_build)
    monkeypatch.setattr(backends, "remove_tree", flaky_remove)
    backend = HostBackend(root, repo=tmp_path, uv="uv")
    with pytest.raises(RuntimeError, match="install failed"):
        backend.start()
    assert root.exists()
    assert conftest.close_sandbox(backend, [SECRET], [], {}) == []
    assert len(calls) == 2 and not root.exists()


def _container_backend():
    pytest.importorskip("testcontainers", reason="install the uat group: uv sync --group uat")
    if problem := backends.docker_problem():
        pytest.skip(problem)
    # Only the image's base: the check needs sh, coreutils and grep, not the runtime or a build.
    base = re.search(r"^FROM\s+(\S+)", (backends.HERE / "Dockerfile").read_text(encoding="utf-8"), re.M).group(1)
    return ContainerBackend(base)


def test_container_output_never_reaches_a_file_and_is_redacted():
    backend = _container_backend()
    try:
        backend.start()
        printing = 'printf "%s\\n" "$UAT_PROBE"; printf "%s\\n" "$UAT_PROBE" >&2; sleep 6'
        with ThreadPoolExecutor(1) as pool:
            running = pool.submit(backend.run, ["sh", "-c", printing], env={"UAT_PROBE": SECRET}, cwd="/")
            time.sleep(3)
            during = backend.leaks(SECRET)
            done = running.result()
        assert during == [] and backend.leaks(SECRET) == []
        assert SECRET not in done.stdout + done.stderr
        assert done.stdout.strip() == done.stderr.strip() == "[redacted]"
        # Output past a pipe's 64 KiB still arrives whole.
        assert len(backend.run(["sh", "-c", "head -c 200000 /dev/zero | tr '\\0' x"], cwd="/").stdout) == 200000
    finally:
        backend.teardown()
