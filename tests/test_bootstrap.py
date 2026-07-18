"""Integration tests for bootstrap effects: claude hook install and per-project skill linking."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import bootstrap as bootstrap_mod, config, paths, resource_loader, skills, subagents, workflows
from dotbrain.cli import app

from conftest import set_fake_home

runner = CliRunner()


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
        install_global_hook=False, home=fake_home, run=_make_runner(),
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
    # Seeded via the same renderer reconcile uses, so the first link is a no-op rewrite.
    before = skills_config.read_text()
    skills.reconcile_global_config(skills_config)
    assert skills_config.read_text() == before


def test_ensure_data_root_reconciles_root_gitignore_from_template(tmp_path: Path):
    root = tmp_path / "dr"
    root.mkdir(parents=True)
    gitignore = root / ".gitignore"
    gitignore.write_text("custom-old-entry\n")

    result = bootstrap_mod.ensure_data_root(root)
    desired = resource_loader.resource("templates/gitignore").read_text()

    assert gitignore.read_text() == desired
    assert f"seeded .gitignore into {root}" in result.logs


def test_ensure_data_root_does_not_clobber_existing_skills_config(tmp_path: Path):
    root = tmp_path / "dr"
    (root / "skills").mkdir(parents=True)
    custom = "version: 1\ntargets:\n  codex: ~/.codex/skills\nglobal_extra:\n  - misc/keep\n"
    (root / "skills" / "skills.yaml").write_text(custom)

    result = bootstrap_mod.ensure_data_root(root)
    assert not result.skills_seeded
    assert (root / "skills" / "skills.yaml").read_text() == custom


# --------------------------------------------------------------------------- claude hook install


def test_install_global_claude_hook_writes_settings_json(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    """install_global_claude_hook writes the SessionStart hook to settings.json via Python."""
    import json
    settings = tmp_path / ".claude" / "settings.json"
    bootstrap_mod.install_global_claude_hook(dotbrain_home, settings=settings, home=fake_home)
    data = json.loads(settings.read_text())
    commands = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert any("dotbrain hook claude-worktree-bootstrap" in c for c in commands)


def test_link_global_skills_links_configured_target(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "codex-skills"
    (dotbrain_home / "skills" / "skills.yaml").write_text(
        "targets:\n"
        f"  codex: {dest}\n"
        "global_baseline:\n"
        "  - brain/wire-brain\n"
    )

    result = bootstrap_mod.link_global_skills(dotbrain_home, "codex")

    assert result.warnings == []
    assert (dest / "wire-brain").is_symlink()
    assert any(line.startswith("global: linked") for line in result.logs)


def test_link_global_skills_reports_actual_link_count(dotbrain_home: Path, tmp_path: Path):
    dest = tmp_path / "codex-skills"
    (dotbrain_home / "skills" / "skills.yaml").write_text(
        "targets:\n"
        f"  codex: {dest}\n"
        "global_extra:\n"
        "  - misc/not-installed\n"
    )

    result = bootstrap_mod.link_global_skills(dotbrain_home, "codex")

    assert any("skill not found" in warning for warning in result.warnings)
    assert result.logs == [f"global: linked {len(skills.GLOBAL_BASELINE)} skill(s) into {dest}"]


def test_link_global_skills_expands_windows_tilde_target(
    dotbrain_home: Path, fake_home: Path
):
    (dotbrain_home / "skills" / "skills.yaml").write_text(
        "targets:\n"
        r"  codex: ~\.codex\skills" "\n"
    )

    result = bootstrap_mod.link_global_skills(dotbrain_home, "codex", home=fake_home)

    assert result.warnings == []
    assert (fake_home / r".codex\skills" / "wire-brain").is_symlink()


def test_ensure_data_root_seeds_global_subagents(tmp_path: Path):
    root = tmp_path / "fresh-dotbrain"
    result = bootstrap_mod.ensure_data_root(root)

    assert result.agents_seeded is True
    assert (root / "agents" / "claude").is_dir()
    assert (root / "agents" / "codex").is_dir()
    assert subagents.load_global_subagents(root) == ()
    for runtime, ext in (("claude", "md"), ("codex", "toml")):
        for name in ("reviewer", "implementer", "investigator", "verifier"):
            assert (root / ".cache" / "agents" / runtime / f"{name}.{ext}").is_file()
    assert any("rehydrated .cache/agents/claude/reviewer.md" in line for line in result.logs)
    assert (root / ".cache" / "agents" / "claude" / "reviewer.md").read_text().startswith("---\n")


def test_wire_project_does_not_seed_project_default_subagents(
    dotbrain_home: Path, tmp_path: Path, fake_home: Path
):
    bootstrap_mod.ensure_data_root(dotbrain_home)
    repo = _fresh_repo(tmp_path, "project-default-subagent")

    _wire(dotbrain_home, repo, fake_home)

    assert config.load_project_subagents(dotbrain_home, "project-default-subagent") == ()
    project_yaml = paths.brainspace(dotbrain_home, "project-default-subagent") / ".brain" / "project.yaml"
    assert "agents:\n  - claude\n  - codex\n" in project_yaml.read_text()
    assert "\nsubagents:\n" not in project_yaml.read_text()


def test_agents_link_project_target_reports_actual_linked_files(
    dotbrain_home: Path, tmp_path: Path, fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    bootstrap_mod.ensure_data_root(dotbrain_home)
    repo = _fresh_repo(tmp_path, "claude-only-agent-link")
    _wire(dotbrain_home, repo, fake_home)
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))

    project_yaml = paths.brainspace(dotbrain_home, "claude-only-agent-link") / ".brain" / "project.yaml"
    project_yaml.write_text(project_yaml.read_text().replace("agents:\n  - claude\n  - codex\n", "agents:\n  - claude\n"))

    result = runner.invoke(
        app,
        ["agents", "link", "--scope", "project", "--target", "codex", "--project", "claude-only-agent-link"],
    )

    assert result.exit_code == 0, result.output
    assert "project: linked 0 subagent file(s) into claude-only-agent-link" in result.output


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
    assert (dest / "reviewer.toml").is_symlink()
    assert any(line.startswith("global: linked") for line in result.logs)


def test_link_global_subagents_warns_once_for_missing_name(
    dotbrain_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    set_fake_home(monkeypatch, tmp_path)
    (dotbrain_home / "agents").mkdir(parents=True, exist_ok=True)
    (dotbrain_home / "agents" / "agents.yaml").write_text("global:\n  - missing-agent\n")

    result = bootstrap_mod.link_global_subagents(dotbrain_home, "all")

    assert result.warnings == ["subagent not found: missing-agent"]


def test_link_global_skills_warns_when_config_missing(dotbrain_home: Path):
    result = bootstrap_mod.link_global_skills(dotbrain_home)

    assert not result.warnings


def test_wire_project_installs_hook_via_python(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    """wire_project with install_global_hook=True writes the hook to settings.json directly."""
    import json
    repo = _fresh_repo(tmp_path, "hooktest")
    workflows.wire_project(
        dotbrain_home=dotbrain_home, repo=repo, run_beads=False,
        install_global_hook=True, home=fake_home, run=_make_runner(),
    )
    settings = fake_home / ".claude" / "settings.json"
    assert settings.is_file()
    data = json.loads(settings.read_text())
    commands = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert any("dotbrain hook claude-worktree-bootstrap" in c for c in commands)


# --------------------------------------------------------------------------- per-project skills


def test_skills_link_project_creates_symlinks_after_wire(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """After wire_project, dotbrain skills link --scope project creates baseline skill symlinks."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = _fresh_repo(tmp_path, "skilltest")
    _wire(dotbrain_home, repo, fake_home)

    result = runner.invoke(app, ["skills", "link", "--scope", "project"])
    assert result.exit_code == 0, result.output

    brainspace = paths.brainspace(dotbrain_home, "skilltest")
    for skill in skills.project_baseline(dotbrain_home):
        name = Path(skill).name
        assert (brainspace / ".claude" / "skills" / name).is_symlink(), \
            f"expected .claude/skills/{name} to be linked"
        assert (brainspace / ".codex" / "skills" / name).is_symlink(), \
            f"expected .codex/skills/{name} to be linked"


def test_skills_link_project_prunes_stale_after_baseline_change(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Re-running skills link after a baseline change removes stale symlinks."""
    monkeypatch.setenv("DOTBRAIN_HOME", str(dotbrain_home))
    repo = _fresh_repo(tmp_path, "prunetest")
    _wire(dotbrain_home, repo, fake_home)

    runner.invoke(app, ["skills", "link", "--scope", "project"])

    # Plant a stale symlink pointing into skills/ (simulates a removed baseline entry)
    brainspace = paths.brainspace(dotbrain_home, "prunetest")
    skills_dir = brainspace / ".claude" / "skills"
    stale = skills_dir / "old-skill"
    stale.symlink_to((dotbrain_home / "skills" / "brain" / "wire-brain").resolve())

    runner.invoke(app, ["skills", "link", "--scope", "project"])

    assert not stale.exists(), "stale symlink should have been pruned"
