"""dotbrain CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from dotbrain import doctor as doctor_mod
from dotbrain import adopter_repos, beads as beads_mod, bootstrap as bootstrap_mod, config, brainspaces, hooks, migrate, paths, resource_loader, skills, subagents, workflows

app = typer.Typer(
    help="dotbrain CLI for wiring project Brainspaces and skills into coding agents.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
skills_app = typer.Typer(help="Link dotbrain skills into agent runtimes.", no_args_is_help=True)
agents_app = typer.Typer(help="Link dotbrain vendor-native subagents into agent runtimes.", no_args_is_help=True)
beads_app = typer.Typer(help="Manage beads tracker state and backend.", no_args_is_help=True)
hook_app = typer.Typer(help="Run dotbrain hook entrypoints.", no_args_is_help=True)
app.add_typer(skills_app, name="skills")
app.add_typer(agents_app, name="agents")
app.add_typer(beads_app, name="beads")
app.add_typer(hook_app, name="hook")


@hook_app.command("session-start")
def hook_session_start(args: list[str] = typer.Argument(None)) -> None:
    """Emit a wired repo's Brain context. Fail-open: silent and exit 0 when there is none."""

    hooks.emit_brain_context()


@app.command()
def bootstrap(
    only: Optional[str] = typer.Option(None, "--only", help="skills"),
    skip_skills: bool = typer.Option(False, "--skip-skills"),
) -> None:
    """Prepare this machine for dotbrain: global skill and subagent links."""
    if only and only != "skills":
        raise typer.BadParameter(f"invalid --only: {only}")

    root = paths.resolve_dotbrain_home()

    # Seed data root (config.yaml, skills/skills.yaml) if missing.
    dr_result = bootstrap_mod.ensure_data_root(root)
    if dr_result.created:
        typer.echo(f"[bootstrap] created data root: {root}")
    if dr_result.config_seeded:
        typer.echo(f"[bootstrap] seeded config.yaml into {root}")
    if dr_result.skills_seeded:
        typer.echo(f"[bootstrap] seeded skills/skills.yaml into {root}")
    if dr_result.agents_seeded:
        typer.echo(f"[bootstrap] seeded agents/agents.yaml into {root}")

    run_skills = only == "skills" or (only is None and not skip_skills)

    if run_skills:
        try:
            _render_global_skill_link(root, "all")
            _render_global_agent_link(root, "all")
        except RuntimeError as exc:
            raise typer.BadParameter(str(exc)) from exc


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
        typer.echo("      'dotbrain bootstrap' (link global skills and subagents)")
        typer.echo("      'dotbrain beads load --all' (hydrate beads)")
    else:
        typer.echo("\nMachine is healthy. Run 'bd ready' for available work.")


@app.command()
def doctor() -> None:
    """Read-only health check: machine readiness, project wiring, beads state drift."""
    root = paths.resolve_dotbrain_home()
    report = doctor_mod.run_doctor(root)
    _render_doctor(report)


@app.command()
def wire(
    all: bool = typer.Option(False, "--all", help="Wire every adopter repo to its Brainspace (brain seeding and symlinks)."),  # noqa: A002
    repo: Optional[str] = typer.Option(None, "--repo", help="Repo to wire. Defaults to the current git repo."),
    name: Optional[str] = typer.Option(None, "--name", help="Project/Brainspace name. Defaults to repo dir name."),
    dotbrain: Optional[str] = typer.Option(None, "--dotbrain", help="dotbrain checkout. Defaults to $DOTBRAIN_HOME/inferred."),
    skip_beads: bool = typer.Option(False, "--skip-beads", help="Do not initialize .beads when missing."),
    remote: str = typer.Option("", "--beads-remote", help="Initialize beads from this Dolt remote."),
    server_host: Optional[str] = typer.Option(None, "--beads-server-host", help="Init beads against an external Dolt sql-server. Defaults to beads.server.host in config.yaml."),
    server_port: Optional[str] = typer.Option(None, "--beads-server-port", help="Dolt sql-server port. Defaults to beads.server.port in config.yaml."),
    server_user: Optional[str] = typer.Option(None, "--beads-server-user", help="Dolt sql-server user. Defaults to beads.server.user in config.yaml."),
    database: str = typer.Option("", "--beads-database", help="Dolt database name. Defaults to project name."),
    no_repo: bool = typer.Option(False, "--no-repo", help="Create a brain-only Brainspace (no code repo). Requires --name."),
    repo_base: Optional[Path] = typer.Option(None, "--repo-base", help="Base directory for adopter repos (default: ~/repos/projects)."),
) -> None:
    """Create or repair a project Brainspace and wire an adopter repo.

    Without --all: wire one project. With --all: reconcile every Brainspace.
    """
    root = Path(dotbrain) if dotbrain else paths.resolve_dotbrain_home()
    if all:
        if repo or name or no_repo or remote:
            raise typer.BadParameter("--all is mutually exclusive with --repo, --name, --no-repo, and --beads-remote")
        try:
            result = workflows.wire_all_projects(root, repo_base=repo_base)
        except (ValueError, RuntimeError) as exc:
            raise typer.BadParameter(str(exc)) from exc
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
            dotbrain_home=root,
            repo=Path(repo) if repo else None,
            project=name,
            no_repo=no_repo,
            run_beads=not skip_beads,
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


