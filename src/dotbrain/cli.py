"""dotbrain CLI entrypoint."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer

from dotbrain import doctor as doctor_mod
from dotbrain import adopter_repos, beads as beads_mod, bootstrap as bootstrap_mod, config, migrate, paths, resource_loader, skills, workflows, worktrees

app = typer.Typer(
    help="dotbrain control-plane CLI (migration scaffold; scripts still own some behavior).",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
skills_app = typer.Typer(help="Link dotbrain skills into agent runtimes.", no_args_is_help=True)
beads_app = typer.Typer(help="Manage beads tracker state and backend.", no_args_is_help=True)
hook_app = typer.Typer(help="Run dotbrain hook entrypoints.", no_args_is_help=True)
app.add_typer(skills_app, name="skills")
app.add_typer(beads_app, name="beads")
app.add_typer(hook_app, name="hook")


def _delegate_to_script(root: Path, script: str, args: list[str]) -> None:
    path = root / "scripts" / script
    if not path.is_file():
        raise typer.BadParameter(f"{path} not found")
    subprocess.run([str(path), *args], cwd=root, check=True)


def _run_packaged_hook(script: str, args: list[str]) -> None:
    raise_code = resource_loader.run_script(f"scripts/{script}", tuple(args))
    if raise_code:
        raise typer.Exit(raise_code)


@hook_app.command("session-start")
def hook_session_start(args: list[str] = typer.Argument(None)) -> None:
    """Run the dotbrain SessionStart hook."""

    _run_packaged_hook("brain-sessionstart.sh", args or [])


@hook_app.command("claude-worktree-bootstrap")
def hook_claude_worktree_bootstrap(args: list[str] = typer.Argument(None)) -> None:
    """Run the global Claude first-worktree bootstrap hook."""

    _run_packaged_hook("claude-worktree-bootstrap.sh", args or [])


@hook_app.command("codex-worktree-bootstrap")
def hook_codex_worktree_bootstrap(args: list[str] = typer.Argument(None)) -> None:
    """Run the global Codex first-worktree bootstrap hook."""

    _run_packaged_hook("codex-worktree-bootstrap.sh", args or [])


@app.command()
def bootstrap(
    only: Optional[str] = typer.Option(None, "--only", help="claude-hook | codex-hook | skills"),
    skip_claude_hook: bool = typer.Option(False, "--skip-claude-hook"),
    skip_codex_hook: bool = typer.Option(False, "--skip-codex-hook"),
    skip_skills: bool = typer.Option(False, "--skip-skills"),
) -> None:
    """Prepare this machine for dotbrain: global hooks and global skill links."""
    if only and only not in {"claude-hook", "codex-hook", "skills"}:
        raise typer.BadParameter(f"invalid --only: {only}")

    root = paths.resolve_dotbrain_root()

    # Seed data root (config.yaml, skills/skills.yaml) if missing.
    dr_result = bootstrap_mod.ensure_data_root(root)
    if dr_result.created:
        typer.echo(f"[bootstrap] created data root: {root}")
    if dr_result.config_seeded:
        typer.echo(f"[bootstrap] seeded config.yaml into {root}")
    if dr_result.skills_seeded:
        typer.echo(f"[bootstrap] seeded skills/skills.yaml into {root}")

    run_claude = only == "claude-hook" or (only is None and not skip_claude_hook)
    run_codex = only == "codex-hook" or (only is None and not skip_codex_hook)
    run_skills = only == "skills" or (only is None and not skip_skills)

    if run_claude:
        bootstrap_mod.install_global_claude_hook(root)
        typer.echo(f"[bootstrap] installed Claude global bootstrap hook in {Path.home() / '.claude' / 'settings.json'}")
    if run_codex:
        bootstrap_mod.install_global_codex_hook(root)
        typer.echo(f"[bootstrap] installed Codex global bootstrap hook in {Path.home() / '.codex' / 'hooks.json'}")
    if run_skills:
        _render_global_skill_link(root, "all")

def _render_doctor(report: doctor_mod.DoctorReport) -> None:
    ok, warn, err = 0, 0, 0

    def _icon(status: str) -> str:
        return {"ok": "✓", "warn": "⚠", "error": "✖"}.get(status, "?")

    typer.echo("\ndotbrain doctor")
    typer.echo("─" * 60)

    typer.echo("\nMachine readiness")
    typer.echo("─" * 40)
    for f in report.machine:
        if f.status == "ok":
            ok += 1
        elif f.status == "warn":
            warn += 1
        else:
            err += 1
        typer.echo(f"  {_icon(f.status)} {f.message}")
        if f.suggestion:
            typer.echo(f"    → {f.suggestion}")

    if report.projects:
        typer.echo(f"\nProjects ({len(report.projects)})")
        typer.echo("─" * 40)
        for name, findings in report.projects.items():
            for f in findings:
                if f.status == "ok":
                    ok += 1
                elif f.status == "warn":
                    warn += 1
                else:
                    err += 1
                typer.echo(f"  {_icon(f.status)} [{name}] {f.message}")
                if f.suggestion:
                    typer.echo(f"    → {f.suggestion}")

    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"  {ok} ok  {warn} warnings  {err} errors")

    if err > 0:
        typer.echo("\nNext: fix errors then re-run 'dotbrain doctor'")
        raise typer.Exit(1)
    elif warn > 0:
        typer.echo("\nNext: 'dotbrain wire --all' (wire projects)")
        typer.echo("      'dotbrain bootstrap' (install hooks/links)")
        typer.echo("      'dotbrain beads load --all' (hydrate beads)")
    else:
        typer.echo("\nMachine is healthy. Run 'bd ready' for available work.")


@app.command()
def doctor() -> None:
    """Read-only health check: machine readiness, project wiring, beads state drift."""
    root = paths.resolve_dotbrain_root()
    report = doctor_mod.run_doctor(root)
    _render_doctor(report)


@app.command()
def wire(
    all: bool = typer.Option(False, "--all", help="Wire every adopter repo to its control root (brain seeding, symlinks, hooks)."),  # noqa: A002
    repo: Optional[str] = typer.Option(None, "--repo", help="Repo to wire. Defaults to the current git repo."),
    name: Optional[str] = typer.Option(None, "--name", help="Project/control-root name. Defaults to repo dir name."),
    dotbrain: Optional[str] = typer.Option(None, "--dotbrain", help="dotbrain checkout. Defaults to $DOTBRAIN_ROOT/inferred."),
    skip_beads: bool = typer.Option(False, "--skip-beads", help="Do not initialize .beads when missing."),
    install_global_hook: bool = typer.Option(False, "--install-global-hook", help="Also install the global Claude SessionStart hook. Prefer `dotbrain bootstrap` for machine setup."),
    skip_global_hook: bool = typer.Option(False, "--skip-global-hook", help="Compatibility no-op; global hooks are no longer installed by default.", hidden=True),
    remote: str = typer.Option("", "--beads-remote", help="Initialize beads from this Dolt remote."),
    server_host: Optional[str] = typer.Option(None, "--beads-server-host", help="Init beads against an external Dolt sql-server. Defaults to beads.server.host in config.yaml."),
    server_port: Optional[str] = typer.Option(None, "--beads-server-port", help="Dolt sql-server port. Defaults to beads.server.port in config.yaml."),
    server_user: Optional[str] = typer.Option(None, "--beads-server-user", help="Dolt sql-server user. Defaults to beads.server.user in config.yaml."),
    database: str = typer.Option("", "--beads-database", help="Dolt database name. Defaults to project name."),
    no_repo: bool = typer.Option(False, "--no-repo", help="Create a brain-only control root (no code repo). Requires --name."),
    repo_base: Optional[Path] = typer.Option(None, "--repo-base", help="Base directory for adopter repos (default: ~/repos/projects)."),
) -> None:
    """Create or repair a project control root and wire an adopter repo.

    Without --all: wire one project. With --all: reconcile every control root.
    """
    root = Path(dotbrain) if dotbrain else paths.resolve_dotbrain_root()
    if all:
        if repo or name or no_repo or remote:
            raise typer.BadParameter("--all is mutually exclusive with --repo, --name, --no-repo, and --beads-remote")
        result = workflows.wire_all_projects(root, repo_base=repo_base)
        for line in result.logs:
            typer.echo(f"[wire] {line}")
        for w in result.warnings:
            typer.echo(f"[wire] warning: {w}", err=True)
        return
    cfg = config.load_config(root)
    server_host = server_host if server_host is not None else cfg.beads_server.host
    server_port = server_port if server_port is not None else cfg.beads_server.port
    server_user = server_user if server_user is not None else cfg.beads_server.user
    try:
        result = workflows.wire_project(
            dotbrain_root=root,
            repo=Path(repo) if repo else None,
            project=name,
            no_repo=no_repo,
            run_beads=not skip_beads,
            install_global_hook=install_global_hook and not skip_global_hook,
            remote=remote,
            server_host=server_host,
            server_port=server_port,
            server_user=server_user,
            database=database,
        )
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    for line in result.logs:
        typer.echo(f"[wire] {line}")
    for warning in result.warnings:
        typer.echo(f"[wire] warning: {warning}", err=True)
    if not install_global_hook:
        typer.echo("[wire] global hooks are machine reconciliation; run `dotbrain bootstrap --only claude-hook` if needed")


@app.command()
def refresh(
    all: bool = typer.Option(False, "--all", help="Refresh every project workspace."),  # noqa: A002
    name: Optional[str] = typer.Option(None, "--name", help="Refresh one project by control-root name."),
    repo_base: Optional[Path] = typer.Option(None, "--repo-base", help="Base directory for repo discovery."),
) -> None:
    """Refresh Brain/workspace files, repo links, beads state, and project skills."""
    if all and name:
        raise typer.BadParameter("--all is mutually exclusive with --name")
    if not all and not name:
        raise typer.BadParameter("use --all or --name")

    try:
        root = paths.resolve_dotbrain_root()
        if all:
            result = workflows.refresh_projects(root, repo_base=repo_base)
        else:
            assert name is not None
            result = workflows.refresh_project(root, name, repo_base=repo_base)
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    for line in result.logs:
        typer.echo(f"[refresh] {line}")
    for warning in result.warnings:
        typer.echo(f"[refresh] warning: {warning}", err=True)


@app.command()
def unwire(
    all: bool = typer.Option(False, "--all", help="Unwire every project control root (keep only; see per-project --archive/--delete for destructive offboard)."),  # noqa: A002
    repo: Optional[Path] = typer.Option(None, "--repo", help="Adopter repo path; defaults to cwd"),
    name: Optional[str] = typer.Option(None, "--name", help="Project/control-root name"),
    no_repo: bool = typer.Option(False, "--no-repo", help="Only offboard the named control root; do not edit an adopter repo."),
    archive: bool = typer.Option(False, "--archive", help="Move control root to projects/.archive/"),
    delete: bool = typer.Option(False, "--delete", help="Remove the control root (destructive)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview the offboard without performing it."),
) -> None:
    """Disconnect an adopter repo from its control root.

    Offboards the control root only (keep/archive/delete). To drop a server-backend project's
    remote beads database, use `dotbrain beads drop-db` separately.
    """
    if all:
        if repo or name or no_repo:
            raise typer.BadParameter("--all is mutually exclusive with --repo, --name, and --no-repo")
        if archive or delete:
            raise typer.BadParameter("--all does not support --archive or --delete; use per-project unwire for destructive offboard")
        results = workflows.unwire_all_projects(
            dotbrain_root=paths.resolve_dotbrain_root(),
            dry_run=dry_run,
        )
        for result in results:
            for line in result.logs:
                typer.echo(f"[{result.project}] {line}")
            for w in result.warnings:
                typer.echo(f"[{result.project}] warning: {w}", err=True)
        return
    if archive and delete:
        typer.echo("error: --archive and --delete are mutually exclusive", err=True)
        raise typer.Exit(2)
    if no_repo and repo is not None:
        raise typer.BadParameter("--no-repo is mutually exclusive with --repo")
    if no_repo and not name:
        raise typer.BadParameter("--no-repo requires --name")
    offboard = "archive" if archive else "delete" if delete else "keep"
    result = workflows.unwire_project(
        dotbrain_root=paths.resolve_dotbrain_root(),
        repo=repo,
        project=name,
        no_repo=no_repo,
        offboard=offboard,
        dry_run=dry_run,
    )
    for line in result.logs:
        typer.echo(line)
    for w in result.warnings:
        typer.echo(f"warning: {w}", err=True)


def _resolve_beads_server(
    server_host: Optional[str],
    server_port: Optional[str],
    server_user: Optional[str],
    ssh_host: Optional[str],
) -> tuple[str, str, str, str]:
    """Resolve sql-server connection from flags, falling back to config.yaml beads.server."""
    cfg = config.load_config(paths.resolve_dotbrain_root())
    host = server_host if server_host is not None else cfg.beads_server.host
    port = server_port if server_port is not None else cfg.beads_server.port
    user = server_user if server_user is not None else cfg.beads_server.user
    ssh = ssh_host if ssh_host is not None else cfg.beads_server.ssh_host
    if not host:
        raise typer.BadParameter(
            "no Dolt sql-server configured; set beads.server.host in config.yaml "
            "or pass --beads-server-host (embedded-backend projects have no remote database)"
        )
    return host, port, user, ssh


@app.command("drop-beads-db", hidden=True)
@beads_app.command("drop-db")
def drop_beads_db(
    name: str = typer.Argument(..., help="Beads database name to drop (usually the project name)."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the destructive drop."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview the drop without running it."),
    ssh_host: Optional[str] = typer.Option(None, "--beads-ssh-host", help="SSH hop that can reach the sql-server; empty connects directly. Defaults to beads.server.ssh_host."),
    server_host: Optional[str] = typer.Option(None, "--beads-server-host", help="Dolt sql-server host. Defaults to beads.server.host."),
    server_port: Optional[str] = typer.Option(None, "--beads-server-port", help="Dolt sql-server port. Defaults to beads.server.port."),
    server_user: Optional[str] = typer.Option(None, "--beads-server-user", help="Dolt sql-server user. Defaults to beads.server.user."),
) -> None:
    """Drop a project's remote beads database on the shared Dolt sql-server."""
    if not (yes or dry_run):
        raise typer.BadParameter("beads drop-db requires --yes (or --dry-run)")
    host, port, user, ssh = _resolve_beads_server(
        server_host, server_port, server_user, ssh_host
    )
    try:
        log = beads_mod.drop_remote_beads_database(
            name, server_host=host, server_port=port, server_user=user, ssh_host=ssh, dry_run=dry_run
        )
    except ValueError as exc:  # unsafe/protected database name
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(log)


