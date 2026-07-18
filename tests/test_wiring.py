"""Tests for the wire-project port (pure helpers, tmp_path mutators, injected seams).

The subprocess seams take a ``run`` callable. ``make_runner`` runs real ``git`` (the fixtures are
real repos) but no-ops ``bd`` and script invocations, so tests stay hermetic and record argv.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from dotbrain import beads, config, paths, workflows


def make_runner(calls: list[list[str]]):
    def run(argv, *, cwd=None, env=None, check=True):
        calls.append(list(argv))
        if argv[0] == "git":
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    return run


# --------------------------------------------------------------------------- subprocess seams


def test_init_beads_skips_when_disabled(dotbrain_home: Path, brainspace: Path):
    calls: list[list[str]] = []
    assert (
        beads.init_beads(brainspace, "example", dotbrain_home, run_beads=False, run=make_runner(calls))
        is None
    )
    assert calls == []


def test_init_beads_skips_when_already_present(dotbrain_home: Path, brainspace: Path):
    # the brainspace fixture already has a .beads dir
    calls: list[list[str]] = []
    assert beads.init_beads(brainspace, "example", dotbrain_home, run=make_runner(calls)) is None
    assert calls == []


def test_normalize_server_beads_metadata_drops_port_key_keeps_identity(tmp_path: Path):
    beads_dir = tmp_path / ".beads"
    beads_dir.mkdir()
    (beads_dir / "metadata.json").write_text(json.dumps({
        "backend": "dolt", "dolt_mode": "server", "dolt_server_host": "h",
        "dolt_server_port": 3307, "dolt_database": "test", "project_id": "abc-123",
    }))

    beads.normalize_server_beads_metadata(beads_dir, "3307")

    data = json.loads((beads_dir / "metadata.json").read_text())
    assert "dolt_server_port" not in data          # deprecated key removed
    assert data["project_id"] == "abc-123"          # identity preserved
    assert data["dolt_database"] == "test"
    assert (beads_dir / "dolt-server.port").read_text().strip() == "3307"  # port file is primary


def test_init_beads_preserves_repo_root_beads_symlink(dotbrain_home: Path):
    # project #0's repo-root .beads is gitignored local wiring pointing at projects/dotbrain/.beads
    proj0_beads = dotbrain_home / "brainspaces" / "dotbrain" / ".beads"
    proj0_beads.mkdir(parents=True)
    root_beads = dotbrain_home / ".beads"
    root_beads.symlink_to("brainspaces/dotbrain/.beads")

    brainspace = dotbrain_home / "brainspaces" / "example"
    brainspace.mkdir(parents=True)

    def run(argv, *, cwd=None, env=None, check=True, **kwargs):
        if argv[:2] == ["bd", "init"]:
            # bd init runs with git top-level = dotbrain and recreates a root .beads pointing at
            # the wired project — the hijack that restore must undo.
            (brainspace / ".beads").mkdir(exist_ok=True)
            if not (dotbrain_home / ".beads").exists():
                (dotbrain_home / ".beads").symlink_to("brainspaces/example/.beads")
            return subprocess.CompletedProcess(list(argv), 0, "", "")
        if argv[0] == "git":
            return subprocess.run(list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True)
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    beads.init_beads(brainspace, "example", dotbrain_home, run=run)

    # TEMP DIAGNOSTIC: narrowing down a Windows-only failure in the hide/restore rename logic.
    hidden_files = list(dotbrain_home.glob(".beads.wire-project.*"))
    print(f"DIAG root_beads.is_symlink()={root_beads.is_symlink()}")
    if root_beads.is_symlink():
        print(f"DIAG root_beads readlink={os.readlink(root_beads)!r}")
        print(f"DIAG root_beads.resolve()={root_beads.resolve()!r}")
    print(f"DIAG proj0_beads.resolve()={proj0_beads.resolve()!r}")
    print(f"DIAG hidden_files_remaining={hidden_files!r}")
    for hf in hidden_files:
        hf_readlink = repr(os.readlink(hf)) if hf.is_symlink() else "N/A"
        print(
            f"DIAG hidden {hf!r} is_symlink={hf.is_symlink()} exists={hf.exists()} "
            f"readlink={hf_readlink}"
        )

    assert root_beads.is_symlink()
    assert root_beads.resolve() == proj0_beads.resolve()  # still project #0, not example
    assert not hidden_files  # no orphaned hidden file


def test_init_beads_rejects_conflicting_backends(dotbrain_home: Path, tmp_path: Path):
    brainspace = dotbrain_home / "brainspaces" / "fresh"
    brainspace.mkdir(parents=True)
    with pytest.raises(ValueError):
        beads.init_beads(
            brainspace, "fresh", dotbrain_home,
            remote="https://example/r", server_host="db.local",
            run=make_runner([]),
        )


def _runner_failing_bd_init(calls: list[list[str]], stderr: str):
    """A runner whose ``bd init`` raises CalledProcessError; git runs for real, rest no-op."""
    def run(argv, *, cwd=None, env=None, check=True):
        calls.append(list(argv))
        if argv[:2] == ["bd", "init"]:
            raise subprocess.CalledProcessError(1, list(argv), output="", stderr=stderr)
        if argv[0] == "git":
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    return run


def test_init_beads_attaches_to_existing_server_db(dotbrain_home: Path):
    # bd init reports the server DB already exists -> attach via metadata hydration.
    brainspace = dotbrain_home / "brainspaces" / "fresh"
    brainspace.mkdir(parents=True)
    calls: list[list[str]] = []
    run = _runner_failing_bd_init(calls, "can't create database fresh; database exists")

    log = beads.init_beads(
        brainspace, "fresh", dotbrain_home,
        server_host="db.local", server_port="3307", server_user="beads",
        run=run,
    )

    assert log is not None and "attached" in log
    metadata = json.loads((brainspace / ".beads" / "metadata.json").read_text())
    assert metadata["dolt_mode"] == "server"
    assert metadata["dolt_server_host"] == "db.local"
    assert metadata["dolt_database"] == "fresh"
    assert (brainspace / ".beads" / "dolt-server.port").read_text().strip() == "3307"
    assert not (brainspace / ".beads" / "config.yaml").exists()
    assert ["bd", "dolt", "test"] in calls


def test_init_beads_surfaces_clean_error_on_other_failure(dotbrain_home: Path):
    # Any non-"exists" bd init failure becomes a RuntimeError carrying bd stderr (no attach, no
    # raw traceback).
    brainspace = dotbrain_home / "brainspaces" / "fresh"
    brainspace.mkdir(parents=True)
    calls: list[list[str]] = []
    run = _runner_failing_bd_init(calls, "dial tcp db.local:3307: connection refused")

    with pytest.raises(RuntimeError) as excinfo:
        beads.init_beads(brainspace, "fresh", dotbrain_home, server_host="db.local", run=run)

    assert "connection refused" in str(excinfo.value)
    assert not (brainspace / ".beads" / "metadata.json").exists()
    assert ["bd", "dolt", "pull"] not in calls


def test_bd_init_args_reinit_local_form():
    # Default call is byte-identical to the non-reinit server form (guards wire regression).
    base = beads._bd_init_args("p", "", "h", "3307", "u", "db")
    assert base[-4:] == ["--database", "db", "--remote", ""]
    assert "--reinit-local" not in base and "--destroy-token" not in base
    # Migration form appends the reinit + destroy-token flags after the server block.
    reinit = beads._bd_init_args(
        "p", "", "h", "3307", "u", "db", reinit_local=True, destroy_token="DESTROY-p"
    )
    assert reinit[: len(base) - 2] == base[:-2]
    assert reinit[-5:] == ["--reinit-local", "--destroy-token", "DESTROY-p", "--remote", ""]
    # reinit flags only apply in server mode, not embedded/remote.
    local = beads._bd_init_args("p", "r", "", "3307", "u", "db", reinit_local=True)
    assert "--reinit-local" not in local
    assert local[-2:] == ["--remote", "r"]

    local_default = beads._bd_init_args("p", "", "", "3307", "u", "db")
    assert local_default[-2:] == ["--remote", ""]


def test_default_run_uses_devnull_stdin(monkeypatch):
    # bd auto-enables non-interactive mode on a non-TTY stdin; without DEVNULL a destructive
    # prompt (e.g. bd init --reinit-local) blocks forever on the terminal. Guard the seam.
    captured: dict = {}

    def fake_run(argv, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    beads._default_run(["bd", "stats"])
    assert captured["stdin"] is subprocess.DEVNULL
    assert captured["capture_output"] is True


def test_wire_project_rejects_foreign_dotbrain_symlink_before_brainspace_mutation(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    repo = tmp_path / "adopter"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    foreign_root = tmp_path / "foreign-dotbrain"
    foreign_root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=foreign_root, check=True)
    (foreign_root / "templates" / ".brain").mkdir(parents=True)
    (foreign_root / "templates" / ".brain" / "AGENTS.md").write_text("# foreign\n")
    foreign_brainspace = foreign_root / "brainspaces" / "adopter"
    for name in paths.BRAINSPACE_LINKS:
        (foreign_brainspace / name).mkdir(parents=True, exist_ok=True)

    (repo / ".brain").symlink_to(foreign_brainspace / ".brain")

    with pytest.raises(RuntimeError, match="another dotbrain checkout"):
        workflows.wire_project(
            dotbrain_home=dotbrain_home,
            repo=repo,
            run_beads=False,
            install_global_hook=False,
            home=fake_home,
            run=make_runner([]),
        )

    assert not (dotbrain_home / "brainspaces" / "adopter").exists()


def test_wire_project_allows_custom_symlink_that_only_matches_dotbrain_shape(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    repo = tmp_path / "custom-shaped"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    custom_target = tmp_path / "srv" / "brainspaces" / "custom-shaped" / ".brain"
    custom_target.mkdir(parents=True)
    (repo / ".brain").symlink_to(custom_target)

    result = workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
        run=make_runner([]),
    )

    brainspace = dotbrain_home / "brainspaces" / "custom-shaped"
    assert result.brainspace == brainspace
    assert (repo / ".brain").is_symlink()
    assert (repo / ".brain").resolve() == (brainspace / ".brain").resolve()


# --------------------------------------------------------------------------- orchestration


def test_wire_project_wires_fixture_repo(dotbrain_home: Path, fake_home: Path, tmp_path: Path):
    repo = tmp_path / "adopter"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "AGENTS.md").write_text("# Adopter\n")

    result = workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
        run=make_runner([]),
    )

    brainspace = dotbrain_home / "brainspaces" / "adopter"
    assert result.brainspace == brainspace
    assert (brainspace / ".brain" / "AGENTS.md").is_file()
    # repo links: .beads is skipped because --skip-beads never created brainspace/.beads
    for name in (".brain", ".claude", ".codex"):
        assert (repo / name).is_symlink()
        assert (repo / name).resolve() == (brainspace / name).resolve()
    assert {"/.brain", "/.claude", "/.codex"} <= paths.exclude_entries(repo)
    if paths.INJECT_ADOPTER_POINTER:
        assert paths.ADOPTER_POINTER in (repo / "AGENTS.md").read_text()
    assert any(".beads is missing" in w for w in result.warnings)


def test_wire_project_brain_only(dotbrain_home: Path, fake_home: Path):
    result = workflows.wire_project(
        dotbrain_home=dotbrain_home,
        project="brainonly",
        no_repo=True,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
        run=make_runner([]),
    )
    brainspace = dotbrain_home / "brainspaces" / "brainonly"
    assert result.repo is None
    assert (brainspace / ".repo").read_text() == "(brain-only)\n"
    assert (brainspace / ".brain" / "AGENTS.md").is_file()


def test_wire_project_unarchives_automatically(dotbrain_home: Path, fake_home: Path, tmp_path: Path):
    """dotbrain wire on an archived project restores it before wiring."""
    repo = tmp_path / "archived-proj"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)

    # Simulate an archived Brainspace
    archive = dotbrain_home / "brainspaces" / ".archive" / "archived-proj"
    archive.mkdir(parents=True)
    (archive / ".brain").mkdir()
    (archive / ".brain" / "AGENTS.md").write_text("# archived\n")
    subprocess.run(
        ["git", "-C", str(dotbrain_home), "add", "brainspaces/.archive/archived-proj"],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(dotbrain_home), "commit", "-q", "-m", "archive"],
        check=True, capture_output=True,
    )

    result = workflows.wire_project(
        dotbrain_home=dotbrain_home, repo=repo, run_beads=False,
        install_global_hook=False, home=fake_home, run=make_runner([]),
    )

    brainspace = dotbrain_home / "brainspaces" / "archived-proj"
    assert brainspace.is_dir()
    assert not archive.exists()
    assert any("unarchived" in l for l in result.logs)
    assert (repo / ".brain").is_symlink()


def test_wire_project_does_not_seed_skills_manifest(dotbrain_home: Path, fake_home: Path, tmp_path: Path):
    """Per-project skills live in project.yaml now; wire must not create the legacy manifest."""
    repo = tmp_path / "with-manifest"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)

    workflows.wire_project(
        dotbrain_home=dotbrain_home, repo=repo, run_beads=False,
        install_global_hook=False, home=fake_home, run=make_runner([]),
    )

    from dotbrain import config, skills
    brainspace = paths.brainspace(dotbrain_home, "with-manifest")
    assert not (brainspace / ".brain" / "agents" / "skills.yaml").exists()
    # The link set is the brain-coupled required core plus project.yaml extras (none here).
    extras = config.load_project_skills(dotbrain_home, "with-manifest")
    assert skills.project_link_set(extras) == skills.project_baseline()


def test_wire_project_greenfield_empty_repo(dotbrain_home: Path, fake_home: Path, tmp_path: Path):
    """Scenario 5: git init with no commits, no AGENTS.md — wire creates AGENTS.md from scratch."""
    repo = tmp_path / "greenfield"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    # no commits, no AGENTS.md

    result = workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
        run=make_runner([]),
    )

    brainspace = dotbrain_home / "brainspaces" / "greenfield"
    assert result.brainspace == brainspace
    agents = repo / "AGENTS.md"
    if paths.INJECT_ADOPTER_POINTER:
        assert agents.is_file()
        assert paths.ADOPTER_POINTER in agents.read_text()
    for name in (".brain", ".claude", ".codex"):
        assert (repo / name).is_symlink()
    assert {"/.brain", "/.claude", "/.codex"} <= paths.exclude_entries(repo)


def test_wire_project_repair_idempotency(dotbrain_home: Path, fake_home: Path, tmp_path: Path):
    """Scenario 8: break a symlink then re-run wire_project; link is restored, no duplicate state."""
    repo = tmp_path / "repairme"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "AGENTS.md").write_text("# Project\n")

    kwargs = dict(dotbrain_home=dotbrain_home, repo=repo, run_beads=False,
                  install_global_hook=False, home=fake_home, run=make_runner([]))

    workflows.wire_project(**kwargs)
    assert (repo / ".brain").is_symlink()

    # simulate breakage
    (repo / ".brain").unlink()
    assert not (repo / ".brain").exists()

    # repair
    workflows.wire_project(**kwargs)
    assert (repo / ".brain").is_symlink()
    brainspace = dotbrain_home / "brainspaces" / "repairme"
    assert (repo / ".brain").resolve() == (brainspace / ".brain").resolve()

    # pointer must not be duplicated in AGENTS.md
    if paths.INJECT_ADOPTER_POINTER:
        text = (repo / "AGENTS.md").read_text()
        assert text.count(paths.ADOPTER_POINTER) == 1


def test_wire_project_records_embedded_deviation(dotbrain_home: Path, fake_home: Path):
    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        project="fork",
        no_repo=True,
        remote="https://example.com/fork",
        install_global_hook=False,
        home=fake_home,
        run=make_runner([]),
    )
    beads = config.load_project_config(dotbrain_home, "fork")
    assert beads.mode == "embedded"
    assert beads.remote == "https://example.com/fork"


def _runner_creating_beads(brainspace: Path):
    """Like make_runner, but ``bd init`` creates the .beads dir as the real bd would."""
    def run(argv, *, cwd=None, env=None, check=True):
        if argv[:2] == ["bd", "init"]:
            (brainspace / ".beads").mkdir(parents=True, exist_ok=True)
        if argv[0] == "git":
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    return run


def test_wire_project_server_host_records_server_mode(
    dotbrain_home: Path, fake_home: Path
):
    brainspace = dotbrain_home / "brainspaces" / "plain"
    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        project="plain",
        no_repo=True,
        server_host="db.local",
        install_global_hook=False,
        home=fake_home,
        run=_runner_creating_beads(brainspace),
    )
    # embedded is the default; an explicit server_host deviates and is recorded in project.yaml.
    assert (dotbrain_home / "brainspaces" / "plain" / ".brain" / "project.yaml").exists()
    assert config.load_project_config(dotbrain_home, "plain").mode == "server"


def test_wire_project_records_custom_database(dotbrain_home: Path, fake_home: Path):
    brainspace = dotbrain_home / "brainspaces" / "renamed"
    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        project="renamed",
        no_repo=True,
        server_host="db.local",
        database="legacy_name",
        install_global_hook=False,
        home=fake_home,
        run=_runner_creating_beads(brainspace),
    )
    beads = config.load_project_config(dotbrain_home, "renamed")
    assert beads.mode == "server"
    assert beads.database == "legacy_name"


def test_wire_project_honors_declared_agent_workspaces(dotbrain_home: Path, fake_home: Path, tmp_path: Path):
    repo = tmp_path / "claude-only"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)

    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
    )

    brainspace = dotbrain_home / "brainspaces" / "claude-only"
    assert (brainspace / ".claude").is_dir()
    assert (brainspace / ".codex").is_dir()
    assert (repo / ".claude").is_symlink()
    assert (repo / ".codex").is_symlink()


def test_wire_project_does_not_rewire_preserved_undeclared_workspace(
    dotbrain_home: Path, fake_home: Path, tmp_path: Path
):
    repo = tmp_path / "downgraded-project"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)

    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
    )
    brainspace = dotbrain_home / "brainspaces" / "downgraded-project"

    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n  - codex\n")
    workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
    )
    assert (repo / ".codex").is_symlink()
    assert (brainspace / ".codex").is_dir()

    (brainspace / ".brain" / "project.yaml").write_text("agents:\n  - claude\n")
    (repo / ".codex").unlink()
    result = workflows.wire_project(
        dotbrain_home=dotbrain_home,
        repo=repo,
        run_beads=False,
        install_global_hook=False,
        home=fake_home,
    )

    assert (brainspace / ".codex").is_dir()
    assert not (repo / ".codex").exists()
    assert not any(".codex is not wired" in warning for warning in result.warnings)
