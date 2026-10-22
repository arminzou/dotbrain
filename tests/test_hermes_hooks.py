"""Hermes session hooks: the packaged plugin maps Hermes events onto `dotbrain hook run`."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

from dotbrain import hooks, resource_loader

PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "plugin"
CONVENTION = "## dotbrain convention\n\nBODY"
# Hermes spills a hook result over this many characters to a file; the model sees a preview only.
HERMES_CONTEXT_LIMIT = 10_000


class FakeContext:
    def __init__(self):
        self.hooks = {}

    def register_skill(self, *args, **kwargs):
        pass

    def register_hook(self, name, callback):
        self.hooks[name] = callback


class FakeCli:
    """Records `dotbrain` calls; `output` is what `hook run` prints, `error` what it raises."""

    def __init__(self):
        self.calls, self.launched = [], []
        self.output, self.error = CONVENTION + "\n\n", None

    def run(self, argv, **kwargs):
        self.calls.append((argv[4], argv[6], kwargs["timeout"]))
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(argv, 0, self.output, "")

    def popen(self, argv, **kwargs):
        self.launched.append(argv[4])


@pytest.fixture
def hermes(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("dotbrain_hermes_hooks_plugin", PLUGIN_ROOT / "__init__.py")
    plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin)  # a fresh module: fresh per-session state
    cli = FakeCli()
    monkeypatch.setattr(plugin.subprocess, "run", cli.run)
    monkeypatch.setattr(plugin.subprocess, "Popen", cli.popen)
    monkeypatch.setattr(plugin.shutil, "which", lambda name: "dotbrain" if name == "dotbrain" else None)
    monkeypatch.chdir(tmp_path)
    ctx = FakeContext()
    plugin.register(ctx)
    return plugin, ctx.hooks, cli


def _turn(hooks, session="s1", history=(), first=True, **kwargs):
    return hooks["pre_llm_call"](session_id=session, conversation_history=list(history),
                                 is_first_turn=first, model="m", platform="cli", **kwargs)


def _injected(context):
    return [{"role": "user", "content": "hi", "api_content": f"<context>{context}</context>\n\nhi"}]


def test_startup_runs_once_and_never_injects_twice(hermes, tmp_path):
    _, hooks, cli = hermes
    assert _turn(hooks) == {"context": CONVENTION}
    assert cli.calls == [("startup", str(tmp_path), hermes[0].START_TIMEOUT)]
    # The history now carries the convention: later turns add nothing and sync nothing.
    for _ in range(3):
        assert _turn(hooks, history=_injected(CONVENTION), first=False) is None
    assert len(cli.calls) == 1


def test_resumed_session_runs_resume_and_skips_context_it_already_has(hermes):
    _, hooks, cli = hermes
    assert _turn(hooks, session="old", first=False) == {"context": CONVENTION}
    assert _turn(hooks, session="replayed", history=_injected(CONVENTION), first=False) is None
    assert [c[0] for c in cli.calls] == ["resume", "resume"]


def test_compaction_refreshes_and_reinjects(hermes):
    _, hooks, cli = hermes
    _turn(hooks)
    cli.output = CONVENTION + " v2\n"
    assert _turn(hooks, history=[{"role": "user", "content": "summary"}], first=False) == {"context": CONVENTION + " v2"}
    assert [c[0] for c in cli.calls] == ["startup", "compaction"]
    assert _turn(hooks, history=_injected(CONVENTION + " v2"), first=False) is None
    assert len(cli.calls) == 2


def test_unwired_checkout_stays_silent(hermes):
    _, hooks, cli = hermes
    cli.output = ""
    assert _turn(hooks) is None
    assert _turn(hooks, first=False) is None
    assert [c[0] for c in cli.calls] == ["startup"]
    # Sync is the CLI's decision: turn ends and exit still reach it.
    hooks["on_session_end"](session_id="s1")
    hooks["on_session_finalize"](session_id="s1")
    assert cli.launched == ["turn-end"] and [c[0] for c in cli.calls] == ["startup", "session-end"]


def test_sync_disabled_passes_the_convention_through(hermes):
    # With sync off the CLI still prints the convention and syncs nothing; the plugin adds no rule.
    _, hooks, cli = hermes
    assert _turn(hooks) == {"context": CONVENTION}
    hooks["on_session_end"](session_id="s1")
    assert cli.launched == ["turn-end"]


def test_turn_end_launches_in_the_background_and_finalize_runs_once(hermes):
    plugin, hooks, cli = hermes
    _turn(hooks)
    hooks["on_session_end"](session_id="s1")
    hooks["on_session_end"](session_id="s1")
    assert cli.launched == ["turn-end", "turn-end"]
    assert [c[0] for c in cli.calls] == ["startup"]  # no waiting call, no full sync
    hooks["on_session_finalize"](session_id="s1")
    hooks["on_session_finalize"](session_id="s1")
    assert cli.calls[1:] == [("session-end", cli.calls[0][1], plugin.END_TIMEOUT)]


def test_unseen_sessions_are_skipped(hermes):
    _, hooks, cli = hermes
    hooks["on_session_end"](session_id="never")
    hooks["on_session_finalize"](session_id="never")
    assert cli.calls == [] and cli.launched == []


def test_children_get_no_convention_and_no_sync(hermes):
    _, hooks, cli = hermes
    _turn(hooks, session="parent")
    hooks["subagent_start"](child_session_id="child", parent_session_id="parent")
    assert _turn(hooks, session="child") is None
    assert _turn(hooks, session="other-child", parent_session_id="parent") is None
    for child in ("child", "other-child"):
        hooks["on_session_end"](session_id=child)
        hooks["on_session_finalize"](session_id=child)
    assert [c[0] for c in cli.calls] == ["startup"] and cli.launched == []


def test_reset_clears_the_session(hermes):
    _, hooks, cli = hermes
    _turn(hooks)
    hooks["on_session_reset"](session_id="s1")
    hooks["on_session_finalize"](session_id="s1")
    assert _turn(hooks) == {"context": CONVENTION}
    assert [c[0] for c in cli.calls] == ["startup", "startup"]


def test_missing_cli_is_a_silent_no_op(hermes, monkeypatch):
    plugin, hooks, cli = hermes
    monkeypatch.setattr(plugin.shutil, "which", lambda name: None)
    assert _turn(hooks) is None
    hooks["on_session_end"](session_id="s1")
    hooks["on_session_finalize"](session_id="s1")
    assert cli.calls == [] and cli.launched == []


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("dotbrain", 25), OSError("gone"), RuntimeError("bug")])
def test_cli_failures_fail_open(hermes, monkeypatch, error):
    plugin, hooks, cli = hermes
    cli.error = error
    assert _turn(hooks) is None
    assert _turn(hooks, first=False) is None
    assert len(cli.calls) == 1  # a failed start is not retried every turn

    def broken(*args, **kwargs):
        raise error

    monkeypatch.setattr(plugin.subprocess, "Popen", broken)
    hooks["on_session_end"](session_id="s1")
    hooks["on_session_finalize"](session_id="s1")


def test_failing_cli_exit_status_injects_nothing(hermes, monkeypatch):
    plugin, hooks, cli = hermes
    monkeypatch.setattr(plugin.subprocess, "run",
                        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 1, CONVENTION, "boom"))
    assert _turn(hooks) is None


def test_checkout_comes_from_hermes_when_available(hermes, monkeypatch, tmp_path):
    import sys
    import types

    plugin, hooks, cli = hermes
    module = types.ModuleType("agent.runtime_cwd")
    module.resolve_agent_cwd = lambda: tmp_path / "project"
    monkeypatch.setitem(sys.modules, "agent", types.ModuleType("agent"))
    monkeypatch.setitem(sys.modules, "agent.runtime_cwd", module)
    _turn(hooks)
    assert cli.calls[0][1] == str(tmp_path / "project")


def test_packaged_convention_fits_hermes_context_limit():
    with resource_loader.resource_file("templates/brain/DOTBRAIN.md") as path:
        body = path.read_text(encoding="utf-8")
    # What the plugin injects: the CLI payload, stripped.
    assert len(f"{hooks.CONVENTION_HEADING}\n\n{body}".strip()) < HERMES_CONTEXT_LIMIT
