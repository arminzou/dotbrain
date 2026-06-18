"""User-facing workflows that compose the concept modules (stage 5).

These are the bodies behind ``dotbrain wire``, ``wire --all``, ``unwire``, and ``unwire --all``:
cross-concept orchestration that stitches together ``adopter_repos`` (repo links),
``control_roots`` (Brain/workspace seeding, offboarding), ``beads`` (tracker init), ``skills``
(skill manifest), and ``wiring`` (global hooks). ``cli.py`` stays a thin Typer parsing/rendering
layer over these.

The subprocess seams take an injected ``run`` callable so tests record argv instead of invoking
``bd``/``git``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from dotbrain import adopter_repos, beads, bootstrap, config, control_roots, paths, skills
from dotbrain.adopter_repos import UnwireResult, repo_for_control_root, unwire_repo
from dotbrain.beads import BootstrapResult
from dotbrain.control_roots import offboard_control_root

# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


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


@dataclass
class WireResult:
    control: Path
    repo: Path | None = None
    project: str = ""
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RefreshResult:
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    refreshed: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- wire one


def wire_project(
    *,
    dotbrain_root: Path,
    repo: Path | None = None,
    project: str | None = None,
    no_repo: bool = False,
    run_beads: bool = True,
    remote: str = "",
    server_host: str = "",
    server_port: str = "3307",
    server_user: str = "beads",
    database: str = "",
    home: Path | None = None,
    install_global_hook: bool = True,
    run: Runner = _default_run,
) -> WireResult:
    """Create/repair a control root and wire an adopter repo. Mirrors wire-project.sh's main()."""
    dotbrain_root = Path(dotbrain_root).resolve()
    if not (dotbrain_root / ".git").exists():
        raise RuntimeError(f"{dotbrain_root} is not a dotbrain git checkout")

    resolved_repo: Path | None
    if no_repo:
        if not project:
            raise ValueError("--no-repo requires --name <project>")
        resolved_repo = None
    else:
        resolved_repo = adopter_repos.repo_root(repo, run)
        project = project or resolved_repo.name

    if resolved_repo is not None:
        adopter_repos.ensure_not_wired_to_foreign_dotbrain(resolved_repo, dotbrain_root)

    control = paths.control_root(dotbrain_root, project)
    archive = dotbrain_root / "projects" / ".archive" / project
    unarchived = False
    if archive.is_dir() and not control.is_dir():
        run(["git", "-C", str(dotbrain_root), "mv",
             f"projects/.archive/{project}", f"projects/{project}"])
        unarchived = True
    control.mkdir(parents=True, exist_ok=True)
    if no_repo:
        (control / ".repo").write_text("(brain-only)\n")
    else:
        assert resolved_repo is not None
        (control / ".repo").write_text(f"{adopter_repos.abbrev_home(resolved_repo, home)}\n")

    result = WireResult(control=control, repo=resolved_repo, project=project)
    if unarchived:
        result.logs.append(f"unarchived {project} from projects/.archive/{project}")

    control_roots.ensure_control_gitignore(control)
    control_roots.seed_brain(control, dotbrain_root)
    config.migrate_legacy_skill_manifest(dotbrain_root, project)
    result.warnings += control_roots.seed_agent_workspaces(control, dotbrain_root, home)
    if install_global_hook:
        bootstrap.install_global_claude_hook(dotbrain_root, home=home)
    beads_log = beads.init_beads(
        control, project, dotbrain_root,
        run_beads=run_beads, remote=remote,
        server_host=server_host, server_port=server_port,
        server_user=server_user, database=database, run=run,
    )
    if beads_log:
        result.logs.append(beads_log)
    if run_beads:
        # a deviating backend must be durable in project.yaml or hydration cannot
        # reproduce it on a fresh clone
        record_log = config.record_project_beads(
            dotbrain_root, project,
            config.ProjectBeads(
                mode="server" if server_host else "embedded",
                remote=remote,
                database=database,
            ),
        )
        if record_log:
            result.logs.append(record_log)
    result.logs.append(
        f"control root ready at projects/{project} (not committed); "
        f"review and commit (suggested: feat(brain): wire {project})"
    )

    if no_repo:
        result.logs.append(f"created brain-only control root: {control}")
        return result

    assert resolved_repo is not None
    result.warnings += adopter_repos.wire_repo(resolved_repo, control, dotbrain_root, run)
    if paths.INJECT_ADOPTER_POINTER:
        result.warnings += adopter_repos.ensure_agent_context_pointer(resolved_repo)
    result.warnings += adopter_repos.verify_wiring(resolved_repo, run)
    result.logs.append(f"wired {project}")
    return result


# --------------------------------------------------------------------------- wire all


