"""Beads tracker setup, hydration, and admin.

Everything that drives the ``bd`` CLI and the ``.beads`` workspace, in three bands:

- **init**: ``bd init --stealth`` in a Brainspace, server-mode metadata
  (write/normalize/attach), and the project-#0 root-``.beads`` hijack guard.
- **load/hydrate**: bring a Brainspace's ``.beads`` into existence from ``config.yaml`` and pull
  remote state, plus the dry-run preview.
- **remote admin**: list/drop databases on the shared Dolt sql-server.

The embedded-to-server migration workflow stays in ``migrate.py`` (it composes these helpers).
This module depends only on ``config`` and ``paths``.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from dotbrain import config, paths

# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]

_DB_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_PROTECTED_DATABASES = {"dotbrain"}


@dataclass
class BootstrapResult:
    wired: list[str] = field(default_factory=list)
    pulled: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _default_run(
    argv: Sequence[str], *, cwd: Path | None = None, env: dict | None = None, check: bool = True
) -> "subprocess.CompletedProcess[str]":
    # stdin=DEVNULL is load-bearing: bd auto-enables non-interactive mode on a non-TTY stdin,
    # so destructive steps (e.g. bd init --reinit-local) skip their confirmation prompt instead
    # of blocking forever on terminal input while capture_output swallows the prompt text.
    return subprocess.run(
        list(argv), cwd=cwd, env=env, check=check,
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )


# --------------------------------------------------------------------------- init & server metadata


def write_server_beads_metadata(
    beads_dir: Path, *, host: str, port: str, user: str, database: str
) -> None:
    """Write the server-mode ``.beads/metadata.json`` + ``dolt-server.port`` (shape).

    Also normalizes the ``.beads`` dir to ``0700`` — bd expects a private beads dir and warns
    otherwise; this matches what ``bd init`` creates.
    """
    beads_dir = Path(beads_dir)
    beads_dir.chmod(0o700)
    (beads_dir / "metadata.json").write_text(json.dumps({
        "database": "dolt",
        "backend": "dolt",
        "dolt_mode": "server",
        "dolt_server_host": host,
        "dolt_server_user": user,
        "dolt_database": database,
    }, indent=2) + "\n")
    (beads_dir / "dolt-server.port").write_text(f"{port}\n")


def normalize_server_beads_metadata(beads_dir: Path, port: str) -> None:
    """Make ``.beads/dolt-server.port`` the source of truth for the port and drop the deprecated
    ``dolt_server_port`` key from metadata.json (bd warns it can leak data across projects). Edits
    metadata in place so identity fields like ``project_id`` survive."""
    beads_dir = Path(beads_dir)
    meta_file = beads_dir / "metadata.json"
    if meta_file.is_file():
        data = json.loads(meta_file.read_text())
        if data.pop("dolt_server_port", None) is not None:
            meta_file.write_text(json.dumps(data, indent=2) + "\n")
    (beads_dir / "dolt-server.port").write_text(f"{port}\n")


def _is_server_db_exists_error(exc: subprocess.CalledProcessError) -> bool:
    """True when ``bd init`` failed only because the server database already exists."""
    return "database exists" in (exc.stderr or "").lower()


def attach_existing_server_beads(
    control: Path,
    project: str,
    *,
    host: str,
    port: str,
    user: str,
    database: str,
    run: Runner = _default_run,
) -> str:
    """Attach to an already-existing server beads DB via metadata hydration.

    When ``bd init`` reports the server database already exists, a create is wrong: write the
    server-mode ``.beads`` scaffolding (metadata.json + port) and verify the
    connection instead. Any partial ``.beads`` left by the failed ``bd init`` is overwritten — the
    data lives on the server, so nothing local is at risk.

    Verification is ``bd dolt test`` (the server-mode check), not ``bd dolt pull``: in server mode no
    Dolt remote is configured, so a pull is a no-op, whereas ``test`` actually confirms the attach
    reaches the server and fails cleanly when it can't.
    """
    beads = Path(control) / ".beads"
    beads.mkdir(parents=True, exist_ok=True)
    write_server_beads_metadata(beads, host=host, port=port, user=user, database=database)
    run(["bd", "dolt", "test"], cwd=control, env=_beads_env(control), check=True)
    return f"attached to existing server beads DB {host}:{port}/{database} (hydrated metadata)"


def init_beads(
    control: Path,
    project: str,
    dotbrain_root: Path,
    *,
    run_beads: bool = True,
    remote: str = "",
    server_host: str = "",
    server_port: str = "3307",
    server_user: str = "beads",
    database: str = "",
    run: Runner = _default_run,
) -> str | None:
    """Run ``bd init --stealth`` in the Brainspace. Returns a log line or None.

    bd runs in stealth mode so it never commits into the dotbrain monorepo; dotbrain owns all git
    writes here. ``_hide_root_beads`` / ``_restore_root_beads`` still guard bd's repo-root ``.beads``
    workspace hijack, which is workspace resolution, not a commit.

    In server mode, an existing server database makes ``bd init`` fail with a create error; that
    case falls back to attaching via metadata hydration rather than a destructive
    re-init. Any other ``bd init`` failure surfaces as a clean ``RuntimeError`` carrying bd's stderr.
    """
    control = Path(control)
    dotbrain_root = Path(dotbrain_root)
    if not run_beads or (control / ".beads").is_dir():
        return None
    if remote and server_host:
        raise ValueError("--beads-remote and --beads-server-host are mutually exclusive")

    hidden = _hide_root_beads(control, dotbrain_root)
    try:
        try:
            run(_bd_init_args(project, remote, server_host, server_port,
                              server_user, database),
                cwd=control, env=_beads_env(control), check=True)
        except subprocess.CalledProcessError as exc:
            if server_host and _is_server_db_exists_error(exc):
                return attach_existing_server_beads(
                    control, project,
                    host=server_host, port=server_port,
                    user=server_user, database=database or project,
                    run=run,
                )
            stderr = (exc.stderr or "").strip()
            raise RuntimeError(f"bd init failed: {stderr}" if stderr else "bd init failed") from exc
    finally:
        _restore_root_beads(hidden, dotbrain_root)

    if server_host:
        _configure_dolt_server(control, server_host, server_port, server_user,
                               database or project, run)
        normalize_server_beads_metadata(control / ".beads", server_port)
    return None


def _bd_init_args(
    project: str,
    remote: str,
    server_host: str,
    server_port: str,
    server_user: str,
    database: str,
    *,
    reinit_local: bool = False,
    destroy_token: str | None = None,
) -> list[str]:
    # --stealth: bd must never git-commit into the dotbrain monorepo. It suppresses the
    # "bd init: initialize beads issue tracking" commit and sets no-git-ops for bd's other git ops.
    args = ["bd", "init", "--stealth", "--prefix", project,
            "--skip-agents", "--skip-hooks", "--non-interactive"]
    if server_host:
        args += [
            "--server", "--external",
            "--server-host", server_host,
            "--server-port", server_port,
            "--server-user", server_user,
            "--database", database or project,
        ]
        if reinit_local:
            args += ["--reinit-local"]
        if destroy_token:
            args += ["--destroy-token", destroy_token]
    args += ["--remote", remote]
    return args


def _beads_env(control: Path) -> dict:
    return {**os.environ, "BEADS_DIR": str(Path(control) / ".beads"), "BD_NON_INTERACTIVE": "1"}


def _hide_root_beads(control: Path, dotbrain_root: Path) -> Path | None:
    """bd init runs in the Brainspace but git sees dotbrain; hide the root .beads symlink first."""
    root_beads = Path(dotbrain_root) / ".beads"
    if control == paths.brainspace(dotbrain_root, "dotbrain"):
        return None
    if not root_beads.is_symlink():
        return None
    hidden = Path(dotbrain_root) / f".beads.wire-project.{os.getpid()}"
    root_beads.rename(hidden)
    return hidden


def _restore_root_beads(hidden: Path | None, dotbrain_root: Path) -> None:
    """Always put project #0's repo-root .beads symlink back.

    bd init runs with the git top-level still resolving to dotbrain, so it may recreate a .beads at
    the repo root pointing at the *wired* project. Remove whatever it left and restore the original
    target unconditionally — a stale ``not root_beads.exists()`` guard here is what let the wired
    project hijack project #0's tracker."""
    if hidden is None or not hidden.exists():
        return
    root_beads = Path(dotbrain_root) / ".beads"
    if root_beads.is_symlink() or root_beads.is_file():
        root_beads.unlink()
    elif root_beads.is_dir():
        shutil.rmtree(root_beads)
    hidden.rename(root_beads)


