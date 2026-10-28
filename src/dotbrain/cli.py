"""dotbrain CLI entrypoint."""

from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path
from enum import Enum
from typing import Optional

import typer
import yaml
from dotbrain.options import HomeOption, RuntimeOption, JsonOption
from dotbrain.results import CommandResult, TargetResult, HelpTyper, ResultGroup, render
from dotbrain.presentation import activity, project_progress

from dotbrain import __version__
from dotbrain import projects
from dotbrain import doctor as doctor_mod
from dotbrain import beads as beads_mod, bootstrap as bootstrap_mod, config, home_sync, hooks, migrate, paths, site as site_mod, workflows

app = HelpTyper(
    cls=ResultGroup,
    help="dotbrain CLI for wiring project Brainspaces and skills into coding agents.",
    no_args_is_help=True,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
skills_app = HelpTyper(help="Link dotbrain skills into agent runtimes.", no_args_is_help=True)
subagents_app = HelpTyper(help="Link your custom vendor-native subagents into agent runtimes.", no_args_is_help=True)
beads_app = HelpTyper(help="Manage beads tracker state and backend.", no_args_is_help=True)
hook_app = HelpTyper(help="Run dotbrain hook entrypoints.", no_args_is_help=True)
site_app = HelpTyper(help="Set up and run a Brain's private site.", no_args_is_help=True)
projects_app = HelpTyper(help="Discover registered projects and inspect local settings.", no_args_is_help=True)
app.add_typer(skills_app, name="skills")
app.add_typer(subagents_app, name="subagents")
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
    """Sync the home (waiting at most 10 s), then emit a wired repo's Brain context. Fail-open."""

    hooks.handle_claude_event("startup")


@hook_app.command("stop")
def hook_stop(args: list[str] = typer.Argument(None)) -> None:
    """Start a detached push-only home sync and return at once. Fail-open and silent."""

    hooks.handle_claude_event("turn-end")


@hook_app.command("session-end")
def hook_session_end(args: list[str] = typer.Argument(None)) -> None:
    """Start a detached full home sync and return at once. Fail-open and silent."""

    hooks.handle_claude_event("session-end")


# str enums, not Literal: Typer before 0.16 cannot resolve Literal and then fails every command.
HookEvent = Enum("HookEvent", {event: event for event in hooks.EVENTS}, type=str)
HookFormat = Enum("HookFormat", {"text": "text", "json": "json"}, type=str)


@hook_app.command("run")
def hook_run(
    event: HookEvent = typer.Option(
        ..., "--event", metavar="<event>", help="Session event: startup, resume, clear, compaction, turn-end, or session-end."),
    checkout: Optional[Path] = typer.Option(None, "--checkout",
                                            help="Checkout the event belongs to. Default: the working directory."),
    output: HookFormat = typer.Option("text", "--format",
                                                   help="Context output: text (raw) or json (an additional_context object)."),
) -> None:
    """Handle a session event for any runtime adapter, without reading a hook payload. Fail-open."""

    hooks.handle_event(event.value, checkout, output.value)


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
    render(result, json_output=json_output)
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
    status = None

    def confirm(found, prompt):
        if status:  # the prompt needs the line the spinner occupies
            status.stop()
        for line in found:
            typer.echo(line)
        typer.echo(prompt + " ", nl=False)
        answer = input().strip().lower() in ("", "y", "yes")
        if status:
            status.start()
        return answer

    root = Path(home).expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        with activity("Bootstrapping...", enabled=not json_output) as status:
            report = bootstrap_mod.prepare(
                root, runtime, confirm=confirm if not json_output and sys.stdin.isatty() and sys.stdout.isatty() else None,
            )
    except ValueError as exc:
        render(CommandResult("bootstrap", "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2)
    render(report, json_output=json_output)
    if report.status != "success":
        raise typer.Exit(1)


def _render_doctor(report: doctor_mod.DoctorReport, *, json_output: bool = False, verbose: bool = False) -> None:
    result = doctor_mod.as_result(report)
    if json_output:
        render(result, json_output=True)
    else:
        from dotbrain.presentation import render_doctor
        render_doctor(report, verbose=verbose)
    if result.status != "success":
        raise typer.Exit(1)


@app.command()
def doctor(home: HomeOption = None,
           project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."),
           all_projects: bool = typer.Option(False, "--all", help="Inspect every registered project."),
           verbose: bool = typer.Option(False, "--verbose", "-v", help="Include healthy checks and informational context."),
           json_output: JsonOption = False) -> None:
    """Read-only health check of machine readiness and selected project setup."""
    label = "Checking machine and all projects..." if all_projects else "Checking machine and project..."
    try:
        root = home.expanduser().resolve() if home else paths.resolve_dotbrain_home()
        with activity(label, enabled=not json_output) as status:
            report = doctor_mod.run_doctor(root, project=project, all_projects=all_projects,
                                           progress=project_progress(status, "Checked") if all_projects else None)
    except ValueError as exc:
        render(CommandResult("doctor", "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (RuntimeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        render(CommandResult("doctor", "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    _render_doctor(report, json_output=json_output, verbose=verbose)


@app.command()
def wire(
    repo: Optional[Path] = typer.Option(None, '--repo', help='Checkout to attach; defaults to the current Git checkout.'),
    project: Optional[str] = typer.Option(None, '--project', help='Select a named Brainspace.'),
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
        with activity("Wiring project...", enabled=not json_output):
            result = workflows.wire_project(dotbrain_home=root, repo=repo, project=project,
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
        with activity("Refreshing all projects..." if all_projects else "Refreshing project...", enabled=not json_output) as status:
            result = workflows.refresh_projects(root, project=project, all_projects=all_projects, runtime=runtime,
                                                progress=project_progress(status, "Refreshing") if all_projects else None)
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
def detach(runtime: RuntimeOption, home: HomeOption = None, json_output: JsonOption = False) -> None:
    """Remove dotbrain's machine-wide delivery from a runtime."""
    root = home.expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        report = workflows.detach_runtime(root, runtime)
    except ValueError as exc:
        render(CommandResult('detach', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (OSError, RuntimeError, yaml.YAMLError) as exc:
        render(CommandResult('detach', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    render(report, json_output=json_output)
    if report.status != 'success':
        raise typer.Exit(1)


@app.command()
def unwire(
    repo: Optional[Path] = typer.Option(None, '--repo', help='Checkout whose wiring to remove.'),
    project: Optional[str] = typer.Option(None, '--project', help='Select a named Brainspace.'),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Remove a checkout's wiring while retaining its Brainspace and tracker databases."""
    root = home.expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        results = [workflows.unwire_project(dotbrain_home=root, repo=repo, project=project)]
    except ValueError as exc:
        render(CommandResult('unwire', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (RuntimeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        render(CommandResult('unwire', 'failure', errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    _render_lifecycle('unwire', results, json_output)


_SYNC_OUTCOMES = {
    "pushed": "pushed {waiting} to {upstream}",
    "rejected": "push rejected: {upstream} has moved; {waiting} wait for the next full sync",
    "unreachable": "remote unreachable; {waiting} waiting to be pushed",
    "no-upstream": "no remote: the current branch has no upstream, so sync commits stay local",
}


_SYNC_EPILOG = ("Acts on the whole home: one commit per changed Brainspace, then one home commit for the rest. "
                "A full sync then fetches and merges the upstream, keeping this machine's version of a file "
                "both sides changed and writing "
                "the other as NAME.sync-conflict-DATE-HOST.ext beside it (an edit wins over a delete). "
                "A push rejected because the remote moved is retried at most 3 times; sync never force-pushes. "
                "Files over sync.max-file-size in config.yaml (bytes, or a size such as 500KB or 1MB; default 1MB) "
                "stay uncommitted and are reported. If incoming changes would overwrite an uncommitted or ignored "
                "local file, Git refuses the merge; sync reports Git's diagnostic, pushes nothing, and fails. "
                "Offline, rejected, and remote-less homes exit 0 and keep "
                "the commits. Nested Git repositories are never recorded. Recording is refused during a "
                "merge, rebase, cherry-pick, or revert, with unmerged paths, or on a detached HEAD. "
                "Turn sync off with sync.enabled: false. Known limit: sync unstages everything before "
                "recording, so index-only state (partially staged hunks, git rm --cached, a staged mode "
                "change) is replaced by the working tree.")


@app.command(epilog=_SYNC_EPILOG)
def sync(
    push_only: bool = typer.Option(False, "--push-only", help="Record and push without fetching the remote."),
    wait_for_lock: float = typer.Option(0, "--wait-for-lock", hidden=True, min=0),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Record uncommitted home changes as sync commits, integrate the upstream, and push."""
    root = home.expanduser().resolve() if home is not None else paths.resolve_dotbrain_home()
    try:
        with activity("Syncing home...", enabled=not json_output):
            report = home_sync.sync(root, push_only=push_only, wait_for_lock=wait_for_lock)
    except ValueError as exc:
        render(CommandResult("sync", "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(2) from exc
    except (home_sync.SyncError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        render(CommandResult("sync", "failure", errors=[str(exc)]), json_output=json_output)
        raise typer.Exit(1) from exc
    target = TargetResult(scope="home", checkout=str(root), changes=list(report.commits),
                          data=dataclasses.asdict(report))
    if report.status == "disabled":
        target.findings.append({"severity": "info", "message": "home sync is disabled (sync.enabled: false)"})
    elif report.status == "locked":
        target.findings.append({"severity": "info", "message": "another sync is running; exited without changes"})
    elif report.status == "blocked":
        message = (f"cannot record while the home has {', '.join(report.blocked_by)}; "
                   "nothing was recorded; finish or abort that, then sync again")
        if not push_only:
            target.status, target.errors = "failure", [message]
            render(CommandResult("sync", "failure", targets=[target]), json_output=json_output)
            raise typer.Exit(1)
        target.findings.append({"severity": "warning", "message": message})
    elif report.status == "collision":
        message = (f"did not integrate {report.upstream}; nothing was pushed. Git reported:\n"
                   + "\n".join(report.collisions))
        target.status, target.errors = "failure", [message]
        render(CommandResult("sync", "failure", targets=[target]), json_output=json_output)
        raise typer.Exit(1)
    else:
        target.findings += [{"severity": "warning", "message": f"not committed, larger than the size limit: {path}"}
                            for path in report.skipped]
        target.findings += [{"severity": "warning", "message": f"not committed, a nested Git repository: {path}"}
                            for path in report.nested]
        target.findings += [{"severity": "warning", "message": f"conflict copy to reconcile: {path}"}
                            for path in report.conflict_copies]
        outcome = _SYNC_OUTCOMES.get(report.push)
        if outcome:
            count = report.pushed if report.push == "pushed" else report.waiting
            message = outcome.format(upstream=report.upstream, waiting=f"{count} commit{'' if count == 1 else 's'}")
            if report.push == "rejected" and not push_only:
                message = f"{message} (gave up after {report.attempts} attempts)"
            if report.push == "pushed":
                target.changes.append(message)
            else:
                target.findings.append({"severity": "info" if report.push == "no-upstream" else "warning",
                                        "message": message})
    render(CommandResult("sync", targets=[target]), json_output=json_output)


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


def _finish_beads(result, json_output, *, preview=False):
    failed = any(target.status == "failure" for target in result.targets) or bool(result.errors)
    if failed:
        result.status = "partial" if any(target.status in {"success", "skipped"} for target in result.targets) else "failure"
    render(result, json_output=json_output, preview=preview)
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
        with activity("Deleting remote database...", enabled=not json_output and not dry_run):
            log = beads_mod.drop_remote_beads_database(name, server_host=host, server_port=port,
                                                      server_user=user, ssh_host=ssh, dry_run=dry_run)
    except ValueError as exc:
        _beads_failure("beads drop-db", exc, json_output, 2)
    except (OSError, subprocess.SubprocessError, RuntimeError, yaml.YAMLError) as exc:
        _beads_failure("beads drop-db", exc, json_output)
    render(CommandResult("beads drop-db", targets=[TargetResult(scope="remote", changes=[log], data={"database": name})]), json_output=json_output, preview=dry_run)


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
        with activity("Listing remote databases...", enabled=not json_output):
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
        with activity("Preparing tracker migration...", enabled=not json_output and not dry_run):
            targets = projects.select_projects(root, project=project, all_projects=all_projects)
            host, port, user, _ = _resolve_beads_server(root, server_host, server_port, server_user)
    except ValueError as exc:
        _beads_failure("beads migrate", exc, json_output, 2)
    except (OSError, yaml.YAMLError) as exc:
        _beads_failure("beads migrate", exc, json_output)
    result = CommandResult("beads migrate")
    for target in targets:
        with activity(f"Migrating tracker for {target.project}...", enabled=not json_output and not dry_run):
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
    _finish_beads(result, json_output, preview=dry_run)


@beads_app.command("sync")
def beads_sync(
    project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."),
    all_projects: bool = typer.Option(False, "--all", help="Sync every registered project."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview tracker sync and configured pulls."),
    home: HomeOption = None, json_output: JsonOption = False,
) -> None:
    """Sync declared local tracker bindings and pull configured remotes; never push."""
    root = home or paths.resolve_dotbrain_home()
    try:
        with activity("Syncing all trackers..." if all_projects else "Syncing tracker...", enabled=not json_output and not dry_run):
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
    _finish_beads(result, json_output, preview=dry_run)


from dotbrain.asset_cli import report as _asset_report

@skills_app.command("list")
def skills_list(home: HomeOption = None, runtime: RuntimeOption = "all", project: Optional[str] = typer.Option(None, "--project", help="Show selections for a named Brainspace."), json_output: JsonOption = False) -> None:
    """Discover locally available skills."""
    _asset_report("skills", "list", home, runtime, project, json_output)


@skills_app.command("link")
def skills_link(home: HomeOption = None, runtime: RuntimeOption = "all", scope: str = typer.Option("project", "--scope", help="Delivery scope: project or global."), project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."), repo: Optional[Path] = typer.Option(None, "--repo", help="Select a wired checkout; defaults to the current checkout."), all_projects: bool = typer.Option(False, "--all", help="Reconcile every registered project."), json_output: JsonOption = False) -> None:
    """Reconcile selected skills in project or explicit global scope."""
    _asset_report("skills", "link", home, runtime, project, json_output, scope, repo, all_projects)


@subagents_app.command("list")
def subagents_list(home: HomeOption = None, runtime: RuntimeOption = "all", project: Optional[str] = typer.Option(None, "--project", help="Show selections for a named Brainspace."), json_output: JsonOption = False) -> None:
    """Discover locally available custom subagents."""
    _asset_report("agents", "list", home, runtime, project, json_output)


@subagents_app.command("link")
def subagents_link(home: HomeOption = None, runtime: RuntimeOption = "all", scope: str = typer.Option("project", "--scope", help="Delivery scope: project or global."), project: Optional[str] = typer.Option(None, "--project", help="Select a named Brainspace."), repo: Optional[Path] = typer.Option(None, "--repo", help="Select a wired checkout; defaults to the current checkout."), all_projects: bool = typer.Option(False, "--all", help="Reconcile every registered project."), json_output: JsonOption = False) -> None:
    """Reconcile selected custom subagents in project or explicit global scope."""
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
            out = site_mod.run_site(command, dotbrain_home=root, brain=brain,
                setup_progress=activity("Preparing site engine...", enabled=not json_output and command != "preview"), **kwargs)
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
