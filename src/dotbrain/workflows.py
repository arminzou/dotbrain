"""User-facing workflows that compose the concept modules (stage 5).

These are the bodies behind ``dotbrain wire``, ``wire --all``, ``unwire``, and ``unwire --all``:
cross-concept orchestration that stitches together ``adopter_repos`` (repo links),
``brainspaces`` (Brain/workspace seeding, offboarding), ``beads`` (tracker init), ``skills``
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

from dotbrain import adopter_repos, beads, bootstrap, config, brainspaces, paths, skills, subagents
from dotbrain.adopter_repos import UnwireResult, repo_for_brainspace, unwire_repo
from dotbrain.beads import BootstrapResult
from dotbrain.brainspaces import offboard_brainspace

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
    brainspace: Path
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
    dotbrain_home: Path,
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
    """Create/repair a Brainspace and wire an adopter repo. Mirrors wire-project.sh's main()."""
    dotbrain_home = Path(dotbrain_home).resolve()
    bootstrap.ensure_root_gitignore(dotbrain_home)
    if not (dotbrain_home / ".git").exists():
        raise RuntimeError(f"{dotbrain_home} is not a dotbrain git checkout")

    resolved_repo: Path | None
    if no_repo:
        if not project:
            raise ValueError("--no-repo requires --name <project>")
        resolved_repo = None
    else:
        resolved_repo = adopter_repos.repo_root(repo, run)
        project = project or resolved_repo.name

    if resolved_repo is not None:
        adopter_repos.ensure_not_wired_to_foreign_dotbrain(resolved_repo, dotbrain_home)

    brainspace = paths.brainspace(dotbrain_home, project)
    rel = paths.data_dir(dotbrain_home).name
    archive = paths.data_dir(dotbrain_home) / ".archive" / project
    unarchived = False
    if archive.is_dir() and not brainspace.is_dir():
        run(["git", "-C", str(dotbrain_home), "mv",
             f"{rel}/.archive/{project}", f"{rel}/{project}"])
        unarchived = True
    brainspace.mkdir(parents=True, exist_ok=True)
    if no_repo:
        (brainspace / ".repo").write_text("(brain-only)\n")
    else:
        assert resolved_repo is not None
        (brainspace / ".repo").write_text(f"{adopter_repos.abbrev_home(resolved_repo, home)}\n")

    result = WireResult(brainspace=brainspace, repo=resolved_repo, project=project)
    if unarchived:
        result.logs.append(f"unarchived {project} from {rel}/.archive/{project}")

    brainspaces.seed_brain(brainspace, dotbrain_home)
    config.migrate_legacy_skill_manifest(dotbrain_home, project)
    active_workspaces = brainspaces.active_agent_workspaces(brainspace, dotbrain_home)
    result.warnings += brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, home)
    if install_global_hook:
        bootstrap.install_global_claude_hook(dotbrain_home, home=home)
    beads_log = beads.init_beads(
        brainspace, project, dotbrain_home,
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
            dotbrain_home, project,
            config.ProjectBeads(
                mode="server" if server_host else "embedded",
                remote=remote,
                database=database,
            ),
        )
        if record_log:
            result.logs.append(record_log)
    result.logs.append(
        f"Brainspace ready at {rel}/{project} (not committed); "
        f"review and commit (suggested: feat(brain): wire {project})"
    )

    if no_repo:
        result.logs.append(f"created brain-only Brainspace: {brainspace}")
        return result

    assert resolved_repo is not None
    result.warnings += adopter_repos.wire_repo(
        resolved_repo, brainspace, dotbrain_home, run, workspace_links=active_workspaces
    )
    if paths.INJECT_ADOPTER_POINTER:
        result.warnings += adopter_repos.ensure_agent_context_pointer(resolved_repo)
    expected_links = (".brain", *active_workspaces)
    if (brainspace / ".beads").exists():
        expected_links += (".beads",)
    result.warnings += adopter_repos.verify_wiring(
        resolved_repo, run, expected_links=expected_links
    )
    result.logs.append(f"wired {project}")
    return result


# --------------------------------------------------------------------------- wire all


def _repair_adopter_repo_links(
    brainspace: Path, repo: Path, dotbrain_home: Path, run: Runner, *, skip_beads_link: bool = False
) -> tuple[list[str], list[str]]:
    git_marker = repo / ".git"
    if not (git_marker.is_dir() or git_marker.is_file()):
        return [], [f"{repo} is not a git repo; skipping"]

    warnings = adopter_repos.wire_repo(
        repo,
        brainspace,
        dotbrain_home,
        run,
        skip_beads_link=skip_beads_link,
        workspace_links=brainspaces.active_agent_workspaces(brainspace, dotbrain_home),
    )
    return [f"wired {brainspace.name} -> {repo}"], warnings