def _configure_dolt_server(
    control: Path, host: str, port: str, user: str, database: str, run: Runner
) -> None:
    env = _beads_env(control)
    for key, value in (("host", host), ("port", port), ("user", user), ("database", database)):
        run(["bd", "dolt", "set", key, value], cwd=control, env=env, check=True)


# --------------------------------------------------------------------------- load / hydrate


def ensure_server_beads_metadata(
    repo: Path,
    name: str,
    *,
    server_host: str = "",
    server_port: str = "3307",
    server_user: str = "beads",
    database: str = "",
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> str | None:
    """Hydrate server-mode ``metadata.json`` from config.yaml defaults, if needed.

    Creates the ``.beads`` directory when absent: it is never git-tracked, so on a
    fresh clone hydration is what brings it into existence.
    """
    metadata = repo / ".beads" / "metadata.json"
    port_file = repo / ".beads" / "dolt-server.port"
    if metadata.is_file() or not server_host:
        return None

    database = database or name
    port = server_port or "3307"
    user = server_user or "beads"

    (repo / ".beads").mkdir(mode=0o700, parents=True, exist_ok=True)
    write_server_beads_metadata(
        repo / ".beads", host=server_host, port=port, user=user, database=database
    )
    try:
        run(["bd", "-C", str(repo), "dolt", "test"], check=True)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        metadata.unlink(missing_ok=True)
        port_file.unlink(missing_ok=True)
        raise
    return f"hydrated server beads metadata for {name} at {server_host}:{port}/{database}"


def ensure_embedded_beads(
    control: Path,
    dotbrain_root: Path,
    *,
    remote: str = "",
    run: Runner = _default_run,
) -> tuple[str | None, str | None]:
    """Hydrate a declared-embedded Brainspace via ``bd init --stealth``. Returns (log, warning).

    With a declared remote the tracker is cloned from it; without one only an empty tracker can
    be created, since embedded data was never recoverable from git.
    """
    if (control / ".beads").is_dir():
        return None, None
    init_beads(control, control.name, dotbrain_root, remote=remote, run=run)
    if remote:
        return f"hydrated embedded beads for {control.name} from {remote}", None
    return (
        f"initialized empty embedded beads for {control.name}",
        f"{control.name}: declared embedded with no remote; tracker starts empty",
    )


def _preview_load(control: Path, beads_cfg, cfg) -> list[str]:
    """Pure dry-run preview of what :func:`pull_beads_for_all` would do for one Brainspace.

    Mirrors the live branch selection (embedded vs server, already-hydrated skip) without touching
    the filesystem or invoking ``bd``, then always notes the pull. Keeping this free of mutators is
    what makes ``--dry-run`` provably side-effect-free (unwire-dry-run lesson, 9cfc44f).
    """
    name = control.name
    lines: list[str] = []
    if beads_cfg.mode == "embedded":
        if not (control / ".beads").is_dir():
            if beads_cfg.remote:
                lines.append(f"would hydrate embedded beads for {name} from {beads_cfg.remote}")
            else:
                lines.append(f"would initialize empty embedded beads for {name}")
    elif not (control / ".beads" / "metadata.json").is_file() and cfg.beads_server.host:
        database = beads_cfg.database or name
        port = cfg.beads_server.port or "3307"
        lines.append(
            f"would hydrate server beads metadata for {name} "
            f"at {cfg.beads_server.host}:{port}/{database}"
        )
    lines.append(f"would pull beads for {name}")
    return lines


def pull_beads_for_all(
    dotbrain_root: Path,
    run: Runner = _default_run,
    bd_timeout: int = 20,
    *,
    projects: Sequence[str] | None = None,
    dry_run: bool = False,
) -> BootstrapResult:
    """Hydrate and pull beads state for Brainspaces declared to use beads.

    Drives off the resolved config.yaml config, not an existing ``.beads`` directory: control
    roots' ``.beads`` are never git-tracked, so on a fresh clone hydration creates them. Targets
    each Brainspace directly, so repo-less projects are hydrated too.

    ``projects`` restricts the run to the named Brainspaces (``None`` = all); a requested name
    with no Brainspace yields a warning. ``dry_run`` only previews via :func:`_preview_load`,
    reaching no filesystem or ``bd`` write by construction.
    """
    dotbrain_root = Path(dotbrain_root).resolve()
    result = BootstrapResult()
    cfg = config.load_config(dotbrain_root)

    if not shutil.which("bd"):
        result.warnings.append("bd is not installed; skipping beads pulls")
        return result

    controls = paths.brainspaces(dotbrain_root)
    if projects is not None:
        by_name = {c.name: c for c in controls}
        controls = []
        for name in projects:
            control = by_name.get(name)
            if control is None:
                result.warnings.append(f"no Brainspace: {paths.data_dir(dotbrain_root).name}/{name}")
                continue
            controls.append(control)

    for control in controls:
        beads_cfg = config.load_project_config(dotbrain_root, control.name)
        if beads_cfg.mode == "none":
            continue

        if dry_run:
            result.logs += _preview_load(control, beads_cfg, cfg)
            continue

        try:
            if beads_cfg.mode == "embedded":
                log, warning = ensure_embedded_beads(
                    control, dotbrain_root, remote=beads_cfg.remote, run=run
                )
                if warning:
                    result.warnings.append(warning)
            else:
                log = ensure_server_beads_metadata(
                    control,
                    control.name,
                    server_host=cfg.beads_server.host,
                    server_port=cfg.beads_server.port,
                    server_user=cfg.beads_server.user,
                    database=beads_cfg.database,
                    run=run,
                )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                OSError, RuntimeError) as exc:
            result.warnings.append(f"failed to hydrate beads metadata for {control}: {exc}")
        else:
            if log:
                result.logs.append(log)

        try:
            subprocess.run(
                ["bd", "-C", str(control), "dolt", "pull"],
                check=True, capture_output=True, text=True, timeout=bd_timeout,
            )
            result.pulled.append(str(control))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            result.warnings.append(f"bd dolt pull failed for {control}")

    return result