@app.command("list-beads-db", hidden=True)
@beads_app.command("list-db")
def list_beads_db(
    ssh_host: Optional[str] = typer.Option(None, "--beads-ssh-host", help="SSH hop that can reach the sql-server; empty connects directly. Defaults to beads.server.ssh_host."),
    server_host: Optional[str] = typer.Option(None, "--beads-server-host", help="Dolt sql-server host. Defaults to beads.server.host."),
    server_port: Optional[str] = typer.Option(None, "--beads-server-port", help="Dolt sql-server port. Defaults to beads.server.port."),
    server_user: Optional[str] = typer.Option(None, "--beads-server-user", help="Dolt sql-server user. Defaults to beads.server.user."),
) -> None:
    """List the databases on the shared Dolt sql-server."""
    host, port, user, ssh = _resolve_beads_server(
        server_host, server_port, server_user, ssh_host
    )
    for db in beads_mod.list_remote_beads_databases(
        server_host=host, server_port=port, server_user=user, ssh_host=ssh
    ):
        typer.echo(db)


@app.command("migrate-beads", hidden=True)
@beads_app.command("migrate")
def migrate_beads(
    repo: Optional[str] = typer.Option(None, "--repo", help="Wired repo path; project name is its dir name."),
    name: Optional[str] = typer.Option(None, "--name", help="Project/control-root name to migrate."),
    all_projects: bool = typer.Option(False, "--all", help="Migrate every embedded control root."),
    dotbrain: Optional[str] = typer.Option(None, "--dotbrain", help="dotbrain checkout. Defaults to $DOTBRAIN_ROOT/inferred."),
    server_host: Optional[str] = typer.Option(None, "--beads-server-host", help="Target Dolt sql-server host. Defaults to beads.server.host in config.yaml."),
    server_port: Optional[str] = typer.Option(None, "--beads-server-port", help="Dolt sql-server port. Defaults to beads.server.port in config.yaml."),
    server_user: Optional[str] = typer.Option(None, "--beads-server-user", help="Dolt sql-server user. Defaults to beads.server.user in config.yaml."),
    database: str = typer.Option("", "--beads-database", help="Dolt database name (single-project only). Defaults to project name."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the planned bd sequence without running it."),
) -> None:
    """Migrate a local-only (embedded Dolt) beads tracker onto the remote sql-server, history intact."""
    root = Path(dotbrain) if dotbrain else paths.resolve_dotbrain_root()
    cfg = config.load_config(root)
    host = server_host if server_host is not None else cfg.beads_server.host
    port = server_port if server_port is not None else cfg.beads_server.port
    user = server_user if server_user is not None else cfg.beads_server.user
    if not host:
        raise typer.BadParameter("no --beads-server-host given and none in config.yaml")
    if all_projects and (repo or name):
        raise typer.BadParameter("--all is mutually exclusive with --repo/--name")

    if all_projects:
        results = migrate.migrate_all(
            dotbrain_root=root,
            server_host=host,
            server_port=port,
            server_user=user,
            dry_run=dry_run,
        )
    else:
        project = name or adopter_repos.repo_root(Path(repo) if repo else None).name
        results = [
            migrate.safe_migrate_project(
                dotbrain_root=root,
                project=project,
                server_host=host,
                server_port=port,
                server_user=user,
                database=database,
                dry_run=dry_run,
            )
        ]

    for r in results:
        for line in r.logs:
            typer.echo(f"[beads migrate] {line}")
        if dry_run:
            typer.echo(f"[beads migrate] {r.project}: planned bd sequence:")
            for argv in r.planned_commands:
                typer.echo(f"  {' '.join(argv)}")
        for w in r.warnings:
            typer.echo(f"[beads migrate] warning: {w}", err=True)

    failed = [
        r for r in results
        if r.status in {"aborted-count-mismatch", "migrated-unverified", "failed"}
    ]
    if failed and not dry_run:
        raise typer.Exit(1)


@beads_app.command("load")
def beads_load(
    all: bool = typer.Option(False, "--all", help="Load tracker state for every control root."),  # noqa: A002
    repo: Optional[str] = typer.Option(None, "--repo", help="Repo whose control root to load. Defaults to the current git repo."),
    name: Optional[str] = typer.Option(None, "--name", help="Project/control-root name to load."),
    dotbrain: Optional[str] = typer.Option(None, "--dotbrain", help="dotbrain checkout. Defaults to $DOTBRAIN_ROOT/inferred."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be hydrated/pulled without mutating anything."),
) -> None:
    """Hydrate local beads state from tracked declarations: attach server trackers, init embedded
    ones, then pull. Pull-only reconcile: never pushes, never touches symlinks or hooks.

    Without --all: load one project (by --name, or the --repo/cwd repo). With --all: every control
    root declared to use beads.
    """
    root = Path(dotbrain) if dotbrain else paths.resolve_dotbrain_root()
    if all:
        if repo or name:
            raise typer.BadParameter("--all is mutually exclusive with --repo and --name")
        projects = None
    else:
        if repo and name:
            raise typer.BadParameter("--repo and --name are mutually exclusive")
        try:
            project = name or adopter_repos.repo_root(Path(repo) if repo else None).name
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        projects = [project]

    result = beads_mod.pull_beads_for_all(root, projects=projects, dry_run=dry_run)
    for line in result.logs:
        typer.echo(f"[beads load] {line}")
    for warning in result.warnings:
        typer.echo(f"[beads load] warning: {warning}", err=True)


worktrees_app = typer.Typer(help="Worktree utilities.", no_args_is_help=True)
app.add_typer(worktrees_app, name="worktrees", hidden=True)


@worktrees_app.command("wire")
def worktrees_wire(
    path: Optional[str] = typer.Argument(None, help="Worktree path (defaults to cwd)"),
) -> None:
    """Reconcile control links inside a git worktree."""
    target = Path(path) if path else Path.cwd()
    result = adopter_repos.reconcile_worktree(target)
    for name in result.created:
        typer.echo(f"linked {name}")
    for name in result.repaired:
        typer.echo(f"repaired {name}")


@app.command()
def codex(
    worktree: str = typer.Option(
        ..., "--worktree", "-w", help="Branch/worktree name, e.g. feature-auth"
    ),
    repo: Optional[Path] = typer.Option(
        None, "--repo", "-C", help="Repo path; defaults to the current git repo"
    ),
    base: str = typer.Option("main", "--base", help="Base ref for a new worktree"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="Initial Codex prompt"),
    codex_arg: list[str] = typer.Option(
        [], "--codex-arg", help="Extra argument passed to Codex; repeatable"
    ),
    print_only: bool = typer.Option(
        False, "--print", help="Print commands instead of running them"
    ),
) -> None:
    """Create or reuse a dotbrain-wired git worktree and start Codex there."""

    try:
        root = worktrees.repo_root(repo or Path.cwd())
        plan = worktrees.codex_worktree_plan(
            root,
            worktree,
            base=base,
            prompt=prompt,
            codex_args=codex_arg,
        )
    except (subprocess.CalledProcessError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    if print_only:
        typer.echo(worktrees.shell_join(plan.create_command))
        typer.echo(worktrees.shell_join(plan.codex_command))
        return

    typer.echo(f"worktree: {plan.worktree}")
    worktrees.create_codex_worktree(plan)
    adopter_repos.reconcile_worktree(plan.worktree)
    worktrees.launch_codex(plan)


_AGENT_WORKSPACES = {
    "all": (".claude", ".codex"),
    "claude-code": (".claude",),
    "codex": (".codex",),
}


@skills_app.command("list", hidden=True)
def skills_list() -> None:
    """List all skills in the skills tree."""
    root = paths.resolve_dotbrain_root()
    for skill in skills.discover_skills(root / "skills"):
        typer.echo(skill)


@skills_app.command("link")
def skills_link(
    target: str = typer.Option("all", "--target", help="claude-code | codex | all"),
    scope: str = typer.Option("all", "--scope", help="global | project | all"),
    project: Optional[str] = typer.Option(
        None, "--project", help="limit project scope to one control root by name"
    ),
) -> None:
    """Link skills into agent runtimes.

    Both scopes are curated include-lists. Project links the brain-coupled
    required core plus each project's ``project.yaml`` ``skills:`` extras into its
    agent workspaces. Global links the required core plus optional operator
    extras into each runtime's global skills dir.
    """
    if target not in {"claude-code", "codex", "all"}:
        raise typer.BadParameter(f"invalid --target: {target}")
    if scope not in {"global", "project", "all"}:
        raise typer.BadParameter(f"invalid --scope: {scope}")

    root = paths.resolve_dotbrain_root()
    if scope in {"project", "all"}:
        _link_projects_native(root, target, project)
    if scope in {"global", "all"}:
        if project:
            typer.echo("skill-link: warning: --project is ignored for global scope", err=True)
        _render_global_skill_link(root, target)


def _link_projects_native(root: Path, target: str, project: Optional[str]) -> None:
    workspaces = _AGENT_WORKSPACES[target]
    if project:
        control = paths.control_root(root, project)
        if not control.is_dir():
            raise typer.BadParameter(f"no control root: projects/{project}")
        controls = [control]
    else:
        controls = paths.control_roots(root)
    for control in controls:
        config.migrate_legacy_skill_manifest(root, control.name)
        extras = config.load_project_skills(root, control.name)
        skill_paths = skills.project_link_set(extras)
        result = skills.link_project(root, control, workspaces, skill_paths)
        for warning in result.warnings:
            typer.echo(f"skill-link: warning: {warning} (project {control.name})", err=True)
        for pruned in result.pruned:
            typer.echo(f"  pruned stale {control.name}/{pruned}")
        typer.echo(f"project: linked {len(skill_paths)} skill(s) into {control.name}")


def _render_global_skill_link(root: Path, target: str) -> None:
    result = bootstrap_mod.link_global_skills(root, target)
    for warning in result.warnings:
        typer.echo(f"skill-link: warning: {warning}", err=True)
    for line in result.logs:
        typer.echo(line if line.startswith("global:") else f"  {line}")