def wire_all_projects(
    dotbrain_home: Path,
    repo_base: Path | None = None,
    home: Path | None = None,
    run: Runner = _default_run,
) -> BootstrapResult:
    """Re-seed brains from templates and repair agent workspace symlinks and hooks for every
    wired Brainspace.  Dotbrain-owned files (DOTBRAIN.md, README.md) are always
    overwritten so template changes propagate.

    Mirrors bootstrap.sh wire_brainspaces.
    """
    dotbrain_home = Path(dotbrain_home).resolve()
    bootstrap.ensure_root_gitignore(dotbrain_home)
    rb = repo_base or (Path.home() / "repos" / "projects")
    result = BootstrapResult()
    cfg = config.load_config(dotbrain_home)

    for brainspace in paths.brainspaces(dotbrain_home):
        brainspaces.seed_brain(brainspace, dotbrain_home)
        # repair per-Brainspace agent workspace hooks and configs
        result.warnings += brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, home)

        repo = adopter_repos.repo_for_brainspace(brainspace, dotbrain_home, rb, home)
        if repo is None:
            result.warnings.append(
                f"no repo found for Brainspace {brainspace.name}; "
                f"add {brainspace}/.repo or create {rb}/{brainspace.name}"
            )
            continue

        logs, warnings = _repair_adopter_repo_links(
            brainspace, repo, dotbrain_home, run,
            # a declared no-beads project never has a .beads dir; not a warning
            skip_beads_link=config.load_project_config(dotbrain_home, brainspace.name).mode == "none",
        )
        result.logs += logs
        result.warnings += warnings
        if logs:
            result.wired.append(str(repo))

    return result


# --------------------------------------------------------------------------- refresh


def _brainspaces_for_refresh(dotbrain_home: Path, projects: Sequence[str] | None) -> list[Path]:
    brainspaces = paths.brainspaces(dotbrain_home)
    if projects is None:
        return brainspaces

    by_name = {brainspace.name: brainspace for brainspace in brainspaces}
    selected: list[Path] = []
    missing: list[str] = []
    for project in projects:
        brainspace = by_name.get(project)
        if brainspace is None:
            missing.append(project)
        else:
            selected.append(brainspace)
    if missing:
        raise ValueError(f"no Brainspace: {', '.join(missing)}")
    return selected


def refresh_projects(
    dotbrain_home: Path,
    *,
    projects: Sequence[str] | None = None,
    repo_base: Path | None = None,
    home: Path | None = None,
    workspaces: Sequence[str] = (".claude", ".codex"),
    run: Runner = _default_run,
) -> RefreshResult:
    """Refresh project Brainspaces without creating or offboarding projects.

    Composes the existing concept owners: Brain/workspace seeding, adopter-repo link repair,
    beads load/hydration, and project skill linking.
    """
    dotbrain_home = Path(dotbrain_home).resolve()
    if not (dotbrain_home / ".git").exists():
        raise RuntimeError(f"{dotbrain_home} is not a dotbrain git checkout")

    result = RefreshResult()
    brainspace_paths = _brainspaces_for_refresh(dotbrain_home, projects)
    cfg = config.load_config(dotbrain_home)
    rb = repo_base or (Path.home() / "repos" / "projects")

    for brainspace in brainspace_paths:
        brainspaces.seed_brain(brainspace, dotbrain_home)
        result.warnings += brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, home)
        migrate_log = config.migrate_legacy_skill_manifest(dotbrain_home, brainspace.name)
        if migrate_log:
            result.logs.append(migrate_log)
        extras = config.load_project_skills(dotbrain_home, brainspace.name)
        skill_paths = skills.project_link_set(extras)
        declared_workspaces = brainspaces.active_agent_workspaces(brainspace, dotbrain_home)
        active_workspaces = tuple(ws for ws in workspaces if ws in declared_workspaces)
        link_result = skills.link_project(dotbrain_home, brainspace, active_workspaces, skill_paths)
        result.logs += [f"pruned skill {entry}" for entry in link_result.pruned]
        result.logs += [f"stashed collision {path}" for path in link_result.stashed]
        result.warnings += link_result.warnings
        subagent_names = subagents.project_link_set(
            config.load_project_subagents(dotbrain_home, brainspace.name)
        )
        subagent_result = subagents.link_project_subagents(
            dotbrain_home,
            brainspace,
            active_workspaces,
            subagent_names,
        )
        result.logs += [f"pruned subagent {entry}" for entry in subagent_result.pruned]
        result.logs += [f"stashed subagent collision {path}" for path in subagent_result.stashed]
        result.warnings += subagent_result.warnings
        result.logs.append(
            f"project: linked {len(subagent_result.linked)} subagent file(s) into {brainspace.name}"
        )

        repo = repo_for_brainspace(brainspace, dotbrain_home, rb, home)
        if repo is None:
            if not _is_brain_only_brainspace(brainspace):
                result.warnings.append(
                    f"no repo found for Brainspace {brainspace.name}; "
                    f"add {brainspace}/.repo or create {rb}/{brainspace.name}"
                )
        else:
            logs, warnings = _repair_adopter_repo_links(
                brainspace,
                repo,
                dotbrain_home,
                run,
                skip_beads_link=config.load_project_config(dotbrain_home, brainspace.name).mode == "none",
            )
            result.logs += logs
            result.warnings += warnings

        result.refreshed.append(brainspace.name)
        result.logs.append(f"refreshed {brainspace.name} ({len(link_result.linked)} skills linked)")

    beads_result = beads.pull_beads_for_all(
        dotbrain_home,
        run=run,
        projects=[brainspace.name for brainspace in brainspace_paths],
    )
    result.logs += beads_result.logs
    result.warnings += beads_result.warnings
    return result


