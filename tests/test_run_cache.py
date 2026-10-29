"""Per-run lookups: machine facts are asked once per command, and cost grows only per project."""
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from threading import Event

import pytest

from dotbrain import cursor, doctor, hermes, projects, run_cache, runtimes, workflows
from dotbrain.doctor import Finding

# The shipped, memoized lookup; conftest replaces it with a stub for every test.
SHIPPED_INSTALLED = runtimes.installed
# Subprocesses one more project may add to a repeat run, measured when the per-run cache landed.
PER_PROJECT_BUDGET = {"refresh": 5, "doctor": 2}


@pytest.fixture(scope="session")
def _repo_template(tmp_path_factory):
    repo = tmp_path_factory.mktemp("template") / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


@pytest.fixture(scope="session")
def _home_template(tmp_path_factory):
    home = tmp_path_factory.mktemp("template") / "home"
    home.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=home, check=True)
    return home


def _machine(tmp_path, home_template, repo_template, count):
    """A data root with ``count`` wired projects that deliver to Claude, Codex and Cursor."""
    home = tmp_path / "home"
    shutil.copytree(home_template, home)
    for index in range(count):
        name = f"project-{index}"
        brain = home / "brainspaces" / name / ".brain"
        brain.mkdir(parents=True)
        (brain / "project.yaml").write_text(
            "version: 2\nagents: [claude, codex, cursor]\nskills: []\nbeads: {mode: embedded}\n", encoding="utf-8")
        (brain / "AGENTS.md").write_text("Rules\n", encoding="utf-8")
        (brain.parent / ".beads").mkdir()
        (brain.parent / ".beads/metadata.json").write_text("{}", encoding="utf-8")
        checkout = tmp_path / name
        shutil.copytree(repo_template, checkout)
        (checkout / ".brain").symlink_to(brain, target_is_directory=True)
        (brain.parent / ".repo").write_text(str(checkout), encoding="utf-8")
    skills = Path.home() / ".claude/skills/shared"  # the conftest sandbox
    skills.mkdir(parents=True, exist_ok=True)
    (skills / "SKILL.md").write_text("---\nname: shared\n---\n", encoding="utf-8")
    return home


@pytest.fixture
def counters(monkeypatch, tmp_path):
    """Count each run's subprocesses, PATH lookups, machine-agent checks and Cursor home-folder reads."""
    counts = {"argv": [], "which": 0, "machine agents": 0, "home listings": Counter()}
    user = Path.home()
    commands = {runtimes.command(rt) for rt in runtimes.RUNTIMES.values()}
    which = shutil.which

    def counted_which(command, *args, **kwargs):
        if command not in commands:
            return which(command, *args, **kwargs)
        counts["which"] += 1
        return f"/fake/{command}" if command in ("claude", "codex") else None

    monkeypatch.setattr(runtimes, "installed", SHIPPED_INSTALLED)
    monkeypatch.setattr(shutil, "which", counted_which)
    owned = hermes.owned

    def counted_owned(directory):
        # Hermes is declared by no project, so only the machine-agent lookup and doctor's
        # one machine check ask whether it is set up.
        counts["machine agents"] += 1
        return owned(directory)

    monkeypatch.setattr(hermes, "owned", counted_owned)
    listing = cursor._listing

    def counted_listing(directory):
        if directory.is_relative_to(user):
            counts["home listings"][directory] += 1
        return listing(directory)

    monkeypatch.setattr(cursor, "_listing", counted_listing)

    def run(argv, **kwargs):
        counts["argv"].append([str(part) for part in argv])
        if argv[0] == "bd":
            stdout = "bd version 1.3.1" if "version" in argv else "[]"
            return subprocess.CompletedProcess(argv, 0, stdout, "")
        return workflows._default_run(argv, **kwargs)

    def reset():
        counts["argv"].clear()
        counts["which"] = 0
        counts["machine agents"] = 0
        counts["home listings"].clear()

    return counts, run, reset


def _refresh(home, run):
    result = workflows.refresh_projects(home, all_projects=True, run=run)
    assert not result.errors, result.errors


def _doctor(home, run, user):
    return doctor.run_doctor(home, user, all_projects=True, run=run)