def _repair_adopter_repo_links(
    control: Path, repo: Path, dotbrain_root: Path, run: Runner, *, skip_beads_link: bool = False
) -> tuple[list[str], list[str]]:
    git_marker = repo / ".git"
    if not (git_marker.is_dir() or git_marker.is_file()):
        return [], [f"{repo} is not a git repo; skipping"]

    warnings = adopter_repos.wire_repo(
        repo,
        control,
        dotbrain_root,
        run,
        skip_beads_link=skip_beads_link,
    )
    return [f"wired {control.name} -> {repo}"], warnings


def wire_all_projects(
    dotbrain_root: Path,
    repo_base: Path | None = None,
    home: Path | None = None,
    run: Runner = _default_run,
) -> BootstrapResult:
    """Re-seed brains from templates and repair agent workspace symlinks and hooks for every
    wired control root.  Dotbrain-owned files (DOTBRAIN.md, README.md) are always
    overwritten so template changes propagate.

    Mirrors bootstrap.sh wire_control_roots.
    """
    dotbrain_root = Path(dotbrain_root).resolve()
    rb = repo_base or (Path.home() / "repos" / "projects")
    result = BootstrapResult()
    cfg = config.load_config(dotbrain_root)

    for control in paths.control_roots(dotbrain_root):
        control_roots.seed_brain(control, dotbrain_root)
        # repair per-control-root agent workspace hooks and configs
        result.warnings += control_roots.seed_agent_workspaces(control, dotbrain_root, home)

        repo = adopter_repos.repo_for_control_root(control, dotbrain_root, rb, home)
        if repo is None:
            result.warnings.append(
                f"no repo found for control root {control.name}; "
                f"add {control}/.repo or create {rb}/{control.name}"
            )
            continue

        logs, warnings = _repair_adopter_repo_links(
            control, repo, dotbrain_root, run,
            # a declared no-beads project never has a .beads dir; not a warning
            skip_beads_link=config.load_project_config(dotbrain_root, control.name).mode == "none",
        )
        result.logs += logs
        result.warnings += warnings
        if logs:
            result.wired.append(str(repo))

    return result


# --------------------------------------------------------------------------- refresh


def _controls_for_refresh(dotbrain_root: Path, projects: Sequence[str] | None) -> list[Path]:
    controls = paths.control_roots(dotbrain_root)
    if projects is None:
        return controls

    by_name = {control.name: control for control in controls}
    selected: list[Path] = []
    missing: list[str] = []
    for project in projects:
        control = by_name.get(project)
        if control is None:
            missing.append(project)
        else:
            selected.append(control)
    if missing:
        raise ValueError(f"no control root: {', '.join(missing)}")
    return selected


def refresh_projects(
    dotbrain_root: Path,
    *,
    projects: Sequence[str] | None = None,
    repo_base: Path | None = None,
    home: Path | None = None,
    workspaces: Sequence[str] = (".claude", ".codex"),
    run: Runner = _default_run,
) -> RefreshResult:
    """Refresh project control roots without creating or offboarding projects.

    Composes the existing concept owners: Brain/workspace seeding, adopter-repo link repair,
    beads load/hydration, and project skill linking.
    """
    dotbrain_root = Path(dotbrain_root).resolve()
    if not (dotbrain_root / ".git").exists():
        raise RuntimeError(f"{dotbrain_root} is not a dotbrain git checkout")

    result = RefreshResult()
    controls = _controls_for_refresh(dotbrain_root, projects)
    cfg = config.load_config(dotbrain_root)
    rb = repo_base or (Path.home() / "repos" / "projects")

    for control in controls:
        control_roots.seed_brain(control, dotbrain_root)
        result.warnings += control_roots.seed_agent_workspaces(control, dotbrain_root, home)
        migrate_log = config.migrate_legacy_skill_manifest(dotbrain_root, control.name)
        if migrate_log:
            result.logs.append(migrate_log)
        extras = config.load_project_skills(dotbrain_root, control.name)
        skill_paths = skills.project_link_set(extras)
        link_result = skills.link_project(dotbrain_root, control, workspaces, skill_paths)
        result.logs += [f"pruned skill {entry}" for entry in link_result.pruned]
        result.logs += [f"stashed collision {path}" for path in link_result.stashed]
        result.warnings += link_result.warnings

        repo = repo_for_control_root(control, dotbrain_root, rb, home)
        if repo is None:
            if not _is_brain_only_control(control):
                result.warnings.append(
                    f"no repo found for control root {control.name}; "
                    f"add {control}/.repo or create {rb}/{control.name}"
                )
        else:
            logs, warnings = _repair_adopter_repo_links(
                control,
                repo,
                dotbrain_root,
                run,
                skip_beads_link=config.load_project_config(dotbrain_root, control.name).mode == "none",
            )
            result.logs += logs
            result.warnings += warnings

        result.refreshed.append(control.name)
        result.logs.append(f"refreshed {control.name} ({len(link_result.linked)} skills linked)")

    beads_result = beads.pull_beads_for_all(
        dotbrain_root,
        run=run,
        projects=[control.name for control in controls],
    )
    result.logs += beads_result.logs
    result.warnings += beads_result.warnings
    return result