def refresh_project(
    dotbrain_home: Path,
    project: str,
    *,
    repo_base: Path | None = None,
    home: Path | None = None,
    workspaces: Sequence[str] = (".claude", ".codex"),
    run: Runner = _default_run,
) -> RefreshResult:
    """Refresh one project Brainspace without creating or offboarding it."""
    return refresh_projects(
        dotbrain_home,
        projects=[project],
        repo_base=repo_base,
        home=home,
        workspaces=workspaces,
        run=run,
    )


def _is_brain_only_brainspace(brainspace: Path) -> bool:
    repo_file = brainspace / ".repo"
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
    dotbrain_home: Path,
    repo: Path | None = None,
    project: str | None = None,
    no_repo: bool = False,
    offboard: str = "keep",
    dry_run: bool = False,
    run: Runner = _default_run,
) -> UnwireResult:
    """Disconnect an adopter repo from its dotbrain Brainspace and offboard the Brainspace.

    Dropping a server-backend project's remote beads database is a separate, explicit step
    (``beads.drop_remote_beads_database`` / the ``beads drop-db`` command).
    """
    dotbrain_home = Path(dotbrain_home).resolve()
    if not (dotbrain_home / ".git").exists():
        raise RuntimeError(f"{dotbrain_home} is not a dotbrain git checkout")

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
    result.logs += offboard_brainspace(dotbrain_home, project, offboard, dry_run=dry_run, run=run)
    if offboard in {"archive", "delete"} and not dry_run:
        # the Brainspace is gone from projects/; a leftover entry would make
        # bootstrap try to hydrate a non-existent project
        removed = config.remove_project_beads(dotbrain_home, project)
        if removed:
            result.logs.append(removed)
    result.logs.append(
        f"unwired {project} (repo: {resolved_repo})\n"
        "repo edits are not committed; review and commit if wanted"
    )
    return result


def unwire_all_projects(
    dotbrain_home: Path,
    offboard: str = "keep",
    dry_run: bool = False,
    run: Runner = _default_run,
) -> list[UnwireResult]:
    """Unwire every project Brainspace. Continues on per-project failure.

    ``offboard`` defaults to ``keep`` (Brainspaces are not destroyed in batch
    mode). Mutually exclusive with ``--archive``/``--delete`` — use per-project
    ``unwire`` for destructive offboard.
    """
    dotbrain_home = Path(dotbrain_home).resolve()
    results: list[UnwireResult] = []
    for brainspace in paths.brainspaces(dotbrain_home):
        project = brainspace.name
        try:
            repo = repo_for_brainspace(brainspace, dotbrain_home)
            if repo and repo.is_dir():
                result = unwire_repo(repo, dry_run=dry_run)
            else:
                result = UnwireResult(project=project, repo=None)
            result.project = project
            result.logs += offboard_brainspace(
                dotbrain_home, project, offboard, dry_run=dry_run, run=run,
            )
            if offboard in {"archive", "delete"} and not dry_run:
                removed = config.remove_project_beads(dotbrain_home, project)
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
