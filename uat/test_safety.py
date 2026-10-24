"""Credential confinement, sandbox removal and isolation reporting, checked with fakes: no runtime, no credential."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

import backends
import conftest
from backends import HostBackend, redact, run_process, sanitized, sh_shim_script, shim_script
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
        HostBackend(root, repo=tmp_path, uv="uv")
    assert "UV_TOOL_DIR" in seen and "OPENAI_API_KEY" not in seen
    assert not root.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="the shim is a Windows .cmd")
def test_shim_drops_credentials_before_running_dotbrain(tmp_path):
    probe = tmp_path / "probe.py"
    probe.write_text("import os\nprint(os.environ.get('OPENAI_API_KEY'))\n")
    shim = tmp_path / "dotbrain.cmd"
    log = tmp_path / "calls.log"
    shim.write_text(shim_script(str(log), sys.executable, ["OPENAI_API_KEY"]), encoding="utf-8")
    done = run_process([str(shim), str(probe)], env={**os.environ, "OPENAI_API_KEY": SECRET}, cwd=tmp_path,
                       timeout=60)
    assert done.returncode == 0 and done.stdout.strip() == "None"
    assert str(probe) in log.read_text()


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
    backend = HostBackend.__new__(HostBackend)  # a built host sandbox, without installing dotbrain
    backend.root = root
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
