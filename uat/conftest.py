"""Runtime delivery UAT: qualify what agent runtimes load from dotbrain, in disposable sandboxes.

Opt-in: ``uv run --group uat pytest uat``. Plain ``uv run pytest`` never collects this directory,
and ``tests/conftest.py`` is not loaded here: its guard fails any test that launches a runtime.

A journey runs only when its runtime is installed and its credential is set; otherwise it skips,
naming what to set, before any runtime process starts or any sandbox exists. Each journey checks
that the live runtime config and the live data root are unchanged, removes its sandbox, and is
stamped with runtime version, OS and dotbrain revision in the report and in ``uat/results.json``.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import pytest

from backends import Backend, HostBackend, remove_tree
from observe import changed, fingerprint, nonce

REPO = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).resolve().parent / "results.json"
PREPARE = Path(__file__).resolve().parent / "prepare.py"

# The only variables a journey treats as a credential. A runtime's model variable names
# provider/model; the provider's key variable must be set too, and only that one reaches the runtime.
MODEL_VARS = {"opencode": "UAT_OPENCODE_MODEL"}
PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
COMMANDS = {"opencode": "opencode"}


@cache
def revision() -> str:
    """The checkout under test: its commit, marked when the working tree differs from it."""
    def git(*args):
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()

    head = git("rev-parse", "HEAD") or "unknown"
    return head + ("+dirty" if git("status", "--porcelain") else "")


def os_name() -> str:
    return platform.platform()


def credential(runtime: str) -> tuple[str, dict[str, str]] | str:
    """``(model, {key variable: value})``, or what to set when it is missing."""
    model_var = MODEL_VARS[runtime]
    model = os.environ.get(model_var, "")
    provider = model.split("/", 1)[0]
    if provider not in PROVIDER_KEYS:
        keys = ", ".join(f"{name} ({var})" for name, var in PROVIDER_KEYS.items())
        return f"set {model_var}=<provider>/<model> and the provider's key; providers: {keys}"
    key = PROVIDER_KEYS[provider]
    if not os.environ.get(key):
        return f"set {key} for {model_var}={model}"
    return model, {key: os.environ[key]}


def live_roots(runtime: str) -> list[Path]:
    """The live runtime config dirs and the live data root, which no journey may change."""
    home = Path.home()

    def xdg(var, default):
        return Path(os.environ.get(var) or home / default)

    runtime_dirs = {
        "opencode": [xdg("XDG_CONFIG_HOME", ".config") / "opencode", xdg("XDG_DATA_HOME", ".local/share") / "opencode",
                     xdg("XDG_STATE_HOME", ".local/state") / "opencode", xdg("XDG_CACHE_HOME", ".cache") / "opencode"],
    }[runtime]
    return runtime_dirs + [Path(os.environ.get("DOTBRAIN_HOME") or home / "dotbrain")]


def leaks(root: Path, secret: str) -> list[str]:
    """Files below ``root`` that contain ``secret``."""
    needle = secret.encode()
    found = []
    for top, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(top, name)
            try:
                with open(path, "rb") as handle:
                    if needle in handle.read():
                        found.append(path)
            except OSError:
                continue
    return found


@dataclass
class Sandbox:
    backend: Backend
    exe: str  # the runtime binary, resolved before the environment swap
    model: str
    credentials: dict[str, str] = field(repr=False)
    convention_nonce: str = ""
    reference_nonce: str = ""

    def runtime(self, *args: str, timeout: float = 300):
        """Run the runtime in the checkout; only this process gets the credential."""
        return self.backend.run([self.exe, *args], env=self.credentials, cwd=self.backend.checkout, timeout=timeout)


@pytest.fixture(params=["host", "container"])
def sandbox(request, tmp_path):
    runtime = request.module.RUNTIME
    props = request.node.user_properties
    props += [("runtime", runtime), ("backend", request.param)]
    if request.param == "container":
        pytest.importorskip("testcontainers", reason="install the uat group: uv sync --group uat")
        pytest.skip("the container backend is not available yet; run the host backend on Windows")
    if sys.platform != "win32":
        pytest.skip("the host backend qualifies native Windows; run it there")
    missing = []
    exe = shutil.which(COMMANDS[runtime])
    if exe is None:
        missing.append(f"install {runtime} so `{COMMANDS[runtime]}` is on PATH")
    found = credential(runtime)
    if isinstance(found, str):
        missing.append(found)
    uv = shutil.which("uv")
    if uv is None:
        missing.append("install uv")
    if missing:
        pytest.skip("; ".join(missing))
    model, credentials = found
    props.append(("model", model))

    roots = live_roots(runtime)
    before = fingerprint(roots)
    root = tmp_path / "sandbox"

    # Registered before the sandbox exists, so a failing construction, preparation or journey still
    # removes it and still reports every isolation violation, beside the original failure.
    def finalize():
        problems = close_sandbox(root, credentials.values(), roots, before)
        assert not problems, "\n".join(problems)

    request.addfinalizer(finalize)
    backend = HostBackend(root, repo=REPO, uv=uv, credential_vars=PROVIDER_KEYS.values())
    session = Sandbox(backend, exe, model, credentials, nonce("convention"), nonce("reference"))
    prepared = backend.run([backend.python, str(PREPARE), "--runtime", runtime, "--checkout", backend.checkout,
                            "--convention-nonce", session.convention_nonce,
                            "--reference-nonce", session.reference_nonce], timeout=300)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    props.append(("runtime_version", backend.run([exe, "--version"]).stdout.strip()))
    return session


def close_sandbox(root: Path, secrets, roots, before) -> list[str]:
    """Scan for leaked credentials, remove the sandbox, and compare the live roots; each step runs
    whatever the others did. Returns every violation found."""
    problems = []
    try:
        for secret in secrets:
            problems += [f"credential written to {path}" for path in leaks(root, secret)]
    except Exception as error:  # noqa: BLE001 - the remaining checks must still run
        problems.append(f"credential scan failed: {error!r}")
    try:
        remove_tree(root)
    except Exception as error:  # noqa: BLE001
        problems.append(f"sandbox not removed: {root}: {error!r}")
    try:
        problems += [f"live path changed: {path}" for path in changed(before, fingerprint(roots))]
    except Exception as error:  # noqa: BLE001
        problems.append(f"isolation guard failed: {error!r}")
    return problems


# Result stamping. Workers forward their reports to the controller, which writes the results file.
_results: dict[str, dict] = {}


def pytest_report_header(config):
    return [f"dotbrain revision: {revision()}", f"OS: {os_name()}"]


def pytest_runtest_logreport(report):
    props = dict(report.user_properties)
    if "runtime" not in props:
        return
    record = _results.setdefault(report.nodeid, {"test": report.nodeid, "outcome": "passed"})
    record.update(props)
    if report.failed:
        record["outcome"] = "failed" if report.when == "call" else "error"
    elif report.skipped:
        record["outcome"] = "skipped"
        if isinstance(report.longrepr, tuple):
            record["reason"] = report.longrepr[2].removeprefix("Skipped: ")


def _stamped() -> list[dict]:
    return [{**record, "os": os_name(), "dotbrain_revision": revision()} for record in _results.values()]


def pytest_sessionfinish(session):
    if hasattr(session.config, "workerinput") or not _results:
        return
    RESULTS.write_text(json.dumps(_stamped(), indent=2) + "\n", encoding="utf-8")


def pytest_terminal_summary(terminalreporter):
    if not _results:
        return
    terminalreporter.section("runtime delivery results")
    for record in _stamped():
        terminalreporter.write_line(
            f"{record['outcome']:8} {record['test']}  {record.get('runtime_version') or '-'}  "
            f"{record['os']}  dotbrain {record['dotbrain_revision']}")
    terminalreporter.write_line(f"results: {RESULTS}")
