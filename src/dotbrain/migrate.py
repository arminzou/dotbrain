"""Migrate a project's beads tracker from embedded Dolt to a remote sql-server.

dotbrain adopters start local-by-default: ``dotbrain wire`` initialises beads with an embedded
Dolt engine. Moving an already-wired brain onto a shared sql-server has to preserve the full
Dolt commit graph, so this uses ``bd backup`` (Dolt-native, history-preserving) rather than the
``bd export`` JSONL path, which drops branches/history.

Per-project sequence (all ``bd`` calls run with ``cwd=<brainspace>`` and ``_beads_env(brainspace)``):

1. ``bd stats --json``                     -> capture ``summary.total_issues`` (pre_count)
2. ``bd backup init <backup-dir>``
3. ``bd backup sync``                       -> full Dolt backup of the embedded db
4. ``bd init --server --external ... --reinit-local --destroy-token DESTROY-<prefix>``
                                            -> repoint .beads at the server (fresh empty db)
5. ``bd backup restore --force <backup-dir>`` -> load full history into the server db
6. ``bd dolt test``                         -> connection sanity
7. ``bd stats --json``                      -> post_count; assert it matches pre_count

The embedded ``.beads/embeddeddolt`` and the backup dir are kept by default as the rollback path;
cleanup stays manual until a migration's history depth is verified on the server.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from dotbrain import config, paths
from dotbrain.beads import (
    Runner,
    _bd_init_args,
    _beads_env,
    _default_run,
    _hide_root_beads,
    _restore_root_beads,
    normalize_server_beads_metadata,
)


# --------------------------------------------------------------------------- pure helpers


def destroy_token(project: str) -> str:
    """The non-interactive ``bd init`` confirmation token for re-initialising over local data."""
    return f"DESTROY-{project}"


def backup_dir_for(brainspace: Path) -> Path:
    """Backup destination, kept outside tracked project Brainspaces."""
    brainspace = Path(brainspace)
    return brainspace.parent.parent / "backups" / "beads" / brainspace.name


def parse_total_issues(stdout: str) -> int | None:
    """Pull ``summary.total_issues`` out of ``bd stats --json``; None when it can't be parsed."""
    try:
        return int(json.loads(stdout)["summary"]["total_issues"])
    except (ValueError, KeyError, TypeError):
        return None


