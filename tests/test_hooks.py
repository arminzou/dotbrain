"""Tests for the SessionStart hook's Brain-context assembly.

This ran as a packaged bash script until the Windows chain proved unreliable; these
tests pin the behavior the script had, including byte-exact passthrough of Brain files.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import time
import threading
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import home_sync, hooks, resource_loader
from dotbrain.cli import app


def _repo(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    return repo


def _wire(repo: Path, convention: bytes | None = None, agents: bytes | None = None) -> None:
    brain = repo / ".brain"
    brain.mkdir()
    if convention is not None:
        (brain / "DOTBRAIN.md").write_bytes(convention)
    if agents is not None:
        (brain / "AGENTS.md").write_bytes(agents)


def test_emits_nothing_outside_a_git_repo(tmp_path: Path):
    assert hooks.brain_context(cwd=tmp_path) == b""


def test_emits_nothing_without_a_brain(tmp_path: Path):
    assert hooks.brain_context(cwd=_repo(tmp_path)) == b""


def test_emits_nothing_when_the_brain_is_empty(tmp_path: Path):
    repo = _repo(tmp_path)
    _wire(repo)
    assert hooks.brain_context(cwd=repo) == b""


def test_emits_the_convention(tmp_path: Path):
    repo = _repo(tmp_path, "my-project")
    _wire(repo, convention=b"CONVENTION BODY\n")

    payload = hooks.brain_context(cwd=repo).decode("utf-8")

    assert payload == "## dotbrain convention\n\nCONVENTION BODY\n\n\n"


def test_project_agents_is_never_injected(tmp_path: Path):
    """It grows with the project; injecting it would eventually truncate the whole payload."""

    repo = _repo(tmp_path)
    _wire(repo, convention=b"CONVENTION BODY\n", agents=b"PROJECT SECRET SAUCE\n")

    payload = hooks.brain_context(cwd=repo).decode("utf-8")

    assert "PROJECT SECRET SAUCE" not in payload
    assert "## Project brain" not in payload


def test_emits_nothing_with_only_project_rules(tmp_path: Path):
    repo = _repo(tmp_path)
    _wire(repo, agents=b"ONLY PROJECT RULES\n")

    assert hooks.brain_context(cwd=repo) == b""


def test_brain_bytes_pass_through_verbatim(tmp_path: Path):
    """No newline translation and no re-encoding — the payload is what ``cat`` produced."""

    repo = _repo(tmp_path)
    body = "line one\r\nline two\r\ncaf\u00e9 na\u00efve\r\n".encode("utf-8")
    _wire(repo, convention=body)

    assert body in hooks.brain_context(cwd=repo)


def test_emit_writes_to_the_given_stream(tmp_path: Path):
    repo = _repo(tmp_path)
    _wire(repo, convention=b"BODY\n")
    buffer = io.BytesIO()

    hooks.emit_brain_context(stream=buffer, cwd=repo)

    assert b"BODY\n" in buffer.getvalue()


def test_emit_is_silent_and_fail_open_without_a_brain(tmp_path: Path):
    buffer = io.BytesIO()
    hooks.emit_brain_context(stream=buffer, cwd=_repo(tmp_path))
    assert buffer.getvalue() == b""


def test_packaged_convention_stays_under_the_payload_limit():
    """Over the limit the runtime spills stdout to a file and the model receives none of it."""

    with resource_loader.resource_file("templates/brain/DOTBRAIN.md") as path:
        body = path.read_bytes()

    payload = len(f"{hooks.CONVENTION_HEADING}\n\n".encode("utf-8")) + len(body) + 2
    assert payload < hooks.PAYLOAD_LIMIT, (
        f"injected convention is {payload} bytes, over the {hooks.PAYLOAD_LIMIT} limit; "
        "trim DOTBRAIN.md or move detail into a skill"
    )


# --- Home sync from the session hooks ------------------------------------------------------

CLI = "from dotbrain.cli import app; app()"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          encoding="utf-8").stdout.strip()


def _home(tmp_path: Path, remote: Path, name: str = "home") -> Path:
    home = tmp_path / name
    home.mkdir()
    for args in (("init", "-q", "-b", "main"), ("config", "user.name", "Test"),
                 ("config", "user.email", "test@example.com"), ("config", "core.autocrlf", "false")):
        _git(home, *args)
    brain = home / "brainspaces" / "alpha" / ".brain"
    brain.mkdir(parents=True)
    (brain / "CONTEXT.md").write_text("x\n", encoding="utf-8")
    (home / "brainspaces" / "alpha" / ".beads").mkdir()
    _git(home, "add", "-A")
    _git(home, "commit", "-q", "-m", "initial")
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    _git(home, "remote", "add", "origin", str(remote))
    _git(home, "push", "-q", "-u", "origin", "main")
    return home


def _wired_checkout(tmp_path: Path, home: Path, name: str = "checkout",
                    links: tuple[str, ...] = (".brain", ".beads")) -> Path:
    checkout = _repo(tmp_path, name)
    for link in links:
        (checkout / link).symlink_to(home / "brainspaces" / "alpha" / link)
    return checkout


def _hook(event: str, cwd: Path, home: Path, stdin: bytes = b"") -> tuple[subprocess.CompletedProcess, float]:
    # -I as the installed `dotbrain` script behaves: the working directory is not on sys.path.
    started = time.monotonic()
    completed = subprocess.run([sys.executable, "-I", "-c", CLI, "hook", event], cwd=cwd, input=stdin,
                               capture_output=True, env={**os.environ, "DOTBRAIN_HOME": str(home)}, timeout=60)
    return completed, time.monotonic() - started


def _eventually(check, seconds: float = 60) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.2)
    return False


@pytest.fixture
def launches(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    started: list[list[str]] = []

    class Done:
        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(hooks, "_launch_detached", lambda argv, cwd: started.append(argv) or Done())
    return started


def test_child_is_detached_without_a_visible_console(tmp_path: Path, monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(hooks.subprocess, "Popen", lambda argv, **kwargs: seen.update(kwargs))

    hooks._launch_detached(["x"], tmp_path)

    assert seen["cwd"] == tmp_path
    assert seen["stdin"] == seen["stdout"] == seen["stderr"] == subprocess.DEVNULL
    if sys.platform == "win32":
        # DETACHED_PROCESS would leave the child with no console, so each git it runs opens a window.
        assert seen["creationflags"] == subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        assert seen["start_new_session"] is True


def test_sync_ignores_modules_shadowing_imports_in_the_checkout(tmp_path: Path):
    remote = tmp_path / "remote.git"
    home = _home(tmp_path, remote)
    checkout = _wired_checkout(tmp_path, home)
    (checkout / "typer.py").write_text("raise SystemExit('shadowed')\n", encoding="utf-8")
    (checkout / ".brain" / "CONTEXT.md").write_text("changed\n", encoding="utf-8")

    completed, _ = _hook("stop", checkout, home)

    assert completed.returncode == 0
    assert _eventually(lambda: "alpha: sync from" in _git(remote, "log", "--format=%s", "main"))


def test_stop_returns_at_once_leaving_a_detached_sync_that_pushes(tmp_path: Path):
    remote = tmp_path / "remote.git"
    home = _home(tmp_path, remote)
    (home / "brainspaces" / "alpha" / ".brain" / "CONTEXT.md").write_text("changed\n", encoding="utf-8")

    completed, elapsed = _hook("stop", home, home)

    assert completed.returncode == 0
    assert completed.stdout == b"" and completed.stderr == b""
    assert elapsed < 5  # process startup only; the sync itself runs after the hook returned
    assert _eventually(lambda: "alpha: sync from" in _git(remote, "log", "--format=%s", "main"))


def test_stop_starts_a_push_only_sync_of_the_resolved_home(tmp_path: Path, monkeypatch, launches):
    home = _home(tmp_path, tmp_path / "remote.git")
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    monkeypatch.chdir(home)

    hooks.start_sync(push_only=True)

    assert launches == [[sys.executable, "-I", "-c", CLI, "sync", "--home", str(home.resolve()), "--push-only"]]


def test_session_start_syncs_then_emits_the_same_payload_when_the_remote_is_unreachable(tmp_path: Path):
    remote = tmp_path / "remote.git"
    home = _home(tmp_path, remote)
    _git(home, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    checkout = _wired_checkout(tmp_path, home)
    (checkout / ".brain" / "DOTBRAIN.md").write_bytes(b"CONVENTION\r\nBODY\n")
    expected = hooks.brain_context(cwd=checkout)

    completed, elapsed = _hook("session-start", checkout, home, stdin=b'{"source": "startup"}')

    assert completed.returncode == 0
    assert completed.stdout == expected
    assert elapsed < hooks.SESSION_START_SYNC_SECONDS
    assert _git(home, "log", "-1", "--format=%s").startswith("alpha: sync from")


def test_session_start_retries_lock_until_holder_releases(tmp_path: Path):
    remote = tmp_path / "remote.git"
    home = _home(tmp_path, remote)
    (home / "new.md").write_text("new\n", encoding="utf-8")
    git_dir = Path(_git(home, "rev-parse", "--absolute-git-dir"))
    holder = home_sync._acquire(git_dir / home_sync.LOCK_NAME)
    assert holder is not None
    # Hold longer than child startup, so the child must retry the lock itself.
    release = threading.Timer(3, home_sync._release, args=(holder,))
    release.start()
    try:
        completed, elapsed = _hook("session-start", home, home)
        assert completed.returncode == 0
        assert elapsed < hooks.SESSION_START_SYNC_SECONDS
        assert "home: sync from" in _git(remote, "log", "-1", "--format=%s", "main")
    finally:
        release.join()


@pytest.mark.parametrize("stdin, push_only", [
    ('{"source": "compact"}', True),  # mid-turn: never fetch and integrate under the agent
    ('{"source": "startup"}', False),
    ('{"source": "resume"}', False),
    ("", False),
    ("not json", False),
    ("[1, 2]", False),
])
def test_session_start_on_compact_only_pushes(tmp_path: Path, monkeypatch, launches, stdin, push_only):
    home = _home(tmp_path, tmp_path / "remote.git")
    checkout = _wired_checkout(tmp_path, home)
    (checkout / ".brain" / "DOTBRAIN.md").write_bytes(b"BODY\n")
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    monkeypatch.chdir(checkout)

    result = CliRunner().invoke(app, ["hook", "session-start"], input=stdin)

    assert result.exit_code == 0
    assert result.stdout_bytes == hooks.brain_context(cwd=checkout)
    assert len(launches) == 1 and ("--push-only" in launches[0]) is push_only


def test_session_start_leaves_a_slow_sync_running_at_the_bound(tmp_path: Path, monkeypatch):
    home = _home(tmp_path, tmp_path / "remote.git")
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    monkeypatch.chdir(home)
    monkeypatch.setattr(hooks, "_sync_argv", lambda *_: [sys.executable, "-c", "import time; time.sleep(30)"])
    children: list[subprocess.Popen] = []
    launch = hooks._launch_detached
    monkeypatch.setattr(hooks, "_launch_detached",
                        lambda argv, cwd: children.append(launch(argv, cwd)) or children[-1])

    started = time.monotonic()
    hooks.start_sync(wait=0.5)

    try:
        assert time.monotonic() - started < 5
        assert children[0].poll() is None  # never killed at the bound
    finally:
        children[0].kill()
        children[0].wait()


def test_session_end_runs_the_full_sync(tmp_path: Path):
    remote = tmp_path / "remote.git"
    home = _home(tmp_path, remote)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(remote), str(other))
    (other / "from-other.md").write_text("y\n", encoding="utf-8")
    _git(other, "add", "-A")
    _git(other, "-c", "user.name=O", "-c", "user.email=o@example.com", "commit", "-q", "-m", "other")
    _git(other, "push", "-q")

    completed, _ = _hook("session-end", home, home)

    assert completed.returncode == 0 and completed.stdout == b""
    assert _eventually(lambda: (home / "from-other.md").is_file())


def test_hooks_sync_only_in_wired_checkouts_or_the_home(tmp_path: Path, monkeypatch, launches):
    home = _home(tmp_path, tmp_path / "remote.git")
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    unwired = _repo(tmp_path, "unwired")
    _wire(unwired, convention=b"BODY\n")  # a real .brain directory is not Brainspace wiring
    elsewhere = _wired_checkout(tmp_path, _home(tmp_path, tmp_path / "other.git", "other-home"), "elsewhere")
    brain_only = _wired_checkout(tmp_path, home, "brain-only", links=(".brain",))

    for cwd, launched in ((unwired, 0), (tmp_path, 0), (elsewhere, 0),
                          (_wired_checkout(tmp_path, home), 1), (brain_only, 1), (home, 1)):
        launches.clear()
        monkeypatch.chdir(cwd)
        hooks.start_sync()
        assert len(launches) == launched, cwd


@pytest.mark.parametrize("event", ["session-start", "stop", "session-end"])
def test_disabled_sync_makes_every_entrypoint_do_nothing(tmp_path: Path, monkeypatch, launches, event):
    home = _home(tmp_path, tmp_path / "remote.git")
    (home / "config.yaml").write_text("sync:\n  enabled: false\n", encoding="utf-8")
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    monkeypatch.chdir(home)

    result = CliRunner().invoke(app, ["hook", event])

    assert result.exit_code == 0 and result.output == ""
    assert launches == []


def test_sync_failures_never_break_a_hook(tmp_path: Path, monkeypatch, launches):
    home = _home(tmp_path, tmp_path / "remote.git")
    (home / "config.yaml").write_text("sync: [not, a, mapping]\n", encoding="utf-8")
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    monkeypatch.chdir(home)

    hooks.start_sync()  # an invalid config is swallowed, not raised

    assert launches == []
