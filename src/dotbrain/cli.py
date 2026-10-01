"""dotbrain CLI entrypoint."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
import yaml
from dotbrain.options import HomeOption, RuntimeOption, JsonOption
from dotbrain.results import CommandResult, TargetResult, ResultGroup, render

from dotbrain import __version__
from dotbrain import projects
from dotbrain import doctor as doctor_mod
from dotbrain import adopter_repos, beads as beads_mod, bootstrap as bootstrap_mod, config, brainspaces, hooks, migrate, paths, resource_loader, site as site_mod, skills, subagents, workflows

app = typer.Typer(
    cls=ResultGroup,
    help="dotbrain CLI for wiring project Brainspaces and skills into coding agents.",
    no_args_is_help=True,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
skills_app = typer.Typer(help="Link dotbrain skills into agent runtimes.", no_args_is_help=True)
agents_app = typer.Typer(help="Link dotbrain vendor-native subagents into agent runtimes.", no_args_is_help=True)
beads_app = typer.Typer(help="Manage beads tracker state and backend.", no_args_is_help=True)
hook_app = typer.Typer(help="Run dotbrain hook entrypoints.", no_args_is_help=True)
site_app = typer.Typer(help="Set up and run a Brain's private site.", no_args_is_help=True)
projects_app = typer.Typer(help="Discover registered projects and inspect local settings.", no_args_is_help=True)
app.add_typer(skills_app, name="skills")
app.add_typer(agents_app, name="agents")
app.add_typer(beads_app, name="beads")
app.add_typer(hook_app, name="hook")
app.add_typer(site_app, name="site")
app.add_typer(projects_app, name="projects")


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", is_eager=True, help="Show the dotbrain version."),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@hook_app.command("session-start")
def hook_session_start(args: list[str] = typer.Argument(None)) -> None:
    """Emit a wired repo's Brain context. Fail-open: silent and exit 0 when there is none."""

    hooks.emit_brain_context()