# --------------------------------------------------------------------------- remote admin


def _mysql_argv(
    query: str, *, server_host: str, server_port: str, server_user: str, ssh_host: str
) -> tuple[list[str], str]:
    """Build the argv to run ``query`` against the sql-server with the mysql client, optionally
    over an ssh hop. Returns (argv, human-readable target). A bare ``dolt sql`` against the data
    dir fails when a server holds it (client mode dials 127.0.0.1), so we use the mysql client."""
    if not server_host:
        raise ValueError("a Dolt sql-server host is required")
    mysql_argv = [
        "mysql", "--host", server_host, "--port", str(server_port),
        "-u", server_user, "-e", query,
    ]
    if ssh_host:
        return ["ssh", ssh_host, " ".join(shlex.quote(a) for a in mysql_argv)], \
            f"{ssh_host} -> {server_host}:{server_port}"
    return mysql_argv, f"{server_host}:{server_port}"


def drop_remote_beads_database(
    project: str,
    *,
    database: str = "",
    server_host: str,
    server_port: str = "3307",
    server_user: str = "beads",
    ssh_host: str = "",
    dry_run: bool = False,
    run: Runner = _default_run,
) -> str:
    """Drop a project's beads database on the shared Dolt sql-server (server backend only).

    ``ssh_host`` is the optional hop that can reach the server; empty means connect directly.
    """
    db = database or project
    if not _DB_NAME_RE.fullmatch(db):
        raise ValueError(f"unsafe beads database name: {db!r}")
    if db in _PROTECTED_DATABASES:
        raise ValueError(f"refusing to drop protected beads database: {db}")

    argv, via = _mysql_argv(
        f"DROP DATABASE IF EXISTS `{db}`;",
        server_host=server_host, server_port=server_port, server_user=server_user, ssh_host=ssh_host,
    )
    if dry_run:
        return f"would drop remote beads database {db} via {via}"
    run(argv, check=True)
    return f"dropped remote beads database: {db}"


def list_remote_beads_databases(
    *,
    server_host: str,
    server_port: str = "3307",
    server_user: str = "beads",
    ssh_host: str = "",
    run: Runner = _default_run,
) -> list[str]:
    """Return the database names on the shared Dolt sql-server (the `SHOW DATABASES` rows)."""
    argv, _ = _mysql_argv(
        "SHOW DATABASES;",
        server_host=server_host, server_port=server_port, server_user=server_user, ssh_host=ssh_host,
    )
    out = run(argv, check=True)
    lines = (out.stdout or "").splitlines()
    # mysql prints a "Database" header row; drop it.
    return [l.strip() for l in lines[1:] if l.strip()]
