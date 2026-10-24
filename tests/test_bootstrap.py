"""Integration tests for bootstrap effects: claude hook install and per-project skill linking."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from dotbrain import assets, bootstrap as bootstrap_mod, config, doctor, paths, resource_loader, runtimes, skills, subagents, workflows
from dotbrain.cli import app

from conftest import set_fake_home

runner = CliRunner()
_installed_on_path = runtimes.installed


def test_cursor_discovery_uses_agent_command(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda command: "/fake/agent" if command == "agent" else None)
    assert runtimes.command(runtimes.find("cursor")) == "agent"
    assert _installed_on_path(runtimes.find("cursor"))


def test_bootstrap_runner_bounds_and_hides_version_probe(monkeypatch):
    import os
    captured = {}

    def run(argv, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", run)
    bootstrap_mod._default_run(["agent", "--version"], timeout=5)
    assert captured["timeout"] == 5
    assert captured["stdin"] == subprocess.DEVNULL
    assert captured["creationflags"] == (subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)



@pytest.mark.parametrize("resolved", ["/fake/bin/pi.cmd", None])
def test_bootstrap_probes_resolved_runtime_path(tmp_path, monkeypatch, resolved):
    import shutil
    root, user = tmp_path / "data", tmp_path / "user"
    monkeypatch.setattr(shutil, "which", lambda command: resolved if command == "pi" else None)
    monkeypatch.setattr(runtimes, "installed", _installed_on_path)
    probes = []

    def run(argv, **kwargs):
        if argv[-1] == "--version":
            probes.append(argv[0])
        return subprocess.CompletedProcess(argv, 0, "", "")

    result = bootstrap_mod.prepare(root, "pi", home=user, run=run)
    assert probes == ([resolved] if resolved else [])
    assert ("Pi: ready" if resolved else "Pi: skipped (command not on PATH)") in str(result)
    assert assets.HOME_DELIVERY["pi"].owned(runtimes.user_dir(runtimes.find("pi"), user)) == bool(resolved)

@pytest.mark.parametrize("answer", ["", "Y", "n", None])
@pytest.mark.parametrize("existing_root", [False, True])
def test_first_machine_bootstrap(tmp_path, monkeypatch, answer, existing_root):
    root, user = tmp_path / "data", tmp_path / "user"
    if existing_root:
        root.mkdir()
        (root / ".git").mkdir()
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name in assets.HOME_DELIVERY)
    monkeypatch.setattr(bootstrap_mod.shutil, "which", lambda command: None)  # probe bare names, not this machine's CLIs
    calls, prompts = [], []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, "", "")

    def confirm(found, prompt):
        prompts.append(prompt)
        assert found == ["Hermes: ready", "OpenCode: ready", "Pi: ready", "Cursor: ready"]
        return answer.lower() in ("", "y")

    result = bootstrap_mod.prepare(root, home=user, run=run, confirm=confirm if answer is not None else None)
    assert result.status == "success", result
    assert len(prompts) == (0 if answer is None else 1)
    for name, module in assets.HOME_DELIVERY.items():
        directory = root if name == "cursor" else runtimes.user_dir(runtimes.find(name), user)
        assert module.owned(directory) == (answer != "n")
        text = str(result)
        assert (f"dotbrain bootstrap --runtime {name}" if answer == "n" else
                f"dotbrain detach --runtime {name}") in text
    assert [argv for argv, _ in calls if argv[-1] == "--version"] == [
        ["hermes", "--version"], ["opencode", "--version"], ["pi", "--version"], ["agent", "--version"]]
    assert all(kwargs["timeout"] == 30 for argv, kwargs in calls if argv[-1] == "--version")


@pytest.mark.parametrize("name", tuple(assets.HOME_DELIVERY))
@pytest.mark.parametrize("failure", ["exit", "timeout"])
def test_bootstrap_skips_broken_runtime(tmp_path, monkeypatch, name, failure):
    root, user = tmp_path / "data", tmp_path / "user"
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name == name)

    def run(argv, **kwargs):
        if argv[-1] == "--version":
            if failure == "timeout":
                raise subprocess.TimeoutExpired(argv, 5)
            return subprocess.CompletedProcess(argv, 1)
        return subprocess.CompletedProcess(argv, 0)

    result = bootstrap_mod.prepare(root, home=user, run=run)
    assert result.status == "success"
    assert "skipped" in str(result)
    assert not (root / ".cache/bootstrap-complete").exists()
    assert not runtimes.user_dir(runtimes.find(name), user).exists()
    assert not assets.HOME_DELIVERY[name].owned(root if name == "cursor" else user)


def test_later_bootstrap_hints_without_prompt_or_setup(tmp_path, monkeypatch):
    root, user = tmp_path / "data", tmp_path / "user"
    run = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name == "pi")
    bootstrap_mod.prepare(root, home=user, run=run)
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name in ("pi", "cursor"))
    result = bootstrap_mod.prepare(root, home=user, run=run,
                                   confirm=lambda *args: pytest.fail("later run prompted"))
    assert "dotbrain bootstrap --runtime cursor" in str(result)
    assert not (user / ".cursor").exists()


@pytest.mark.parametrize("initial", ["detach", "decline", "empty", "upgrade"])
@pytest.mark.parametrize("terminal", [False, True])
def test_bootstrap_completion_survives_no_owned_delivery(tmp_path, monkeypatch, initial, terminal):
    root, user = tmp_path / "data", tmp_path / "user"
    run = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0)
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name in assets.HOME_DELIVERY)
    marker = root / ".cache/bootstrap-complete"
    if initial == "upgrade":
        bootstrap_mod.ensure_data_root(root, run=run)
        assets.link_global(root, "skills", "pi", user_home=user, run=run)
        assert not marker.exists()
        result = bootstrap_mod.prepare(root, home=user, run=run,
            confirm=lambda *args: pytest.fail("upgraded machine prompted"))
        assert "dotbrain bootstrap --runtime cursor" in str(result)
        assert not (user / ".cursor").exists()
    else:
        if initial == "empty":
            monkeypatch.setattr(runtimes, "installed", lambda rt: False)
        result = bootstrap_mod.prepare(root, home=user, run=run,
                                       confirm=(lambda *args: False) if initial == "decline" else None)
    assert result.status == "success", result
    assert marker.is_file()
    assert "/.cache/" in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    if initial in ("detach", "upgrade"):
        assert workflows.detach_runtime(root, "all", home=user, run=run).status == "success"
    assert marker.is_file()
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name in assets.HOME_DELIVERY)
    result = bootstrap_mod.prepare(root, home=user, run=run,
        confirm=(lambda *args: pytest.fail("completed machine prompted")) if terminal else None)
    assert result.status == "success", result
    for name, module in assets.HOME_DELIVERY.items():
        directory = root if name == "cursor" else runtimes.user_dir(runtimes.find(name), user)
        assert not module.owned(directory)
        assert f"dotbrain bootstrap --runtime {name}" in str(result)
    # Explicit setup remains available after completion, including after declining.
    result = bootstrap_mod.prepare(root, "pi", home=user, run=run,
                                  confirm=lambda *args: pytest.fail("explicit setup prompted"))
    assert result.status == "success", result
    assert assets.HOME_DELIVERY["pi"].owned(runtimes.user_dir(runtimes.find("pi"), user))


def test_cloned_home_without_cache_is_first_machine_run(dotbrain_home, tmp_path, monkeypatch):
    import shutil

    run = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0)
    bootstrap_mod.prepare(dotbrain_home, home=tmp_path / "first-user", run=run)
    assert (dotbrain_home / ".cache/bootstrap-complete").is_file()
    assert subprocess.run(["git", "check-ignore", ".cache/bootstrap-complete"], cwd=dotbrain_home,
                          capture_output=True, check=True).returncode == 0
    clone = tmp_path / "cloned-data"
    shutil.copytree(dotbrain_home, clone, ignore=shutil.ignore_patterns(".cache"), symlinks=True)
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name == "pi")
    prompts = []
    result = bootstrap_mod.prepare(clone, home=tmp_path / "second-user", run=run,
                                  confirm=lambda *args: prompts.append(args) or True)
    assert result.status == "success", result
    assert len(prompts) == 1
    assert "dotbrain detach --runtime pi" in str(result)


@pytest.mark.parametrize("runtime", ["hermes", "opencode", "pi", "cursor"])
def test_explicit_bootstrap_never_prompts(tmp_path, monkeypatch, runtime):
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name in assets.HOME_DELIVERY)
    result = bootstrap_mod.prepare(tmp_path / "data", runtime, home=tmp_path / "user",
        run=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0),
        confirm=lambda *args: pytest.fail("explicit runtime prompted"))
    assert result.status == "success", result
    assert f"dotbrain detach --runtime {runtime}" in str(result)
    for other in assets.HOME_DELIVERY:
        if other != runtime:
            assert f"dotbrain detach --runtime {other}" not in str(result)


@pytest.mark.parametrize("stdin,stdout,json_output,prompt", [
    (True, True, False, True), (False, True, False, False),
    (True, False, False, False), (True, True, True, False),
])
def test_bootstrap_terminal_and_json_prompt_routing(tmp_path, monkeypatch, stdin, stdout, json_output, prompt):
    import sys
    from dotbrain.results import CommandResult

    def prepare(*args, confirm=None, **kwargs):
        assert (confirm is not None) == prompt
        if confirm:
            assert confirm(["Pi: ready"], "Set up dotbrain for Pi? [Y/n]")
        return CommandResult("bootstrap")

    monkeypatch.setattr(bootstrap_mod, "prepare", prepare)
    monkeypatch.setattr("builtins.input", lambda: "Y")
    # Invoke directly so CliRunner's stream replacement does not mask terminal detection.
    monkeypatch.setattr(sys.stdin, "isatty", lambda: stdin)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: stdout)
    from dotbrain.cli import bootstrap
    bootstrap(home=tmp_path, runtime="all", json_output=json_output)


def _make_runner(calls=None):
    """Real git, stubbed everything else — mirrors test_wiring.make_runner."""
    if calls is None:
        calls = []

    def run(argv, *, cwd=None, env=None, check=True):
        calls.append(list(argv))
        if argv[0] == "git":
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    return run


def _wire(dotbrain_home, repo, fake_home):
    workflows.wire_project(
        dotbrain_home=dotbrain_home, repo=repo, run_beads=False,
        home=fake_home, run=_make_runner(),
    )


def _fresh_repo(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    return repo


# --------------------------------------------------------------------------- data root seeding


def test_ensure_data_root_seeds_skills_config(tmp_path: Path):
    root = tmp_path / "dr"
    result = bootstrap_mod.ensure_data_root(root)
    skills_config = root / "skills" / "skills.yaml"
    gitignore = root / ".gitignore"
    assert result.skills_seeded
    assert skills_config.is_file()
    assert gitignore.is_file()
    generated = [
        gitignore,
        root / "config.yaml",
        skills_config,
        root / "agents" / "agents.yaml",
    ]
    assert all(b"\r\n" not in path.read_bytes() for path in generated)
    before = skills_config.read_text()
    assert skills.load_global_config(skills_config).global_extra == ()
    bootstrap_mod.ensure_data_root(root)
    assert skills_config.read_text() == before


def test_ensure_data_root_preserves_operator_gitignore(tmp_path: Path):
    root = tmp_path / "dr"
    root.mkdir(parents=True)
    gitignore = root / ".gitignore"
    gitignore.write_text("custom-old-entry\n")

    result = bootstrap_mod.ensure_data_root(root)
    assert gitignore.read_text() == "custom-old-entry\n"
    assert f"seeded .gitignore into {root}" not in result.logs


def test_ensure_data_root_does_not_clobber_existing_skills_config(tmp_path: Path):
    root = tmp_path / "dr"
    (root / "skills").mkdir(parents=True)
    custom = "version: 1\ntargets:\n  codex: ~/.codex/skills\nglobal_extra:\n  - misc/keep\n"
    (root / "skills" / "skills.yaml").write_text(custom)

    result = bootstrap_mod.ensure_data_root(root)
    assert not result.skills_seeded
    assert (root / "skills" / "skills.yaml").read_text() == custom


def test_link_global_skills_links_configured_target(dotbrain_home: Path, tmp_path: Path, fake_home: Path):
    dest = tmp_path / "profile/skills"
    dest.parent.mkdir()
    (dotbrain_home / "skills" / "skills.yaml").write_text(
        "targets:\n"
        f"  codex: {dest}\n"
        "global_extra:\n"
        "  - misc/discovery-test\n"
    )

    result = bootstrap_mod.link_global_skills(dotbrain_home, "codex", home=fake_home)

    assert result.warnings == []
    assert (dest / "discovery-test").is_symlink()
    assert any(line.startswith("delivered global") for line in result.logs)


def test_link_global_skills_reports_actual_link_count(dotbrain_home: Path, tmp_path: Path, fake_home: Path):
    dest = tmp_path / "codex-skills"
    (dotbrain_home / "skills" / "skills.yaml").write_text(
        "targets:\n"
        f"  codex: {dest}\n"
        "global_extra:\n"
        "  - misc/not-installed\n"
    )

    result = bootstrap_mod.link_global_skills(dotbrain_home, "codex", home=fake_home)

    assert any("skill not found" in warning for warning in result.warnings)
    assert result.logs == []


def test_link_global_skills_expands_windows_tilde_target(
    dotbrain_home: Path, fake_home: Path
):
    (dotbrain_home / "skills" / "skills.yaml").write_text(
        "targets:\n"
        r"  codex: ~\.codex\skills" "\n"
    )

    result = bootstrap_mod.link_global_skills(dotbrain_home, "codex", home=fake_home)

    assert result.warnings == []
    assert (fake_home / ".codex/skills").is_dir()


def test_global_delivery_reads_the_runtime_description(dotbrain_home: Path, tmp_path: Path, monkeypatch):
    set_fake_home(monkeypatch, tmp_path)
    # 'skillsonly' has skills and hooks but no native subagents; 'later' is a runtime this version
    # does not recognize, as a newer dotbrain sharing the home might declare.
    monkeypatch.setitem(runtimes.RUNTIMES, "skillsonly",
                        runtimes.Runtime("skillsonly", "skillsonly", "Skills Only", ".skillsonly", hooks=True))
    dest, later = tmp_path / "skillsonly-skills", tmp_path / "later-skills"
    (dotbrain_home / "skills" / "skills.yaml").write_text(
        f"targets:\n  skillsonly: {dest}\n  later: {later}\nglobal_extra:\n  - misc/discovery-test\n")
    for runtime in ("all", "skillsonly"):
        linked = bootstrap_mod.link_global_skills(dotbrain_home, runtime, home=tmp_path)
        assert linked.warnings == []
        assert linked.notices == (["unsupported global skills runtime skipped: later"] if runtime == "all" else [])
        assert bootstrap_mod.link_global_subagents(dotbrain_home, runtime, home=tmp_path).warnings == []
    assert (dest / "discovery-test").is_symlink()
    assert not later.exists()
    with pytest.raises(ValueError, match="no native subagent delivery"):
        assets.link_global(dotbrain_home, "agents", "skillsonly", user_home=tmp_path)
    findings = doctor._check_machine(dotbrain_home, tmp_path)
    assert [f.message for f in findings if f.status == "error"] == []
    assert any(f.status == "warn" and f.message.endswith(": later") for f in findings)
    result = runner.invoke(app, ["bootstrap", "--home", str(dotbrain_home), "--runtime", "later", "--json"])
    assert result.exit_code == 2
    assert "--runtime must be claude, codex, hermes, opencode, pi, cursor, skillsonly, or all" in result.stdout


def test_ensure_data_root_seeds_global_subagents(tmp_path: Path):
    root = tmp_path / "fresh-dotbrain"
    result = bootstrap_mod.ensure_data_root(root)

    assert result.agents_seeded is True
    assert (root / "agents" / "claude").is_dir()
    assert (root / "agents" / "codex").is_dir()
    assert subagents.load_global_subagents(root) == ()
    # Claude Code receives packaged subagents from the plugin; Codex gets prefixed generated copies.
    for name in ("reviewer", "worker", "verifier", "researcher"):
        assert (root / ".cache" / "agents" / "codex" / f"dotbrain-{name}.toml").is_file()
    assert not (root / ".cache" / "agents" / "claude").exists()
    assert any("synced .cache/agents/codex/dotbrain-reviewer.toml" in line for line in result.logs)


def test_wire_project_does_not_seed_project_default_subagents(
    dotbrain_home: Path, tmp_path: Path, fake_home: Path
):
    bootstrap_mod.ensure_data_root(dotbrain_home)
    repo = _fresh_repo(tmp_path, "project-default-subagent")

    _wire(dotbrain_home, repo, fake_home)

    assert config.load_project_subagents(dotbrain_home, "project-default-subagent") == ()
    project_yaml = paths.brainspace(dotbrain_home, "project-default-subagent") / ".brain" / "project.yaml"
    declaration = yaml.safe_load(project_yaml.read_text())
    assert "agents" not in declaration
    assert "subagents" not in declaration


def test_agents_link_project_target_reports_actual_linked_files(
    dotbrain_home: Path, tmp_path: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    bootstrap_mod.ensure_data_root(dotbrain_home)
    repo = _fresh_repo(tmp_path, "claude-only-agent-link")
    _wire(dotbrain_home, repo, fake_home)
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    project_yaml = paths.brainspace(dotbrain_home, "claude-only-agent-link") / ".brain" / "project.yaml"
    declaration = yaml.safe_load(project_yaml.read_text())
    declaration["agents"] = ["claude"]
    project_yaml.write_text(yaml.safe_dump(declaration, sort_keys=False))

    result = runner.invoke(
        app,
        ["agents", "link", "--scope", "project", "--runtime", "codex", "--project", "claude-only-agent-link"],
    )

    assert result.exit_code == 2, result.output
    assert "not declared" in result.output


def test_link_global_subagents_links_configured_target(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    dest = tmp_path / ".codex" / "agents"
    set_fake_home(monkeypatch, tmp_path)
    bootstrap_mod.ensure_data_root(dotbrain_home)
    (dotbrain_home / "agents" / "agents.yaml").write_text(
        "targets:\n"
        "  codex: ~/.codex/agents\n"
        "global:\n"
        "  - reviewer\n"
    )
    result = bootstrap_mod.link_global_subagents(dotbrain_home, "codex", home=tmp_path)

    assert result.warnings == []
    assert subagents.is_managed_copy(dest / "dotbrain-reviewer.toml")
    assert any(line.startswith("delivered global") for line in result.logs)


def test_link_global_subagents_warns_once_for_missing_name(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    set_fake_home(monkeypatch, tmp_path)
    (dotbrain_home / "agents").mkdir(parents=True, exist_ok=True)
    (dotbrain_home / "agents" / "agents.yaml").write_text("global:\n  - missing-agent\n")

    result = bootstrap_mod.link_global_subagents(dotbrain_home, "all")

    assert result.warnings == ["subagent not found: missing-agent"]


def test_link_global_skills_warns_when_config_missing(dotbrain_home: Path, fake_home: Path):
    result = bootstrap_mod.link_global_skills(dotbrain_home, home=fake_home)

    assert not result.warnings


# --------------------------------------------------------------------------- per-project skills


@pytest.mark.usefixtures("claude_codex_on_path")
def test_skills_link_project_creates_selected_symlinks_after_wire(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Project linking materializes only the declared selection."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = _fresh_repo(tmp_path, "skilltest")
    _wire(dotbrain_home, repo, fake_home)

    project_yaml = paths.brainspace(dotbrain_home, "skilltest") / ".brain" / "project.yaml"
    project_yaml.write_text(project_yaml.read_text() + "\nskills:\n  - misc/discovery-test\n")
    result = runner.invoke(app, ["skills", "link", "--scope", "project", "--repo", str(repo)])
    assert result.exit_code == 0, result.output

    assert (repo / ".claude" / "skills" / "discovery-test").is_symlink()
    assert (repo / ".agents" / "skills" / "discovery-test").is_symlink()


@pytest.mark.usefixtures("claude_codex_on_path")
def test_skills_link_project_prunes_stale_selection(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Re-running skills link removes stale dotbrain-owned symlinks."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = _fresh_repo(tmp_path, "prunetest")
    _wire(dotbrain_home, repo, fake_home)

    runner.invoke(app, ["skills", "link", "--scope", "project", "--repo", str(repo)])

    # Plant a stale symlink pointing into skills/.
    skills_dir = repo / ".claude" / "skills"
    stale = skills_dir / "old-skill"
    stale.symlink_to((dotbrain_home / "skills" / "misc" / "discovery-test").resolve())

    runner.invoke(app, ["skills", "link", "--scope", "project", "--repo", str(repo)])

    assert not stale.exists(), "stale symlink should have been pruned"


def test_ensure_data_root_initializes_a_git_checkout(tmp_path: Path):
    """A seeded data root must be a git checkout.

    wire, refresh, and unwire all reject a data root without .git, so seeding the files
    without initializing the repo left every fresh install failing on the first wire.
    """
    root = tmp_path / "dr"

    result = bootstrap_mod.ensure_data_root(root)

    assert result.git_initialized
    assert (root / ".git").exists()


def test_ensure_data_root_leaves_an_existing_checkout_alone(tmp_path: Path):
    root = tmp_path / "dr"
    bootstrap_mod.ensure_data_root(root)
    marker = root / ".git" / "dotbrain-marker"
    marker.write_text("kept", encoding="utf-8")

    result = bootstrap_mod.ensure_data_root(root)

    assert not result.git_initialized
    assert marker.read_text(encoding="utf-8") == "kept"


def test_ensure_data_root_reports_a_missing_git_binary(tmp_path: Path):
    def _no_git(argv, *, cwd=None, check=True):
        raise FileNotFoundError(argv[0])

    with pytest.raises(RuntimeError, match="git is required"):
        bootstrap_mod.ensure_data_root(tmp_path / "dr", run=_no_git)


def test_installed_runtimes_are_not_seeded_and_are_named(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(runtimes, "installed", lambda rt: rt.name == "opencode")
    home, user = tmp_path / "dr", tmp_path / "user"
    bootstrap_mod.ensure_data_root(home, user_home=user)
    targets = skills.load_global_config(home / "skills/skills.yaml").targets
    assert "opencode" not in targets
    assert "hermes" not in targets
    linked = bootstrap_mod.link_global_skills(home, "all", home=user)
    assert linked.warnings == []
    assert linked.notices == ["OpenCode is installed; run `dotbrain bootstrap --runtime opencode` to deliver dotbrain to it"]
    assert not (user / ".config/opencode").exists()
    assert "targets:" not in (home / "skills/skills.yaml").read_text()

    # An existing config gains no target: bootstrap names the command instead of delivering unasked.
    (home / "skills/skills.yaml").write_text("targets: {}\nglobal_extra: []\n")
    other = tmp_path / "other"
    linked = bootstrap_mod.link_global_skills(home, "all", home=other)
    assert linked.notices == ["OpenCode is installed; run `dotbrain bootstrap --runtime opencode` to deliver dotbrain to it"]
    assert not (other / ".config/opencode").exists()