def _repeat_run(command, tmp_path, home_template, repo_template, counters, count):
    counts, run, reset = counters
    home = _machine(tmp_path, home_template, repo_template, count)
    _refresh(home, run)  # the first run installs and links; the repeat run is the steady state
    reset()
    if command == "refresh":
        _refresh(home, run)
    else:
        _doctor(home, run, Path.home())
    return {"subprocesses": len(counts["argv"]),
            "exclude lookups": Counter(argv[2] for argv in counts["argv"] if "--git-common-dir" in argv
                                       and "--git-dir" not in argv),
            "machine": {"PATH lookups": counts["which"], "machine agent checks": counts["machine agents"],
                        "bd version": sum(argv[-1] == "version" for argv in counts["argv"]),
                        "most reads of one home folder": max(counts["home listings"].values(), default=0)}}


@pytest.mark.parametrize("command", ["refresh", "doctor"])
def test_machine_lookups_stay_constant_as_projects_grow(tmp_path, _home_template, _repo_template, counters, command):
    two = _repeat_run(command, tmp_path / "two", _home_template, _repo_template, counters, 2)
    four = _repeat_run(command, tmp_path / "four", _home_template, _repo_template, counters, 4)
    assert two["machine"] == four["machine"]
    assert four["machine"]["most reads of one home folder"] == 1
    assert four["machine"]["bd version"] == (1 if command == "doctor" else 0)
    assert four["subprocesses"] - two["subprocesses"] <= 2 * PER_PROJECT_BUDGET[command]
    if command == "refresh":
        # Each repository's exclude file is looked up once, however many entries refresh writes.
        assert len(four["exclude lookups"]) == 4 and set(four["exclude lookups"].values()) == {1}


def test_parallel_doctor_reports_projects_in_serial_order(tmp_path, _home_template, _repo_template, counters, monkeypatch):
    _, run, _ = counters
    home = _machine(tmp_path, _home_template, _repo_template, 4)
    _refresh(home, run)
    user = Path.home()
    targets = projects.select_projects(home, all_projects=True)
    with run_cache.scope():
        serial = {target.project: doctor._check_project(target, home.resolve(), run, skip_absent=True, home=user)
                  for target in targets}
    assert _doctor(home, run, user).projects == serial
    assert list(serial) == [f"project-{index}" for index in range(4)]

    # Release each project only after the previous completion was reported.
    ready = [Event() for _ in range(4)]
    ready[3].set()

    def check(target, *args, **kwargs):
        assert ready[int(target.project[-1])].wait(timeout=30), "previous project did not report completion"
        return [Finding("ok", target.project)]

    monkeypatch.setattr(doctor, "_check_project", check)
    progress = []

    def on_progress(name, completed, total):
        progress.append((name, completed, total))
        index = int(name[-1])
        if index:
            ready[index - 1].set()

    report = doctor.run_doctor(home, user, all_projects=True, run=run, progress=on_progress)
    assert [(name, [f.message for f in findings]) for name, findings in report.projects.items()] == [
        (f"project-{index}", [f"project-{index}"]) for index in range(4)]
    assert [step[1:] for step in progress] == [(1, 4), (2, 4), (3, 4), (4, 4)]
    assert [step[0] for step in progress] == [f"project-{index}" for index in (3, 2, 1, 0)]


def test_cache_is_off_outside_a_run_and_cleared_by_a_delivery(tmp_path):
    calls = []
    lookup = run_cache.memo(lambda value: calls.append(value) or value)
    lookup(1), lookup(1)
    assert calls == [1, 1]
    with run_cache.scope():
        lookup(1), lookup(1)
        assert calls == [1, 1, 1]
        run_cache.clear()  # an owned copy was installed or removed
        lookup(1)
        assert calls == [1, 1, 1, 1]
    lookup(1)
    assert calls == [1, 1, 1, 1, 1]


def test_cursor_delivery_sees_its_own_changes_within_a_run(tmp_path):
    home, user = tmp_path / "data", tmp_path / "user-home"
    (home / "skills/fresh").mkdir(parents=True)
    (home / "skills/fresh/SKILL.md").write_text("---\nname: fresh\n---\n", encoding="utf-8")
    receiver = user / ".cursor/skills"
    with run_cache.scope():
        assert "fresh" not in cursor.discovered(user)
        assert ".cursor/skills/fresh" in cursor.deliver(home, receiver, ["fresh"], scopes=(user,)).linked
        assert "fresh" in cursor.discovered(user)
