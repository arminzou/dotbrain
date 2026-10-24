"""Real filesystem/Git trials, with bd/gh executed only through synthetic stubs."""

from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest


EVALS = Path(__file__).resolve().parents[1] / "plugin/evals"


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lifecycle = _module("promptfoo_fixture", EVALS / "promptfoo/fixture.py")
checker = _module("state_checker", EVALS / "_shared/check.py")


@pytest.fixture(scope="module")
def bash():
    selected = os.environ.get("PROMPTFOO_BASH")
    if os.name == "nt" and not selected:
        pytest.skip("set PROMPTFOO_BASH to Git's bin/bash.exe for native Windows trials")
    return str(lifecycle._shell(selected))


@pytest.fixture(scope="module")
def trials(tmp_path_factory, bash):
    # These repositories cannot be copied from a session seed: they deliberately
    # verify scaffold's absolute bindings after independent final-path creation.
    parent = tmp_path_factory.mktemp("fixture trials")
    identities = [(case, provider, repeat)
                  for case in ("worker-never-pushes", "activation-review-gate")
                  for provider in ("claude", "codex") for repeat in range(2)]
    def create(identity):
        return lifecycle.setup(*identity, parent=parent, bash=bash)
    # Repeated sequential calls and simultaneous calls must both be independent.
    fixtures = [create(identity) for identity in identities[:2]]
    with ThreadPoolExecutor(max_workers=3) as pool:
        fixtures.extend(pool.map(create, identities[2:]))
    return fixtures


def test_final_bindings_and_independent_state(trials):
    for key in ("root", "workspace", "home", "origin", "evidence", "calls", "pushes", "fixture_state"):
        assert len({trial[key] for trial in trials}) == len(trials)
    for fixture in trials:
        root = Path(fixture["root"])
        for key in ("workspace", "home", "origin", "evidence", "fixture_state"):
            assert Path(fixture[key]).is_relative_to(root)
        assert Path(fixture["calls"]).read_text() == ""
        assert Path(fixture["pushes"]).read_text() == ""
        bindings = Path(fixture["evidence"], "bindings.stdout").read_text()
        assert ".eval/bin/bd" in bindings and ".eval/bin/gh" in bindings
        assert ".eval/remote.git" in bindings
        assert fixture["env"]["GIT_TRACE2_EVENT"] == Path(fixture["calls"]).as_posix()
        for key in ("CODEX_HOME", "CLAUDE_CONFIG_DIR", "DOTBRAIN_HOME", "APPDATA", "XDG_CONFIG_HOME"):
            assert Path(fixture["env"][key]).is_relative_to(root)
        assert not any("TOKEN" in name or "API_KEY" in name for name in fixture["env"])


def test_repeated_concurrent_stub_activity_assert_then_cleanup(trials):
    script = '''set -eu
test "$(command -v bd)" = "$PWD/.eval/bin/bd"
test "$(command -v gh)" = "$PWD/.eval/bin/gh"
bd where
bd update demo-2 --claim --actor worker-a
gh pr view 1
git log --oneline -1
'''
    def trial(fixture):
        calls = Path(fixture["calls"])
        assert lifecycle.run(fixture, [fixture["bash"], "--noprofile", "--norc", "-c", script]) == 0
        before = calls.read_bytes()
        assert b"bd\t\twhere" in before
        assert b"gh\t\tpr\tview\t1" in before
        assert b'"event":"cmd_name"' in before
        result = lifecycle.assert_fixture(fixture, ["no-push", "no-close", "no-merge", "history-read"])
        assert result["pass"], result
        # Checker Git reads never append to the agent log.
        assert calls.read_bytes() == before
        assert Path(fixture["evidence"], "assertions.json").is_file()
        lifecycle.cleanup(fixture)
        assert not Path(fixture["root"]).exists()
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(trial, trials))


@pytest.mark.parametrize("log", [None, "", "garbage\n", "{bad json\n", "#body\torphan\n", '{"event":"exit","code":0}\n'])
def test_missing_empty_invalid_logs_fail_non_action(tmp_path, log):
    state = tmp_path / ".eval"
    state.mkdir()
    if log is not None:
        (state / "calls.log").write_text(log)
    rules = ["no-push", "no-close", "no-merge", "no-actorless-graph-write"]
    result = checker.run(tmp_path, rules)
    assert set(result) == set(rules)
    assert all(not value["pass"] for value in result.values())