def _project_report(command: str, root: Path, project: str | None, json_output: bool) -> None:
    try:
        records = (projects.list_projects(root) if command == "projects list" else
                   [projects.inspect_project(root, target) for target in
                    projects.select_projects(root, project=project)])
    except (yaml.YAMLError, OSError) as exc:
        render(CommandResult(command, "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    except ValueError as exc:
        render(CommandResult(command, "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    result = CommandResult(command, targets=[
        TargetResult(project=record["project"], checkout=record["checkout"], data=record,
                     status="failure" if "error" in record else "success",
                     errors=[record["error"]] if "error" in record else [])
        for record in records
    ])
    if any(target.errors for target in result.targets):
        result.status = "partial" if any(not target.errors for target in result.targets) else "failure"
    if json_output:
        render(result, json_output=True)
        if result.status != "success":
            raise typer.Exit(1)
        return
    lines = [f"{result.command}: {result.status}"]
    for target in result.targets:
        record = target.data
        lines.append(f"  {target.project}: {target.checkout or 'Brain-only'}")
        if target.errors:
            lines.extend(f"    error: {error}" for error in target.errors)
            continue
        lines.append(f"    runtimes: {', '.join(record['runtimes']) or 'none'}; tracker: {record['beads']['mode']}")
        lines.append("    wiring: " + (", ".join(f"{name} {status}" for name, status in record['wiring'].items()) or "no checkout"))
        if command == "projects show":
            lines.append(f"    Brainspace: {record['brainspace']}")
            lines.extend(f"    {name}: {value or 'disabled'}" for name, value in record['paths'].items())
            lines.append("    settings: " + json.dumps(record['settings'], ensure_ascii=True))
            lines.append("    configured skills: " + (", ".join(record['skills']['configured']) or "none"))
            lines.append("    effective skills: " + (", ".join(record['skills']['effective']) or "none"))
            lines.append("    subagents: " + (", ".join(record['subagents']) or "none"))
    lines.append(f"{len(result.targets)} project(s)")
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    typer.echo("\n".join(lines).encode(encoding, errors="backslashreplace").decode(encoding))
    if result.status != "success":
        raise typer.Exit(1)


@projects_app.command("list")
def projects_list(home: HomeOption = None, json_output: JsonOption = False) -> None:
    """List every registered project using local declarations and wiring."""
    _project_report("projects list", home or paths.resolve_dotbrain_home(), None, json_output)


@projects_app.command("show")
def projects_show(
    project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Inspect the current wired project or a named project's registered checkout."""
    _project_report("projects show", home or paths.resolve_dotbrain_home(), project, json_output)


@app.command()
def bootstrap(
    home: HomeOption = None,
    runtime: RuntimeOption = "all",
    json_output: JsonOption = False,
) -> None:
    """Prepare this machine for dotbrain: global skill and subagent links."""
    report = CommandResult("bootstrap", targets=[TargetResult(scope="global")])
    target = report.targets[0]
    if runtime not in ("claude", "codex", "all"):
        report.status = "failure"
        report.errors.append("--runtime must be claude, codex, or all")
        render(report, json_output=json_output)
        raise typer.Exit(2)
    root = Path(home).expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        dr_result = bootstrap_mod.ensure_data_root(root)
        target.changes.extend(dr_result.logs)
        legacy_runtime = "claude-code" if runtime == "claude" else runtime
        for linker in (bootstrap_mod.link_global_skills, bootstrap_mod.link_global_subagents):
            linked = linker(root, legacy_runtime)
            target.changes.extend(line for line in linked.logs if "linked 0 " not in line)
            target.errors.extend(linked.warnings)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as exc:
        target.errors.append(str(exc))
    if target.errors:
        target.status = "failure"
        report.status = "partial" if target.changes else "failure"
    render(report, json_output=json_output)
    if report.status != "success":
        raise typer.Exit(1)


def _render_doctor(report: doctor_mod.DoctorReport, *, json_output: bool = False) -> None:
    result = doctor_mod.as_result(report)
    render(result, json_output=json_output)
    if result.status != "success":
        raise typer.Exit(1)


@app.command()
def doctor(home: HomeOption = None,
           project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."),
           all_projects: bool = typer.Option(False, "--all", help="Inspect every registered project."),
           json_output: JsonOption = False) -> None:
    """Read-only health check of machine readiness and selected project setup."""
    try:
        root = home.expanduser().resolve() if home else paths.resolve_dotbrain_home()
        report = doctor_mod.run_doctor(root, project=project, all_projects=all_projects)
    except ValueError as exc:
        render(CommandResult("doctor", "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (RuntimeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        render(CommandResult("doctor", "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    _render_doctor(report, json_output=json_output)


@app.command()
def wire(
    repo: Optional[Path] = typer.Option(None, '--repo', help='Checkout to attach; defaults to the current Git checkout.'),
    project: Optional[str] = typer.Option(None, '--project', help='Select a named Brainspace.'),
    no_repo: bool = typer.Option(False, '--no-repo', help='Create a Brain-only project; requires --project.'),
    skip_beads: bool = typer.Option(False, '--skip-beads', help='Create without a tracker.'),
    remote: str = typer.Option('', '--remote', help='Dolt remote for initial tracker creation.'),
    server_host: Optional[str] = typer.Option(None, '--server-host', help='Dolt server host; defaults to config.'),
    server_port: Optional[str] = typer.Option(None, '--server-port', help='Dolt server port; defaults to config.'),
    server_user: Optional[str] = typer.Option(None, '--server-user', help='Dolt server user; defaults to config.'),
    database: str = typer.Option('', '--database', help='Tracker database; defaults to project name.'),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Create a Brainspace or attach a checkout, including a linked worktree."""
    root = home.expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        cfg = config.load_config(root).beads_server
        selected_host = cfg.host if server_host is None else server_host
        if remote and selected_host:
            raise ValueError('--remote and --server-host are mutually exclusive')
        result = workflows.wire_project(dotbrain_home=root, repo=repo, project=project, no_repo=no_repo,
                run_beads=not skip_beads, remote=remote, server_host=selected_host,
                server_port=cfg.port if server_port is None else server_port,
                server_user=cfg.user if server_user is None else server_user, database=database)
    except ValueError as exc:
        render(CommandResult('wire', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (RuntimeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        render(CommandResult('wire', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    _render_lifecycle('wire', [result], json_output)


def _render_lifecycle(command, results, json_output):
    report = CommandResult(command)
    for result in results:
        errors = list(result.errors)
        target = TargetResult(project=result.project, checkout=str(result.repo) if result.repo else None,
                 changes=result.logs, errors=errors,
                 findings=[{'severity': 'warning', 'message': warning} for warning in result.warnings],
                 status='failure' if errors else 'success')
        report.targets.append(target)
    if any(target.status == 'failure' for target in report.targets):
        report.status = 'partial' if any(target.status == 'success' or target.changes for target in report.targets) else 'failure'
    render(report, json_output=json_output)
    if report.status != 'success':
        raise typer.Exit(1)


@app.command()
def refresh(
    project: Optional[str] = typer.Option(None, '--project', help='Select a named Brainspace.'),
    all_projects: bool = typer.Option(False, '--all', help='Refresh all registered projects.'),
    home: HomeOption = None, runtime: RuntimeOption = 'all', json_output: JsonOption = False,
) -> None:
    """Repair setup while preserving project declarations and content."""
    root = home.expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        result = workflows.refresh_projects(root, project=project, all_projects=all_projects, runtime=runtime)
    except ValueError as exc:
        render(CommandResult('refresh', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (RuntimeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        render(CommandResult('refresh', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    report = CommandResult('refresh', targets=result.targets)
    if result.errors:
        report.status = 'partial' if any(target.status == 'success' or target.changes for target in report.targets) else 'failure'
    render(report, json_output=json_output)
    if result.errors:
        raise typer.Exit(1)


@app.command()
def unwire(
    all_projects: bool = typer.Option(False, '--all', help='Detach registered checkouts.'),
    repo: Optional[Path] = typer.Option(None, '--repo', help='Checkout to detach.'),
    project: Optional[str] = typer.Option(None, '--project', help='Select a named Brainspace.'),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Detach checkouts while retaining their Brainspaces and tracker databases."""
    root = home.expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        if all_projects and (repo is not None or project is not None):
            raise ValueError('--all cannot be combined with --project or --repo')
        results = (workflows.unwire_all_projects(root) if all_projects else
                   [workflows.unwire_project(dotbrain_home=root, repo=repo, project=project)])
    except ValueError as exc:
        render(CommandResult('unwire', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (RuntimeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        render(CommandResult('unwire', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    _render_lifecycle('unwire', results, json_output)


def _resolve_beads_server(root, server_host, server_port, server_user, ssh_host=None):
    cfg = config.load_config(root).beads_server
    host = server_host if server_host is not None else cfg.host
    if not host:
        raise ValueError("no Dolt sql-server configured; set beads.server.host or pass --server-host")
    return (host, server_port if server_port is not None else cfg.port,
            server_user if server_user is not None else cfg.user,
            ssh_host if ssh_host is not None else cfg.ssh_host)


def _beads_failure(command, exc, json_output, code=1):
    render(CommandResult(command, "failure", errors=[str(exc)]), json_output=json_output)
    raise typer.Exit(code) from exc


def _finish_beads(result, json_output):
    failed = any(target.status == "failure" for target in result.targets) or bool(result.errors)
    if failed:
        result.status = "partial" if any(target.status in {"success", "skipped"} for target in result.targets) else "failure"
    render(result, json_output=json_output)
    if failed:
        raise typer.Exit(1)


@beads_app.command("drop-db")
def drop_beads_db(
    name: str = typer.Argument(..., help="Database identifier, including an orphaned database."),
    yes: bool = typer.Option(False, "--yes", help="Confirm the destructive drop."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without deleting."),
    server_host: Optional[str] = typer.Option(None, "--server-host", help="Dolt server host; defaults to config."),
    server_port: Optional[str] = typer.Option(None, "--server-port", help="Dolt server port; defaults to config."),
    server_user: Optional[str] = typer.Option(None, "--server-user", help="Dolt server user; defaults to config."),
    ssh_host: Optional[str] = typer.Option(None, "--ssh-host", help="Optional SSH hop; defaults to config."),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Explicitly delete a remote database; never infer it from the current project."""
    try:
        if not (yes or dry_run):
            raise ValueError("beads drop-db requires --yes (or --dry-run)")
        host, port, user, ssh = _resolve_beads_server(home or paths.resolve_dotbrain_home(), server_host, server_port, server_user, ssh_host)
        log = beads_mod.drop_remote_beads_database(name, server_host=host, server_port=port,
                                                  server_user=user, ssh_host=ssh, dry_run=dry_run)
    except ValueError as exc:
        _beads_failure("beads drop-db", exc, json_output, 2)
    except (OSError, subprocess.SubprocessError, RuntimeError, yaml.YAMLError) as exc:
        _beads_failure("beads drop-db", exc, json_output)
    render(CommandResult("beads drop-db", targets=[TargetResult(scope="remote", changes=[log], data={"database": name})]), json_output=json_output)


@beads_app.command("list-db")
def list_beads_db(
    server_host: Optional[str] = typer.Option(None, "--server-host", help="Dolt server host; defaults to config."),
    server_port: Optional[str] = typer.Option(None, "--server-port", help="Dolt server port; defaults to config."),
    server_user: Optional[str] = typer.Option(None, "--server-user", help="Dolt server user; defaults to config."),
    ssh_host: Optional[str] = typer.Option(None, "--ssh-host", help="Optional SSH hop; defaults to config."),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """List remote database identifiers, including databases without a Brainspace."""
    try:
        host, port, user, ssh = _resolve_beads_server(home or paths.resolve_dotbrain_home(), server_host, server_port, server_user, ssh_host)
        databases = beads_mod.list_remote_beads_databases(server_host=host, server_port=port, server_user=user, ssh_host=ssh)
    except ValueError as exc:
        _beads_failure("beads list-db", exc, json_output, 2)
    except (OSError, subprocess.SubprocessError, RuntimeError, yaml.YAMLError) as exc:
        _beads_failure("beads list-db", exc, json_output)
    render(CommandResult("beads list-db", targets=[TargetResult(scope="remote", changes=databases, data={"databases": databases})]), json_output=json_output)


@beads_app.command("migrate")
def migrate_beads(
    project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."),
    all_projects: bool = typer.Option(False, "--all", help="Migrate every registered project."),
    server_host: Optional[str] = typer.Option(None, "--server-host", help="Target Dolt server host; defaults to config."),
    server_port: Optional[str] = typer.Option(None, "--server-port", help="Target Dolt server port; defaults to config."),
    server_user: Optional[str] = typer.Option(None, "--server-user", help="Target Dolt server user; defaults to config."),
    database: str = typer.Option("", "--database", help="Database override for a single project."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview the history-preserving migration."),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Migrate embedded trackers to a server, keeping history and rollback backups."""
    root = home or paths.resolve_dotbrain_home()
    try:
        if all_projects and database:
            raise ValueError("--database cannot be combined with --all")
        targets = projects.select_projects(root, project=project, all_projects=all_projects)
        host, port, user, _ = _resolve_beads_server(root, server_host, server_port, server_user)
    except ValueError as exc:
        _beads_failure("beads migrate", exc, json_output, 2)
    except (OSError, yaml.YAMLError) as exc:
        _beads_failure("beads migrate", exc, json_output)
    result = CommandResult("beads migrate")
    for target in targets:
        migration = migrate.safe_migrate_project(dotbrain_home=root, project=target.project,
            server_host=host, server_port=port, server_user=user, database=database, dry_run=dry_run)
        failure = migration.status in {"aborted-count-mismatch", "migrated-unverified", "failed", "skipped-unknown"}
        result.targets.append(TargetResult(project=target.project,
            checkout=str(target.checkout) if target.checkout else None,
            status="failure" if failure else "skipped" if migration.status.startswith("skipped-") else "success",
            changes=migration.logs, errors=migration.warnings if failure else [],
            findings=[] if failure else [{"severity": "warning", "message": w} for w in migration.warnings],
            data={"migration_status": migration.status, "pre_count": migration.pre_count,
                  "post_count": migration.post_count, "planned_commands": migration.planned_commands}))
    _finish_beads(result, json_output)


@beads_app.command("sync")
def beads_sync(
    project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."),
    all_projects: bool = typer.Option(False, "--all", help="Sync every registered project."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview tracker hydration and configured pulls."),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Hydrate declared local tracker bindings and pull configured remotes; never push."""
    root = home or paths.resolve_dotbrain_home()
    try:
        targets = projects.select_projects(root, project=project, all_projects=all_projects)
        sync = beads_mod.pull_beads_for_all(root, projects=[target.project for target in targets], dry_run=dry_run)
    except ValueError as exc:
        _beads_failure("beads sync", exc, json_output, 2)
    except (OSError, RuntimeError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        _beads_failure("beads sync", exc, json_output)
    checkout_by_project = {target.project: str(target.checkout) if target.checkout else None for target in targets}
    result = CommandResult("beads sync", targets=[TargetResult(
        project=item["project"], checkout=checkout_by_project[item["project"]], status=item["status"],
        changes=item["changes"], errors=item["errors"],
        findings=[{"severity": "warning", "message": w} for w in item["warnings"]]) for item in sync.targets])
    result.errors = [error for error in sync.errors if not any(error in item["errors"] for item in sync.targets)]
    _finish_beads(result, json_output)


from dotbrain.asset_cli import report as _asset_report

@skills_app.command("list")
def skills_list(home: HomeOption = None, runtime: RuntimeOption = "all", project: Optional[str] = typer.Option(None, "--project"), json_output: JsonOption = False) -> None:
    """Discover locally available skills."""
    _asset_report("skills", "list", home, runtime, project, json_output)


@skills_app.command("link")
def skills_link(home: HomeOption = None, runtime: RuntimeOption = "all", scope: str = typer.Option("project", "--scope"), project: Optional[str] = typer.Option(None, "--project"), repo: Optional[Path] = typer.Option(None, "--repo"), all_projects: bool = typer.Option(False, "--all"), json_output: JsonOption = False) -> None:
    """Reconcile selected skills in project or explicit global scope."""
    _asset_report("skills", "link", home, runtime, project, json_output, scope, repo, all_projects)


@agents_app.command("list")
def agents_list(home: HomeOption = None, runtime: RuntimeOption = "all", project: Optional[str] = typer.Option(None, "--project"), json_output: JsonOption = False) -> None:
    """Discover locally available agents."""
    _asset_report("agents", "list", home, runtime, project, json_output)


@agents_app.command("link")
def agents_link(home: HomeOption = None, runtime: RuntimeOption = "all", scope: str = typer.Option("project", "--scope"), project: Optional[str] = typer.Option(None, "--project"), repo: Optional[Path] = typer.Option(None, "--repo"), all_projects: bool = typer.Option(False, "--all"), json_output: JsonOption = False) -> None:
    """Reconcile selected agents in project or explicit global scope."""
    _asset_report("agents", "link", home, runtime, project, json_output, scope, repo, all_projects)


_SITE_PROJECT = typer.Option(None, "--project", help="Select a named Brainspace.")


def _site_target(project: Optional[str], home: Optional[Path]) -> tuple[Path, projects.ProjectTarget, Path]:
    root = home.expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    target = projects.select_projects(root, project=project)[0]
    brain = paths.confined_path(target.brainspace, ".brain")
    if not brain.is_dir():
        raise site_mod.SiteError(f"no Brain for '{target.project}' at {brain}")
    return root, target, brain


@site_app.command("init")
def site_init(
    project: Optional[str] = _SITE_PROJECT,
    title: Optional[str] = typer.Option(None, "--title", help="Site title. Defaults to '<name> Brain'."),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Give a Brain a site: create .brain/site/ with site.yaml, the home page, and the manual."""
    _site_operation("init", project, home, json_output, title)


def _site_operation(command: str, project: Optional[str], home: Optional[Path],
                    json_output: bool = False, title: Optional[str] = None) -> None:
    report = CommandResult(f"site {command}")
    exit_code = 0
    try:
        root, selected, brain = _site_target(project, home)
        target = TargetResult(project=selected.project,
                              checkout=str(selected.checkout) if selected.checkout else None)
        report.targets.append(target)
        if command == "init":
            target.changes.extend(f"created {path}" for path in site_mod.init(brain, title))
        else:
            kwargs = {"run": site_mod.stderr_run} if command == "build" else {}
            out = site_mod.run_site(command, dotbrain_home=root, brain=brain, **kwargs)
            if command == "build":
                target.changes.append(f"built into {out}")
                target.data = {"output": str(out)}
    except ValueError as exc:
        report.errors.append(str(exc))
        exit_code = 2
    except (site_mod.SiteError, OSError, RuntimeError, yaml.YAMLError) as exc:
        report.errors.append(str(exc))
        exit_code = 1
    if exit_code:
        report.status = "failure"
        for target in report.targets:
            target.status = "failure"
    if command in ("init", "build") or exit_code:
        render(report, json_output=json_output)
    if exit_code:
        raise typer.Exit(exit_code)


@site_app.command("dev")
def site_dev(project: Optional[str] = _SITE_PROJECT, home: HomeOption = None) -> None:
    """Serve the Brain site locally with live reload (127.0.0.1)."""
    _site_operation("dev", project, home)


@site_app.command("build")
def site_build(project: Optional[str] = _SITE_PROJECT, home: HomeOption = None,
               json_output: JsonOption = False) -> None:
    """Build the Brain site; fails on a nav link to a missing page."""
    _site_operation("build", project, home, json_output)


@site_app.command("preview")
def site_preview(project: Optional[str] = _SITE_PROJECT, home: HomeOption = None) -> None:
    """Serve the last build locally (127.0.0.1)."""
    _site_operation("preview", project, home)
