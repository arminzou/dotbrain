"""Tests for the embedded -> remote-server beads migration helper.

The subprocess seam takes a ``run`` callable. ``make_migrate_runner`` records argv, no-ops ``bd``
(returning canned ``bd stats --json`` for the pre/post count checks), and runs real ``git`` if it
ever appears, so tests stay hermetic without a live Dolt server.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from dotbrain import config, migrate, paths


def _stats_json(total: int) -> str:
    return json.dumps({"schema_version": 1, "summary": {"total_issues": total}})


def make_migrate_runner(calls: list[list[str]], *, pre_total: int = 3, post_total: int = 3):
    """A fake Runner: records every argv, answers ``bd stats --json`` pre then post."""
    state = {"stats_calls": 0}

    def run(argv, *, cwd=None, env=None, check=True):
        calls.append(list(argv))
        if argv[:3] == ["bd", "stats", "--json"]:
            state["stats_calls"] += 1
            total = pre_total if state["stats_calls"] == 1 else post_total
            return subprocess.CompletedProcess(list(argv), 0, _stats_json(total), "")
        if argv[0] == "git":
            return subprocess.run(
                list(argv), cwd=cwd, env=env, check=check, capture_output=True, text=True
            )
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    return run


def _seed_beads(control: Path, mode: str | None) -> None:
    """Give a control root a ``.beads`` with the given dolt_mode (or no metadata when None)."""
    beads = control / ".beads"
    beads.mkdir(parents=True, exist_ok=True)
    if mode is not None:
        (beads / "metadata.json").write_text(json.dumps({"dolt_mode": mode, "backend": "dolt"}))


# --------------------------------------------------------------------------- pure helpers


def test_destroy_token():
    assert migrate.destroy_token("dotbrain") == "DESTROY-dotbrain"


def test_backup_dir_outside_beads(tmp_path: Path):
    control = tmp_path / "projects" / "demo"
    assert migrate.backup_dir_for(control) == tmp_path / "backups" / "beads" / "demo"


def test_parse_total_issues():
    assert migrate.parse_total_issues(_stats_json(61)) == 61
    assert migrate.parse_total_issues("not json") is None
    assert migrate.parse_total_issues("{}") is None


def test_beads_mode(dotbrain_root: Path):
    embedded = paths.control_root(dotbrain_root, "emb")
    _seed_beads(embedded, "embedded")
    server = paths.control_root(dotbrain_root, "srv")
    _seed_beads(server, "server")
    nobeads = paths.control_root(dotbrain_root, "bare")
    nobeads.mkdir(parents=True)
    unknown = paths.control_root(dotbrain_root, "unk")
    _seed_beads(unknown, None)

    assert migrate.beads_mode(embedded) == "embedded"
    assert migrate.beads_mode(server) == "server"
    assert migrate.beads_mode(nobeads) == "none"
    assert migrate.beads_mode(unknown) == "unknown"


# --------------------------------------------------------------------------- migrate_project


def test_migrate_embedded_happy_path_emits_full_argv_sequence(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")
    calls: list[list[str]] = []

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root,
        project="example",
        server_host="10.0.0.1",
        server_port="3307",
        server_user="beads",
        run=make_migrate_runner(calls, pre_total=61, post_total=61),
    )

    assert result.status == "migrated"
    assert result.pre_count == result.post_count == 61
    backup = str(dotbrain_root / "backups" / "beads" / "example")
    init = [
        "bd", "init", "--stealth", "--prefix", "example",
        "--skip-agents", "--skip-hooks", "--non-interactive",
        "--server", "--external", "--server-host", "10.0.0.1", "--server-port", "3307",
        "--server-user", "beads", "--database", "example",
        "--reinit-local", "--destroy-token", "DESTROY-example", "--remote", "",
    ]
    assert calls == [
        ["bd", "stats", "--json"],
        ["bd", "backup", "init", backup],
        ["bd", "backup", "sync"],
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
         "10.0.0.1", "mkdir", "-p", str(dotbrain_root / "backups" / "beads")],
        ["rsync", "-a", "--delete", "-e", "ssh -o BatchMode=yes -o ConnectTimeout=10",
         f"{backup}/", f"10.0.0.1:{backup}/"],
        init,
        ["bd", "backup", "restore", "--force", backup],
        ["bd", "dolt", "test"],
        ["bd", "stats", "--json"],
    ]


def test_backup_copy_is_non_interactive():
    """ssh/rsync must use BatchMode + ConnectTimeout so a host-key prompt fails fast, not hangs."""
    ssh, rsync = migrate._backup_server_copy_argv("10.0.0.1", Path("/b/backup"))
    assert ssh[:5] == ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
    assert rsync[3] == "-e" and rsync[4] == "ssh -o BatchMode=yes -o ConnectTimeout=10"


def test_backup_copy_skipped_for_local_host():
    assert migrate._backup_server_copy_argv("localhost", Path("/b/backup")) == []


def test_migrate_database_override(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")
    calls: list[list[str]] = []

    migrate.migrate_project(
        dotbrain_root=dotbrain_root,
        project="example",
        server_host="h",
        database="custom-db",
        run=make_migrate_runner(calls),
    )
    init = next(c for c in calls if c[:2] == ["bd", "init"])
    assert "--database" in init and init[init.index("--database") + 1] == "custom-db"


def test_migrate_dry_run_emits_no_bd_calls(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")
    calls: list[list[str]] = []

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root,
        project="example",
        server_host="h",
        dry_run=True,
        run=make_migrate_runner(calls),
    )

    assert calls == []
    assert result.status == "dry-run"
    assert len(result.planned_commands) == 9
    assert result.planned_commands[0] == ["bd", "stats", "--json"]
    assert not list(dotbrain_root.glob(".beads.wire-project.*"))


def test_migrate_count_mismatch_aborts_project(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")
    calls: list[list[str]] = []

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root,
        project="example",
        server_host="h",
        run=make_migrate_runner(calls, pre_total=61, post_total=60),
    )

    assert result.status == "aborted-count-mismatch"
    assert any("left intact for rollback" in w for w in result.warnings)
    # no destroy/cleanup of embedded data is ever emitted
    assert not any(call[0] in {"rm", "rmdir"} for call in calls)
    assert not any(c.endswith("embeddeddolt") for call in calls for c in call)


def test_migrate_unverified_when_stats_unparseable(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")
    calls: list[list[str]] = []

    def run(argv, *, cwd=None, env=None, check=True):
        calls.append(list(argv))
        if argv[:3] == ["bd", "stats", "--json"]:
            return subprocess.CompletedProcess(list(argv), 0, "not json", "")
        return subprocess.CompletedProcess(list(argv), 0, "", "")

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root, project="example", server_host="h", run=run,
    )

    # migration commands ran, but the count check could not run -> unverified, not a clean success
    assert result.status == "migrated-unverified"
    assert result.pre_count is None and result.post_count is None
    assert any("could not verify issue count" in w for w in result.warnings)


def test_migrate_skips_server_mode_idempotent(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "server")
    calls: list[list[str]] = []

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root, project="example", server_host="h",
        run=make_migrate_runner(calls),
    )
    assert result.status == "skipped-server"
    assert calls == []


def test_migrate_skips_unknown_mode(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, None)  # .beads dir but no metadata.json
    calls: list[list[str]] = []

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root, project="example", server_host="h",
        run=make_migrate_runner(calls),
    )
    assert result.status == "skipped-unknown"
    assert calls == []


# --------------------------------------------------------- project-#0 symlink dance


def test_migrate_non_dotbrain_project_hides_root_beads(dotbrain_root: Path):
    # A repo-root .beads symlink that must be hidden while bd runs in a non-dotbrain control root.
    real = dotbrain_root / "projects" / "example" / ".beads"
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")
    (dotbrain_root / ".beads").symlink_to(real)
    calls: list[list[str]] = []

    seen = {"hidden_during_run": False}
    base_run = make_migrate_runner(calls)

    def spy(argv, *, cwd=None, env=None, check=True):
        if argv[:2] == ["bd", "init"]:
            seen["hidden_during_run"] = not (dotbrain_root / ".beads").exists() or \
                (dotbrain_root / ".beads").is_symlink() is False
        return base_run(argv, cwd=cwd, env=env, check=check)

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root, project="example", server_host="h", run=spy,
    )
    assert result.status == "migrated"
    # symlink restored afterward, no leftover temp
    assert (dotbrain_root / ".beads").is_symlink()
    assert not list(dotbrain_root.glob(".beads.wire-project.*"))


def test_migrate_dotbrain_project_does_not_hide_root_beads(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "dotbrain")
    _seed_beads(control, "embedded")
    real = control / ".beads"
    (dotbrain_root / ".beads").symlink_to(real)
    calls: list[list[str]] = []

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root, project="dotbrain", server_host="h",
        run=make_migrate_runner(calls),
    )
    assert result.status == "migrated"
    # dotbrain project: root .beads is never hidden, no temp created
    assert (dotbrain_root / ".beads").is_symlink()
    assert not list(dotbrain_root.glob(".beads.wire-project.*"))


# --------------------------------------------------------------------------- migrate_all


def test_migrate_all_mixes_embedded_and_server(dotbrain_root: Path):
    _seed_beads(paths.control_root(dotbrain_root, "emb"), "embedded")
    _seed_beads(paths.control_root(dotbrain_root, "srv"), "server")
    paths.control_root(dotbrain_root, "bare").mkdir(parents=True)
    calls: list[list[str]] = []

    results = migrate.migrate_all(
        dotbrain_root=dotbrain_root, server_host="h",
        run=make_migrate_runner(calls),
    )
    by_project = {r.project: r.status for r in results}
    assert by_project == {
        "emb": "migrated",
        "srv": "skipped-server",
        "bare": "skipped-no-beads",
    }
    # only the embedded project produced bd calls
    assert any(c[:2] == ["bd", "init"] for c in calls)
    assert sum(1 for c in calls if c[:2] == ["bd", "init"]) == 1


def test_safe_migrate_project_reports_ssh_failure_cleanly(dotbrain_root: Path):
    _seed_beads(paths.control_root(dotbrain_root, "emb"), "embedded")

    def failing_run(argv, *, cwd=None, env=None, check=True):
        if argv[0] == "ssh":
            raise subprocess.CalledProcessError(255, argv, stderr="Host key verification failed.")
        return subprocess.CompletedProcess(list(argv), 0, _stats_json(3), "")

    result = migrate.safe_migrate_project(
        dotbrain_root=dotbrain_root, project="emb", server_host="h", run=failing_run,
    )
    assert result.status == "failed"
    assert any("Host key verification failed" in w for w in result.warnings)
    assert any("ssh-keyscan" in w for w in result.warnings)


def test_migrate_removes_embedded_entry_from_config(dotbrain_root: Path):
    # After a successful migration the project is server-mode; a stale embedded
    # entry would make bootstrap hydrate it as embedded on a fresh clone.
    (dotbrain_root / "dotbrain.yaml").write_text(
        "version: 2\nprojects:\n  example:\n    beads:\n      mode: embedded\n"
    )
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")

    migrate.migrate_project(
        dotbrain_root=dotbrain_root,
        project="example",
        server_host="h",
        run=make_migrate_runner([], pre_total=3, post_total=3),
    )

    assert not (dotbrain_root / "projects" / "example" / "project.yaml").exists()


def test_migrate_records_custom_database_deviation(dotbrain_root: Path):
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")

    migrate.migrate_project(
        dotbrain_root=dotbrain_root,
        project="example",
        server_host="h",
        database="legacy_name",
        run=make_migrate_runner([], pre_total=3, post_total=3),
    )

    beads = config.load_project_config(dotbrain_root, "example")
    assert beads.mode == "server"
    assert beads.database == "legacy_name"


def test_migrate_abort_keeps_embedded_entry(dotbrain_root: Path):
    (dotbrain_root / "dotbrain.yaml").write_text(
        "version: 2\nprojects:\n  example:\n    beads:\n      mode: embedded\n"
    )
    control = paths.control_root(dotbrain_root, "example")
    _seed_beads(control, "embedded")

    result = migrate.migrate_project(
        dotbrain_root=dotbrain_root,
        project="example",
        server_host="h",
        run=make_migrate_runner([], pre_total=3, post_total=2),
    )

    assert result.status == "aborted-count-mismatch"
    assert config.load_project_config(dotbrain_root, "example").mode == "embedded"