def beads_mode(brainspace: Path) -> str:
    """Classify a Brainspace's beads backend: ``embedded`` | ``server`` | ``none`` | ``unknown``.

    Reads ``.beads/metadata.json`` directly (the same file bootstrap inspects); avoids shelling out.
    """
    metadata = Path(brainspace) / ".beads" / "metadata.json"
    if not (Path(brainspace) / ".beads").is_dir():
        return "none"
    if not metadata.is_file():
        return "unknown"
    try:
        data = json.loads(metadata.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "unknown"
    mode = str(data.get("dolt_mode", "")).strip()
    if mode == "embedded":
        return "embedded"
    if mode in {"server", "external"}:
        return "server"
    return "unknown"


# --------------------------------------------------------------------------- result type


@dataclass
class MigrationResult:
    project: str = ""
    brainspace: Path | None = None
    status: str = ""  # migrated|migrated-unverified|skipped-server|skipped-no-beads|skipped-unknown|aborted-count-mismatch|dry-run|failed
    pre_count: int | None = None
    post_count: int | None = None
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    planned_commands: list[list[str]] = field(default_factory=list)


# --------------------------------------------------------------------------- orchestration


def _migration_argv(
    project: str, database: str, host: str, port: str, user: str, backup: Path
) -> list[list[str]]:
    """The ordered bd command sequence for one embedded -> server migration."""
    return [
        ["bd", "stats", "--json"],
        ["bd", "backup", "init", str(backup)],
        ["bd", "backup", "sync"],
        *_backup_server_copy_argv(host, backup),
        _bd_init_args(
            project, "", host, port, user, database or project,
            reinit_local=True, destroy_token=destroy_token(project),
        ),
        ["bd", "backup", "restore", "--force", str(backup)],
        ["bd", "dolt", "test"],
        ["bd", "stats", "--json"],
    ]


# Non-interactive SSH for the backup copy: the migration runs with no TTY, so a
# first-connect host-key prompt or an unreachable server would hang it forever.
# BatchMode disables prompts and ConnectTimeout bounds the wait, turning either
# case into a fast, surfaced error instead of a silent stall.
_SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
_RSYNC_SSH = "ssh " + " ".join(_SSH_OPTS)


def _host_is_local(host: str) -> bool:
    return host in {"", "localhost", "127.0.0.1", "::1"}


def _backup_server_copy_argv(host: str, backup: Path) -> list[list[str]]:
    """Make a local file:// backup visible to a remote external Dolt server."""
    if _host_is_local(host):
        return []
    return [
        ["ssh", *_SSH_OPTS, host, "mkdir", "-p", str(backup.parent)],
        ["rsync", "-a", "--delete", "-e", _RSYNC_SSH, f"{backup}/", f"{host}:{backup}/"],
    ]


def migrate_project(
    *,
    dotbrain_home: Path,
    project: str,
    server_host: str,
    server_port: str = "3307",
    server_user: str = "beads",
    database: str = "",
    dry_run: bool = False,
    run: Runner = _default_run,
) -> MigrationResult:
    dotbrain_home = Path(dotbrain_home)
    brainspace = paths.brainspace(dotbrain_home, project)
    result = MigrationResult(project=project, brainspace=brainspace)

    mode = beads_mode(brainspace)
    if mode == "server":
        result.status = "skipped-server"
        result.logs.append(f"{project}: already on a Dolt server; nothing to migrate")
        return result
    if mode == "none":
        result.status = "skipped-no-beads"
        result.logs.append(f"{project}: no .beads to migrate")
        return result
    if mode == "unknown":
        result.status = "skipped-unknown"
        result.warnings.append(
            f"{project}: could not determine beads mode from metadata.json; skipping to avoid a "
            "destructive re-init"
        )
        return result

    database = database or project
    backup = backup_dir_for(brainspace)
    commands = _migration_argv(
        project, database, server_host, server_port, server_user, backup
    )
    backup_copy_commands = _backup_server_copy_argv(server_host, backup)
    init_args = commands[3 + len(backup_copy_commands)]

    if dry_run:
        result.status = "dry-run"
        result.planned_commands = commands
        result.logs.append(f"{project}: dry-run; {len(commands)} bd commands planned")
        return result

    env = _beads_env(brainspace)
    hidden = _hide_root_beads(brainspace, dotbrain_home)
    try:
        stats_pre = run(["bd", "stats", "--json"], cwd=brainspace, env=env, check=True)
        result.pre_count = parse_total_issues(stats_pre.stdout or "")

        backup.parent.mkdir(parents=True, exist_ok=True)
        run(["bd", "backup", "init", str(backup)], cwd=brainspace, env=env, check=True)
        run(["bd", "backup", "sync"], cwd=brainspace, env=env, check=True)
        for argv in backup_copy_commands:
            run(argv, cwd=brainspace, env=env, check=True)
        run(init_args, cwd=brainspace, env=env, check=True)  # bd init --server ... --reinit-local
        run(["bd", "backup", "restore", "--force", str(backup)], cwd=brainspace, env=env, check=True)
        run(["bd", "dolt", "test"], cwd=brainspace, env=env, check=True)
        # bd writes the legacy dolt_server_port into metadata.json; make the port file primary.
        normalize_server_beads_metadata(brainspace / ".beads", server_port)

        stats_post = run(["bd", "stats", "--json"], cwd=brainspace, env=env, check=True)
        result.post_count = parse_total_issues(stats_post.stdout or "")
    finally:
        _restore_root_beads(hidden, dotbrain_home)

    if result.pre_count is None or result.post_count is None:
        result.status = "migrated-unverified"
        result.warnings.append(
            f"{project}: migrated, but could not verify issue count from bd stats; verify history "
            "depth on the server before removing embedded data"
        )
        _record_migrated_backend(dotbrain_home, project, database, result)
        return result
    if result.post_count != result.pre_count:
        result.status = "aborted-count-mismatch"
        result.warnings.append(
            f"{project}: post-restore count {result.post_count} != pre-migration "
            f"{result.pre_count}; embedded data and backup left intact for rollback"
        )
        return result

    result.status = "migrated"
    result.logs.append(
        f"{project}: migrated to {server_host}:{server_port}/{database} "
        f"({result.post_count} issues); embedded data + backup kept for rollback"
    )
    _record_migrated_backend(dotbrain_home, project, database, result)
    return result


def _record_migrated_backend(
    dotbrain_home: Path, project: str, database: str, result: MigrationResult
) -> None:
    """The project is on the server now; its dotbrain.yaml entry must say so."""
    if database != project:
        log = config.record_project_beads(
            dotbrain_home, project, config.ProjectBeads(mode="server", database=database)
        )
    else:
        log = config.remove_project_beads(dotbrain_home, project)
    if log:
        result.logs.append(log)


def _looks_like_ssh_failure(exc: Exception) -> bool:
    """True when the failed command was the ssh/rsync backup copy (a likely host-key issue)."""
    cmd = getattr(exc, "cmd", None)
    return bool(cmd) and cmd[0] in {"ssh", "rsync"}


def safe_migrate_project(**kwargs) -> MigrationResult:
    """``migrate_project`` that turns any subprocess failure into a ``failed`` result.

    Both the single-project CLI path and the ``--all`` sweep use this so a failed migration
    reports a clean status and an actionable hint instead of crashing with a traceback. Accepts
    the same keyword arguments as ``migrate_project``.
    """
    project = kwargs.get("project", "")
    try:
        return migrate_project(**kwargs)
    except Exception as exc:
        brainspace = paths.brainspace(Path(kwargs["dotbrain_home"]), project) if project else None
        detail = str(exc)
        stderr = (getattr(exc, "stderr", "") or "").strip()
        if stderr:
            detail = f"{detail}: {stderr}"
        warnings = [f"{project}: migration failed: {detail}"]
        if _looks_like_ssh_failure(exc):
            warnings.append(
                f"{project}: the Dolt server's SSH host key may be untrusted; trust it first "
                "(e.g. `ssh-keyscan <host> >> ~/.ssh/known_hosts`) and retry"
            )
        return MigrationResult(project=project, brainspace=brainspace, status="failed", warnings=warnings)


def migrate_all(
    *,
    dotbrain_home: Path,
    server_host: str,
    server_port: str = "3307",
    server_user: str = "beads",
    dry_run: bool = False,
    run: Runner = _default_run,
) -> list[MigrationResult]:
    """Migrate every embedded Brainspace; skip server/none ones; never abort the whole sweep."""
    dotbrain_home = Path(dotbrain_home)
    return [
        safe_migrate_project(
            dotbrain_home=dotbrain_home,
            project=brainspace.name,
            server_host=server_host,
            server_port=server_port,
            server_user=server_user,
            dry_run=dry_run,
            run=run,
        )
        for brainspace in paths.brainspaces(dotbrain_home)
    ]