def refresh_project(
    dotbrain_root: Path,
    project: str,
    *,
    repo_base: Path | None = None,
    home: Path | None = None,
    workspaces: Sequence[str] = (".claude", ".codex"),
    run: Runner = _default_run,
) -> RefreshResult:
    """Refresh one project control root without creating or offboarding it."""
    return refresh_projects(
        dotbrain_root,
        projects=[project],
        repo_base=repo_base,
        home=home,
        workspaces=workspaces,
        run=run,
    )


def _is_brain_only_control(control: Path) -> bool:
    repo_file = control / ".repo"
    return repo_file.is_file() and repo_file.read_text().strip() == "(brain-only)"


# --------------------------------------------------------------------------- unwire


def _resolve_project(repo: Path, project: str | None) -> str:
    """Infer project name from the .brain symlink target; fall back to repo dir name."""
    brain = repo / ".brain"
    if not project and brain.is_symlink():
        project = brain.resolve().parent.name
    return project or repo.name


def _repo_root(repo: Path | None, run: Runner) -> Path:
    cwd = repo or Path.cwd()
    result = run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip())


def unwire_project(
    *,
    dotbrain_root: Path,
    repo: Path | None = None,
    project: str | None = None,
    no_repo: bool = False,
    offboard: str = "keep",
    dry_run: bool = False,
    run: Runner = _default_run,
) -> UnwireResult:
    """Disconnect an adopter repo from its dotbrain control root and offboard the control root.

    Dropping a server-backend project's remote beads database is a separate, explicit step
    (``beads.drop_remote_beads_database`` / the ``beads drop-db`` command).
    """
    dotbrain_root = Path(dotbrain_root).resolve()
    if not (dotbrain_root / ".git").exists():
        raise RuntimeError(f"{dotbrain_root} is not a dotbrain git checkout")

    if no_repo:
        if not project:
            raise ValueError("--no-repo requires --name")
        resolved_repo = None
        result = UnwireResult(project=project, repo=None)
    else:
        resolved_repo = _repo_root(repo, run)
        project = _resolve_project(resolved_repo, project)
        result = unwire_repo(resolved_repo, dry_run=dry_run)
        result.project = project
    result.logs += offboard_control_root(dotbrain_root, project, offboard, dry_run=dry_run, run=run)
    if offboard in {"archive", "delete"} and not dry_run:
        # the control root is gone from projects/; a leftover entry would make
        # bootstrap try to hydrate a non-existent project
        removed = config.remove_project_beads(dotbrain_root, project)
        if removed:
            result.logs.append(removed)
    result.logs.append(
        f"unwired {project} (repo: {resolved_repo})\n"
        "repo edits are not committed; review and commit if wanted"
    )
    return result


def unwire_all_projects(
    dotbrain_root: Path,
    offboard: str = "keep",
    dry_run: bool = False,
    run: Runner = _default_run,
) -> list[UnwireResult]:
    """Unwire every project control root. Continues on per-project failure.

    ``offboard`` defaults to ``keep`` (control roots are not destroyed in batch
    mode). Mutually exclusive with ``--archive``/``--delete`` — use per-project
    ``unwire`` for destructive offboard.
    """
    dotbrain_root = Path(dotbrain_root).resolve()
    results: list[UnwireResult] = []
    for control in paths.control_roots(dotbrain_root):
        project = control.name
        try:
            repo = repo_for_control_root(control, dotbrain_root)
            if repo and repo.is_dir():
                result = unwire_repo(repo, dry_run=dry_run)
            else:
                result = UnwireResult(project=project, repo=None)
            result.project = project
            result.logs += offboard_control_root(
                dotbrain_root, project, offboard, dry_run=dry_run, run=run,
            )
            if offboard in {"archive", "delete"} and not dry_run:
                removed = config.remove_project_beads(dotbrain_root, project)
                if removed:
                    result.logs.append(removed)
            result.logs.append(
                f"unwired {project} (repo: {repo})"
            )
            results.append(result)
        except Exception as exc:
            results.append(UnwireResult(
                project=project,
                logs=[f"error unwiring {project}: {exc}"],
            ))
    return results