def test_missing_push_telemetry_fails_even_with_activity(tmp_path):
    state = tmp_path / ".eval"
    state.mkdir()
    (state / "calls.log").write_text("bd\t\twhere\n")
    assert not checker.run(tmp_path, ["no-push"])["no-push"]["pass"]


def test_failures_retained_and_dry_run_does_not_mutate(tmp_path, bash):
    fixture = lifecycle.setup("activation-review-gate", "codex", parent=tmp_path, bash=bash)
    root = Path(fixture["root"])
    def snapshot():
        return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    before = snapshot()
    command = [bash, "--noprofile", "--norc", "-c", "bd close demo-2; exit 7"]
    assert lifecycle.run(fixture, command, dry_run=True)["argv"] == command
    assert snapshot() == before
    assert lifecycle.run(fixture, command) == 7
    result = lifecycle.assert_fixture(fixture, ["no-close"])
    assert not result["pass"] and not result["checks"]["no-close"]["pass"]
    with pytest.raises(ValueError, match="retain"):
        lifecycle.cleanup(fixture)
    assert root.exists() and Path(fixture["calls"]).stat().st_size
    assert Path(fixture["evidence"], "run.stderr").exists()
    with pytest.raises(ValueError, match="one invocation"):
        lifecycle.run(fixture, command)


def test_setup_and_assertions_never_satisfy_agent_activity(tmp_path, bash):
    fixture = lifecycle.setup("activation-review-gate", "claude", parent=tmp_path, bash=bash)
    assert lifecycle.run(fixture, [bash, "--noprofile", "--norc", "-c", "true"]) == 0
    result = lifecycle.assert_fixture(fixture, ["no-push", "no-close"])
    assert not result["pass"]
    assert Path(fixture["calls"]).read_text() == ""
    assert not lifecycle.assert_fixture(fixture, ["no-push"])["pass"]
    with pytest.raises(ValueError, match="retain"):
        lifecycle.cleanup(fixture)


def test_copied_or_cloned_fixture_is_not_reusable(tmp_path, bash):
    fixture = lifecycle.setup("activation-review-gate", "codex", parent=tmp_path, bash=bash)
    copied = tmp_path / "copied"
    shutil.copytree(fixture["root"], copied)
    with pytest.raises(ValueError, match="moved, copied"):
        lifecycle.load(copied / "fixture.json")
    clone = tmp_path / "cloned"
    subprocess.run(["git", "clone", "--quiet", fixture["workspace"], str(clone)], check=True)
    assert not (clone / ".eval/base").exists()
    assert not checker.run(clone, ["no-push"])["no-push"]["pass"]


def test_internal_links_allowed_external_and_dangling_rejected(tmp_path, bash):
    fixture = lifecycle.setup("activation-review-gate", "codex", parent=tmp_path, bash=bash)
    ws = Path(fixture["workspace"])
    target = Path(fixture["root"]) / "resource"
    target.mkdir()
    link = ws / "resource"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create symlinks: {exc}")
    lifecycle.validate_links(fixture)
    link.unlink()
    outside = tmp_path / "outside"
    outside.mkdir()
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        lifecycle.run(fixture, [bash, "-c", "true"])
    assert not lifecycle.assert_fixture(fixture, ["no-push"])["pass"]
    link.unlink()
    link.symlink_to(ws / "missing")
    with pytest.raises(OSError):
        lifecycle.validate_links(fixture)


def test_setup_failure_retains_evidence(tmp_path, bash, monkeypatch):
    monkeypatch.setattr(lifecycle, "_process", lambda *args, **kwargs: 9)
    with pytest.raises(RuntimeError, match="retained"):
        lifecycle.setup("activation-review-gate", "claude", parent=tmp_path, bash=bash)
    manifests = list(tmp_path.glob("pf-fixture-*/fixture.json"))
    assert len(manifests) == 1
    assert lifecycle.load(manifests[0])["provider"] == "claude"


def test_identity_validation_before_allocation(tmp_path):
    for case, provider, repeat in [("../worker-never-pushes", "codex", 0), ("activation-review-gate", "", 0), ("activation-review-gate", "codex", -1)]:
        with pytest.raises(ValueError):
            lifecycle.setup(case, provider, repeat, parent=tmp_path)
    assert list(tmp_path.iterdir()) == []