@app.command()
def refresh(
    all: bool = typer.Option(False, "--all", help="Refresh every project workspace."),  # noqa: A002
    name: Optional[str] = typer.Option(None, "--name", help="Refresh one project by Brainspace name."),
    repo_base: Optional[Path] = typer.Option(None, "--repo-base", help="Base directory for repo discovery."),
) -> None:
    """Refresh Brain/workspace files, repo links, beads state, and project skills."""
    if all and name:
        raise typer.BadParameter("--all is mutually exclusive with --name")
    if not all and not name:
        raise typer.BadParameter("use --all or --name")

    try:
        root = paths.resolve_dotbrain_home()
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
    all: bool = typer.Option(False, "--all", help="Unwire every project Brainspace (keep only; see per-project --archive/--delete for destructive offboard)."),  # noqa: A002
    repo: Optional[Path] = typer.Option(None, "--repo", help="Adopter repo path; defaults to cwd"),
    name: Optional[str] = typer.Option(None, "--name", help="Project/Brainspace name"),
    no_repo: bool = typer.Option(False, "--no-repo", help="Only offboard the named Brainspace; do not edit an adopter repo."),
    archive: bool = typer.Option(False, "--archive", help="Move Brainspace to <data-dir>/.archive/"),
    delete: bool = typer.Option(False, "--delete", help="Remove the Brainspace (destructive)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview the offboard without performing it."),
) -> None:
    """Disconnect an adopter repo from its Brainspace.

    Offboards the Brainspace only (keep/archive/delete). To drop a server-backend project's
    remote beads database, use `dotbrain beads drop-db` separately.
    """
    if all:
        if repo or name or no_repo:
            raise typer.BadParameter("--all is mutually exclusive with --repo, --name, and --no-repo")
        if archive or delete:
            raise typer.BadParameter("--all does not support --archive or --delete; use per-project unwire for destructive offboard")
        results = workflows.unwire_all_projects(
            dotbrain_home=paths.resolve_dotbrain_home(),
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
        dotbrain_home=paths.resolve_dotbrain_home(),
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
    cfg = config.load_config(paths.resolve_dotbrain_home())
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
    name: Optional[str] = typer.Option(None, "--name", help="Project/Brainspace name to migrate."),
    all_projects: bool = typer.Option(False, "--all", help="Migrate every embedded Brainspace."),
    dotbrain: Optional[str] = typer.Option(None, "--dotbrain", help="dotbrain checkout. Defaults to $DOTBRAIN_HOME/inferred."),
    server_host: Optional[str] = typer.Option(None, "--beads-server-host", help="Target Dolt sql-server host. Defaults to beads.server.host in config.yaml."),
    server_port: Optional[str] = typer.Option(None, "--beads-server-port", help="Dolt sql-server port. Defaults to beads.server.port in config.yaml."),
    server_user: Optional[str] = typer.Option(None, "--beads-server-user", help="Dolt sql-server user. Defaults to beads.server.user in config.yaml."),
    database: str = typer.Option("", "--beads-database", help="Dolt database name (single-project only). Defaults to project name."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the planned bd sequence without running it."),
) -> None:
    """Migrate a local-only (embedded Dolt) beads tracker onto the remote sql-server, history intact."""
    root = Path(dotbrain) if dotbrain else paths.resolve_dotbrain_home()
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
            dotbrain_home=root,
            server_host=host,
            server_port=port,
            server_user=user,
            dry_run=dry_run,
        )
    else:
        project = name or adopter_repos.repo_root(Path(repo) if repo else None).name
        results = [
            migrate.safe_migrate_project(
                dotbrain_home=root,
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
    all: bool = typer.Option(False, "--all", help="Load tracker state for every Brainspace."),  # noqa: A002
    repo: Optional[str] = typer.Option(None, "--repo", help="Repo whose Brainspace to load. Defaults to the current git repo."),
    name: Optional[str] = typer.Option(None, "--name", help="Project/Brainspace name to load."),
    dotbrain: Optional[str] = typer.Option(None, "--dotbrain", help="dotbrain checkout. Defaults to $DOTBRAIN_HOME/inferred."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be hydrated/pulled without mutating anything."),
) -> None:
    """Hydrate local beads state from tracked declarations: attach server trackers, init embedded
    ones, then pull. Pull-only reconcile: never pushes, never touches symlinks or hooks.

    Without --all: load one project (by --name, or the --repo/cwd repo). With --all: every brainspace
    root declared to use beads.
    """
    root = Path(dotbrain) if dotbrain else paths.resolve_dotbrain_home()
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


_AGENT_WORKSPACES = {
    "all": (".claude", ".codex"),
    "claude-code": (".claude",),
    "codex": (".codex",),
}


@skills_app.command("list", hidden=True)
def skills_list() -> None:
    """List all skills in the skills tree."""
    root = paths.resolve_dotbrain_home()
    for skill in skills.discover_skills(root / "skills"):
        typer.echo(skill)


@skills_app.command("link")
def skills_link(
    target: str = typer.Option("all", "--target", help="claude-code | codex | all"),
    scope: str = typer.Option("all", "--scope", help="global | project | all"),
    project: Optional[str] = typer.Option(
        None, "--project", help="limit project scope to one Brainspace by name"
    ),
) -> None:
    """Link skills into agent runtimes.

    Both scopes are curated include-lists. Project links each project's
    ``project.yaml`` ``skills:`` selection into its agent workspaces. Global
    links the operator's optional global selection into each runtime's skills
    directory.
    """
    if target not in {"claude-code", "codex", "all"}:
        raise typer.BadParameter(f"invalid --target: {target}")
    if scope not in {"global", "project", "all"}:
        raise typer.BadParameter(f"invalid --scope: {scope}")

    root = paths.resolve_dotbrain_home()
    try:
        if scope in {"project", "all"}:
            _link_projects_native(root, target, project)
        if scope in {"global", "all"}:
            if project:
                typer.echo("skill-link: warning: --project is ignored for global scope", err=True)
            _render_global_skill_link(root, target)
    except RuntimeError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _link_projects_native(root: Path, target: str, project: Optional[str]) -> None:
    workspaces = _AGENT_WORKSPACES[target]
    if project:
        brainspace = paths.brainspace(root, project)
        if not brainspace.is_dir():
            raise typer.BadParameter(f"no Brainspace: {paths.data_dir(root).name}/{project}")
        brainspace_paths = [brainspace]
    else:
        brainspace_paths = paths.brainspaces(root)
    for brainspace in brainspace_paths:
        config.migrate_legacy_skill_manifest(root, brainspace.name)
        extras = config.load_project_skills(root, brainspace.name)
        skill_paths = skills.project_link_set(extras)
        declared_workspaces = brainspaces.active_agent_workspaces(brainspace, root)
        active_workspaces = tuple(ws for ws in workspaces if ws in declared_workspaces)
        repo = adopter_repos.repo_for_brainspace(brainspace, root)
        workspace_dirs, workspace_warnings = workflows.project_workspace_dirs(
            brainspace, repo, active_workspaces
        )
        result = skills.link_project(
            root,
            brainspace,
            tuple(workspace_dirs),
            skill_paths,
            workspace_dirs=workspace_dirs,
        )
        if repo is not None:
            adopter_repos.reconcile_link_excludes(
                repo,
                linked=tuple(entry for entry in result.linked if entry.startswith((".claude/", ".codex/"))),
                pruned=tuple(entry for entry in result.pruned if entry.startswith((".claude/", ".codex/"))),
            )
        for warning in workspace_warnings:
            typer.echo(f"skill-link: warning: {warning} (project {brainspace.name})", err=True)
        for warning in result.warnings:
            typer.echo(f"skill-link: warning: {warning} (project {brainspace.name})", err=True)
        for pruned in result.pruned:
            typer.echo(f"  pruned stale {brainspace.name}/{pruned}")
        typer.echo(f"project: linked {len(result.linked)} skill(s) into {brainspace.name}")


def _render_global_skill_link(root: Path, target: str) -> None:
    result = bootstrap_mod.link_global_skills(root, target)
    for warning in result.warnings:
        typer.echo(f"skill-link: warning: {warning}", err=True)
    for line in result.logs:
        typer.echo(line if line.startswith("global:") else f"  {line}")


@agents_app.command("list", hidden=True)
def agents_list() -> None:
    root = paths.resolve_dotbrain_home()
    names: set[str] = set()
    for subdir, ext in subagents.RUNTIME_SPEC.values():
        runtime_dir = root / "agents" / subdir
        if runtime_dir.is_dir():
            for path in runtime_dir.glob(f"*{ext}"):
                names.add(path.stem)
        try:
            resource_dir = resource_loader.resource(f"agents/{subdir}")
        except FileNotFoundError:
            continue
        if resource_dir.is_dir():
            for entry in resource_dir.iterdir():
                if entry.is_file() and entry.name.endswith(ext):
                    names.add(Path(entry.name).stem)
    for name in sorted(names):
        typer.echo(name)


@agents_app.command("link")
def agents_link(
    target: str = typer.Option("all", "--target", help="claude-code | codex | all"),
    scope: str = typer.Option("all", "--scope", help="global | project | all"),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        help="Limit project linking to a single Brainspace by name.",
    ),
) -> None:
    if target not in {"claude-code", "codex", "all"}:
        raise typer.BadParameter(f"invalid --target: {target}")
    if scope not in {"global", "project", "all"}:
        raise typer.BadParameter(f"invalid --scope: {scope}")

    root = paths.resolve_dotbrain_home()
    if scope in {"project", "all"}:
        brainspaces_to_link = [paths.brainspace(root, project)] if project else paths.brainspaces(root)
        if project and not brainspaces_to_link[0].exists():
            raise typer.BadParameter(f"unknown project: {project}")
        for brainspace in brainspaces_to_link:
            names = subagents.project_link_set(config.load_project_subagents(root, brainspace.name))
            declared_workspaces = brainspaces.active_agent_workspaces(brainspace, root)
            active_workspaces = tuple(ws for ws in _AGENT_WORKSPACES[target] if ws in declared_workspaces)
            repo = adopter_repos.repo_for_brainspace(brainspace, root)
            workspace_dirs, workspace_warnings = workflows.project_workspace_dirs(
                brainspace, repo, active_workspaces
            )
            result = subagents.link_project_subagents(
                root,
                brainspace,
                tuple(workspace_dirs),
                names,
                workspace_dirs=workspace_dirs,
            )
            if repo is not None:
                adopter_repos.reconcile_link_excludes(
                    repo,
                    linked=tuple(entry for entry in result.linked if entry.startswith((".claude/", ".codex/"))),
                    pruned=tuple(entry for entry in result.pruned if entry.startswith((".claude/", ".codex/"))),
                )
            for warning in workspace_warnings:
                typer.echo(f"agent-link: warning: {warning} (project {brainspace.name})", err=True)
            for warning in result.warnings:
                typer.echo(f"agent-link: warning: {warning} (project {brainspace.name})", err=True)
            for pruned in result.pruned:
                typer.echo(f"  pruned stale {brainspace.name}/{pruned}")
            typer.echo(f"project: linked {len(result.linked)} subagent file(s) into {brainspace.name}")

    if scope in {"global", "all"}:
        _render_global_agent_link(root, target)


def _render_global_agent_link(root: Path, target: str) -> None:
    result = bootstrap_mod.link_global_subagents(root, target)
    for warning in result.warnings:
        typer.echo(f"agent-link: warning: {warning}", err=True)
    for line in result.logs:
        typer.echo(line if line.startswith("global:") else f"  {line}")
