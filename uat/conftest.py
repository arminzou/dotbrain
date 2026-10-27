"""Runtime delivery UAT: qualify what agent runtimes load from dotbrain, in a Linux container.

Opt-in: ``uv run --group uat pytest uat``; it needs Docker and makes no model call. Plain
``uv run pytest`` never collects this directory, and ``tests/conftest.py`` is not loaded here.

Each journey runs in a fresh container and is stamped with runtime version, image digest, OS and
dotbrain revision in the report and in ``uat/results.json``.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
from functools import cache
from pathlib import Path

import pytest

import backends

REPO = Path(__file__).resolve().parent.parent
RESULTS = Path(__file__).resolve().parent / "results.json"


@cache
def revision() -> str:
    """The checkout under test: its commit, marked when the working tree differs from it."""
    def git(*args):
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True).stdout.strip()

    head = git("rev-parse", "HEAD") or "unknown"
    return head + ("+dirty" if git("status", "--porcelain") else "")


def os_name() -> str:
    return platform.platform()


@pytest.fixture(scope="module")
def image(tmp_path_factory):
    """The suite's image: ``(tag, image id)``, built once per checkout state and shared by every worker."""
    pytest.importorskip("testcontainers", reason="install the uat group: uv sync --group uat")
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("install uv")
    if problem := backends.docker_problem():
        pytest.skip(problem)
    return backends.container_image(REPO, uv, tmp_path_factory.getbasetemp().parent)


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
        image = f"  image {record['image_digest']}" if "image_digest" in record else ""
        terminalreporter.write_line(
            f"{record['outcome']:8} {record['test']}  {record.get('runtime_version') or '-'}  "
            f"{record['os']}{image}  dotbrain {record['dotbrain_revision']}")
    terminalreporter.write_line(f"results: {RESULTS}")
