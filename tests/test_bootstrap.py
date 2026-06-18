"""Integration tests for bootstrap effects: claude hook install and per-project skill linking."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dotbrain import bootstrap as bootstrap_mod, paths, skills, workflows
from dotbrain.cli import app

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


def _wire(dotbrain_root, repo, fake_home):
    workflows.wire_project(
        dotbrain_root=dotbrain_root, repo=repo, run_beads=False,
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
    assert result.skills_seeded
    assert skills_config.is_file()
    # Seeded via the same renderer reconcile uses, so the first link is a no-op rewrite.
    before = skills_config.read_text()
    skills.reconcile_global_config(skills_config)
    assert skills_config.read_text() == before


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
    dotbrain_root: Path, fake_home: Path, tmp_path: Path
):
    """install_global_claude_hook writes the SessionStart hook to settings.json via Python."""
    import json
    settings = tmp_path / ".claude" / "settings.json"
    bootstrap_mod.install_global_claude_hook(dotbrain_root, settings=settings, home=fake_home)
    data = json.loads(settings.read_text())
    commands = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert any("dotbrain hook claude-worktree-bootstrap" in c for c in commands)


def test_link_global_skills_links_configured_target(dotbrain_root: Path, tmp_path: Path):
    dest = tmp_path / "codex-skills"
    (dotbrain_root / "skills" / "skills.yaml").write_text(
        "targets:\n"
        f"  codex: {dest}\n"
        "global_baseline:\n"
        "  - brain/wire-brain\n"
    )

    result = bootstrap_mod.link_global_skills(dotbrain_root, "codex")

    assert result.warnings == []
    assert (dest / "wire-brain").is_symlink()
    assert any("global: linked 1 skill(s)" in line for line in result.logs)


def test_link_global_skills_warns_when_config_missing(dotbrain_root: Path):
    result = bootstrap_mod.link_global_skills(dotbrain_root)

    assert not result.warnings


def test_wire_project_installs_hook_via_python(
    dotbrain_root: Path, fake_home: Path, tmp_path: Path
):
    """wire_project with install_global_hook=True writes the hook to settings.json directly."""
    import json
    repo = _fresh_repo(tmp_path, "hooktest")
    workflows.wire_project(
        dotbrain_root=dotbrain_root, repo=repo, run_beads=False,
        install_global_hook=True, home=fake_home, run=_make_runner(),
    )
    settings = fake_home / ".claude" / "settings.json"
    assert settings.is_file()
    data = json.loads(settings.read_text())
    commands = [h["command"] for e in data["hooks"]["SessionStart"] for h in e["hooks"]]
    assert any("dotbrain hook claude-worktree-bootstrap" in c for c in commands)


# --------------------------------------------------------------------------- per-project skills


def test_skills_link_project_creates_symlinks_after_wire(
    dotbrain_root: Path, fake_home: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """After wire_project, dotbrain skills link --scope project creates baseline skill symlinks."""
    monkeypatch.setenv("DOTBRAIN_ROOT", str(dotbrain_root))
    repo = _fresh_repo(tmp_path, "skilltest")
    _wire(dotbrain_root, repo, fake_home)

    result = runner.invoke(app, ["skills", "link", "--scope", "project"])
    assert result.exit_code == 0, result.output

    control = paths.control_root(dotbrain_root, "skilltest")
    for skill in skills.project_baseline(dotbrain_root):
        name = Path(skill).name
        assert (control / ".claude" / "skills" / name).is_symlink(), \
            f"expected .claude/skills/{name} to be linked"
    assert not (control / ".codex").exists()


def test_skills_link_project_prunes_stale_after_baseline_change(
    dotbrain_root: Path, fake_home: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Re-running skills link after a baseline change removes stale symlinks."""
    monkeypatch.setenv("DOTBRAIN_ROOT", str(dotbrain_root))
    repo = _fresh_repo(tmp_path, "prunetest")
    _wire(dotbrain_root, repo, fake_home)

    runner.invoke(app, ["skills", "link", "--scope", "project"])

    # Plant a stale symlink pointing into skills/ (simulates a removed baseline entry)
    control = paths.control_root(dotbrain_root, "prunetest")
    skills_dir = control / ".claude" / "skills"
    stale = skills_dir / "old-skill"
    stale.symlink_to((dotbrain_root / "skills" / "brain" / "wire-brain").resolve())

    runner.invoke(app, ["skills", "link", "--scope", "project"])

    assert not stale.exists(), "stale symlink should have been pruned"
