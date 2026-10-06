"""User-facing workflows that compose the concept modules (stage 5).

These are the bodies behind ``dotbrain wire``, ``refresh``, and ``unwire``:
cross-concept orchestration that stitches together ``adopter_repos`` (repo links),
``brainspaces`` (Brain/workspace preparation), ``beads`` (tracker init), ``skills``
(skill manifest). ``cli.py`` stays a thin Typer parsing/rendering
layer over these.

The subprocess seams take an injected ``run`` callable so tests record argv instead of invoking
``bd``/``git``.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dotbrain import assets, projects as project_selection, adopter_repos, beads, bootstrap, config, brainspaces, paths, skills, subagents
from dotbrain.adopter_repos import UnwireResult, unwire_repo
from dotbrain.results import TargetResult

# A subprocess seam: same shape as ``subprocess.run`` but easy to fake in tests.
Runner = Callable[..., "subprocess.CompletedProcess[str]"]


def _default_run(
    argv: Sequence[str], *, cwd: Path | None = None, env: dict | None = None, check: bool = True,
    timeout: int | None = None,
) -> "subprocess.CompletedProcess[str]":
    # stdin=DEVNULL is load-bearing: bd auto-enables non-interactive mode on a non-TTY stdin,
    # so destructive steps (e.g. bd init --reinit-local) skip their confirmation prompt instead
    # of blocking forever on terminal input while capture_output swallows the prompt text.
    return subprocess.run(
        list(argv), cwd=cwd, env=env, check=check,
        capture_output=True, encoding="utf-8", stdin=subprocess.DEVNULL,
        timeout=timeout,
    )


@dataclass
class WireResult:
    brainspace: Path
    repo: Path | None = None
    project: str = ""
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class RefreshResult:
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    refreshed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    targets: list[TargetResult] = field(default_factory=list)


def _tracker_changes(synced) -> list[str]:
    return list(dict.fromkeys([*synced.logs, *(entry for target in synced.targets
                    if target['status'] != 'skipped' for entry in target['changes'])]))


def project_workspace_dirs(
    brainspace: Path,
    repo: Path | None,
    workspaces: Sequence[str],
    run: Runner = _default_run,
) -> tuple[dict[str, Path], list[str]]:
    """Resolve runtime workspace directories, materializing them in the adopter repo."""
    directories: dict[str, Path] = {}
    warnings: list[str] = []
    for workspace in workspaces:
        if repo is not None:
            warning = adopter_repos.materialize_workspace(repo, brainspace, workspace, run)
            if warning:
                warnings.append(warning)
                continue
            directories[workspace] = repo / workspace
        else:
            directories[workspace] = brainspace / workspace
    return directories, warnings


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
    run: Runner = _default_run,
) -> WireResult:
    """Create/repair a Brainspace and wire an adopter repo. Mirrors wire-project.sh's main()."""
    dotbrain_home = Path(dotbrain_home).resolve()
    if not (dotbrain_home / ".git").exists():
        raise RuntimeError(f"{dotbrain_home} is not a dotbrain git checkout")

    resolved_repo: Path | None
    if no_repo:
        if repo is not None:
            raise ValueError("--no-repo cannot be combined with --repo")
        if not project:
            raise ValueError("--no-repo requires --project <name>")
        resolved_repo = None
    else:
        resolved_repo = adopter_repos.repo_root(repo, run)
        adopter_repos.ensure_not_wired_to_foreign_dotbrain(resolved_repo, dotbrain_home)
        if (resolved_repo / ".brain").is_symlink():
            wired = project_selection._wired(dotbrain_home, resolved_repo)
            if project is not None and project != wired.project:
                raise ValueError("--project does not match this checkout's Brainspace")
            project = wired.project

    parent = adopter_repos.linked_worktree_parent(resolved_repo, run) if resolved_repo else None
    if parent is not None:
        main = project_selection.select_projects(dotbrain_home, repo=parent, run=run)[0]
        if project is not None and project != main.project:
            raise ValueError("--project does not match the main checkout's Brainspace")
        project = main.project
    project = project or resolved_repo.name

    brainspace = paths.brainspace(dotbrain_home, project)
    # Resolve identity and every managed destination before even root housekeeping:
    # rejecting a selector must not seed a phantom project or rewrite registration.
    paths.brainspace_link_targets(dotbrain_home, project)
    for relative in (".repo", ".repo.local", ".brain/project.yaml", ".claude", ".codex"):
        paths.confined_path(brainspace, relative)
    paths.confined_path(dotbrain_home, ".gitignore")
    if resolved_repo is not None:
        adopter_repos.ensure_wiring_matches(resolved_repo, dotbrain_home, project)
        for name in (".brain", ".beads"):
            entry = resolved_repo / name
            if entry.exists() and not entry.is_symlink():
                raise ValueError(f"{entry}: a user-owned entry conflicts with attachment")
    existing = brainspace.is_dir()
    if existing:
        legacy = brainspace / ".brain/agents/skills.yaml"
        if legacy.exists():
            raise RuntimeError(f"{legacy}: move skills into .brain/project.yaml before wiring")
        # Resolve complete asset selections before converting an owned workspace link.
        workspaces = assets.project_workspaces(dotbrain_home,
                     project_selection.ProjectTarget(project, brainspace, resolved_repo), "all")
        try:
            skills.resolve_selection(dotbrain_home, config.load_project_skills(dotbrain_home, project))
        except ValueError as exc:
            if str(exc).startswith(("skill not found:", "skill folder contains no skills:")):
                raise RuntimeError(str(exc)) from exc
            raise
        runtimes = [subagents.WORKSPACE_RUNTIME[ws] for ws in workspaces]
        errors = subagents.validate_selection(dotbrain_home,
                    subagents.project_link_set(config.load_project_subagents(dotbrain_home, project)), runtimes)
        if errors:
            raise RuntimeError("; ".join(errors))
    rel = paths.data_dir(dotbrain_home).name
    bootstrap.ensure_root_gitignore(dotbrain_home)
    brainspace.mkdir(parents=True, exist_ok=True)
    if no_repo and not existing:
        (brainspace / ".repo").write_text(
            "(brain-only)\n", encoding="utf-8", newline="\n"
        )
    elif not existing:
        assert resolved_repo is not None
        (brainspace / ".repo").write_text(
            f"{adopter_repos.abbrev_home(resolved_repo, home)}\n",
            encoding="utf-8",
            newline="\n",
        )
    elif parent is None and resolved_repo is not None and adopter_repos.repo_for_brainspace(brainspace, dotbrain_home) is None:
        pointer = brainspace / (".repo.local" if (brainspace / ".repo.local").exists() else ".repo")
        paths.confined_path(brainspace, pointer.name)
        pointer.write_text(f"{adopter_repos.abbrev_home(resolved_repo, home)}\n", encoding="utf-8", newline="\n")

    result = WireResult(brainspace=brainspace, repo=resolved_repo, project=project)
    missing_links = [name for name in paths.BRAINSPACE_LINKS
                     if resolved_repo is not None and not (resolved_repo / name).is_symlink()]
    changed_workspaces = [name for name in brainspaces.active_agent_workspaces(brainspace, dotbrain_home)
                          if resolved_repo is not None and
                          ((resolved_repo / name).is_symlink() or not (resolved_repo / name).exists())]

    if parent is None:
        result.logs += [f"shared Brain: updated {relative}" for relative in brainspaces.seed_brain(brainspace, dotbrain_home)]
    active_workspaces = brainspaces.active_agent_workspaces(brainspace, dotbrain_home)
    result.warnings += brainspaces.seed_agent_workspaces(brainspace, dotbrain_home, home)
    if resolved_repo is not None:
        workspace_dirs, workspace_warnings = project_workspace_dirs(brainspace, resolved_repo, active_workspaces, run)
        result.errors += workspace_warnings
        result.logs += [f"materialized {name}" for name in changed_workspaces if name in workspace_dirs]
        target = project_selection.ProjectTarget(project, brainspace, resolved_repo)
        if not result.errors:
            for kind in ("skills", "agents"):
                linked = assets.link_project(dotbrain_home, target, kind, run=run)
                result.errors += linked.warnings
                result.logs += [f"linked {entry}" for entry in linked.linked]
                result.logs += [f"pruned {entry}" for entry in linked.pruned]
    if existing and run_beads and parent is None:
        synced = beads.pull_beads_for_all(dotbrain_home, projects=[project], run=run)
        result.logs += _tracker_changes(synced)
        result.warnings += synced.warnings
        result.errors += synced.errors
    beads_log = None if existing else beads.init_beads(
        brainspace, project, dotbrain_home,
        run_beads=run_beads, remote=remote,
        server_host=server_host, server_port=server_port,
        server_user=server_user, database=database, run=run,
    )
    if beads_log:
        result.logs.append(beads_log)
    if run_beads and not existing:
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
    elif not existing and not run_beads:
        config.record_project_beads(dotbrain_home, project, config.ProjectBeads(mode="none"))
    if not existing:
        result.logs.append(f"created Brainspace at {rel}/{project}")

    if no_repo:
        return result

    assert resolved_repo is not None
    result.warnings += adopter_repos.wire_repo(
        resolved_repo,
        brainspace,
        dotbrain_home,
        run,
        skip_beads_link=config.load_project_config(dotbrain_home, project).mode == "none",
        workspace_links=(),
    )
    if paths.INJECT_ADOPTER_POINTER:
        result.warnings += adopter_repos.ensure_agent_context_pointer(resolved_repo)
    expected_links = (".brain",)
    if config.load_project_config(dotbrain_home, project).mode != "none" and (brainspace / ".beads").exists():
        expected_links += (".beads",)
    result.warnings += adopter_repos.verify_wiring(
        resolved_repo, run, expected_links=expected_links
    )
    result.logs += [f"attached {name}" for name in missing_links if (resolved_repo / name).is_symlink()]
    return result


# --------------------------------------------------------------------------- refresh


def _refresh_preflight(dotbrain_home, target, runtime, run):
    brain = paths.confined_path(target.brainspace, '.brain')
    if not brain.is_dir():
        raise RuntimeError(f'{brain}: missing Brain; use dotbrain wire before refresh')
    declaration = paths.confined_path(target.brainspace, '.brain/project.yaml')
    if not declaration.is_file():
        raise RuntimeError(f'{declaration}: missing project declaration; restore it before refresh')
    legacy = paths.confined_path(target.brainspace, '.brain/agents/skills.yaml')
    if legacy.exists():
        raise RuntimeError(f'{legacy}: move skills into .brain/project.yaml before refresh')
    workspaces = assets.project_workspaces(dotbrain_home, target, runtime)
    skills.resolve_selection(dotbrain_home, config.load_project_skills(dotbrain_home, target.project))
    names = subagents.project_link_set(config.load_project_subagents(dotbrain_home, target.project))
    errors = subagents.validate_selection(dotbrain_home, names,
                 [subagents.WORKSPACE_RUNTIME[ws] for ws in workspaces])
    if errors:
        raise RuntimeError('; '.join(errors))
    if target.checkout is None:
        return workspaces
    repo = target.checkout
    if not repo.is_dir():
        raise RuntimeError(f'{repo}: registered checkout is missing; restore it or update .repo.local')
    actual = adopter_repos.repo_root(repo, run)
    if actual != repo.resolve():
        raise RuntimeError(f'{repo}: registered path is not a Git checkout root')
    adopter_repos.ensure_wiring_matches(repo, dotbrain_home, target.project)
    for name in paths.BRAINSPACE_LINKS:
        entry = repo / name
        if entry.exists() and not entry.is_symlink():
            raise RuntimeError(f'{entry}: foreign entry conflicts with setup repair')
    for ws in workspaces:
        directory = repo / ws
        if directory.is_symlink():
            if directory.resolve() != (target.brainspace / ws).resolve():
                raise RuntimeError(f'{directory}: foreign workspace link conflicts with delivery')
        elif directory.exists() and not directory.is_dir():
            raise RuntimeError(f'{directory}: workspace is not a directory')
        for kind in ('skills', 'agents'):
            receiver = directory / kind
            if receiver.is_symlink() or (receiver.exists() and not receiver.is_dir()):
                raise RuntimeError(f'{receiver}: foreign asset directory conflicts with delivery')
    return workspaces


def refresh_projects(
    dotbrain_home: Path, *, project: str | None = None, all_projects: bool = False,
    runtime: str = 'all', cwd: Path | None = None, run: Runner = _default_run,
) -> RefreshResult:
    dotbrain_home = Path(dotbrain_home).resolve()
    if not (dotbrain_home / '.git').exists():
        raise RuntimeError(f'{dotbrain_home} is not a dotbrain git checkout')
    config.load_config(dotbrain_home)
    assets.runtime_key(runtime)
    targets = project_selection.select_projects(dotbrain_home, project=project,
                    all_projects=all_projects, cwd=cwd, run=run)
    # A runtime filter is an invocation constraint: reject it across the batch before writes.
    if runtime != 'all':
        for target in targets:
            try:
                assets.project_workspaces(dotbrain_home, target, 'all')
            except (ValueError, OSError, yaml.YAMLError):
                # Invalid declarations are isolated as target failures below; a valid
                # undeclared runtime remains an invocation error before any writes.
                continue
            assets.project_workspaces(dotbrain_home, target, runtime)
    result = RefreshResult()
    for selected in targets:
        target = TargetResult(project=selected.project,
                    checkout=str(selected.checkout) if selected.checkout else None,
                    data={'shared_brain_changes': [], 'shared_tracker_changes': [], 'checkout_changes': []})
        result.targets.append(target)
        try:
            workspaces = _refresh_preflight(dotbrain_home, selected, runtime, run)
            shared = brainspaces.seed_brain(selected.brainspace, dotbrain_home, create_missing=False)
            target.data['shared_brain_changes'] += shared
            target.changes += [f'shared Brain: updated {entry}' for entry in shared]
            if selected.checkout is not None:
                repo = selected.checkout
                for ws in workspaces:
                    was_local = (repo / ws).is_dir() and not (repo / ws).is_symlink()
                    warning = adopter_repos.materialize_workspace(repo, selected.brainspace, ws, run)
                    if warning:
                        raise RuntimeError(warning)
                    if not was_local:
                        target.data['checkout_changes'].append(f'materialized {ws}')
                for kind in ('skills', 'agents'):
                    linked = assets.link_project(dotbrain_home, selected, kind, runtime, run=run)
                    target.errors += linked.warnings
                    target.data['checkout_changes'] += [f'linked {entry}' for entry in linked.linked]
                    target.data['checkout_changes'] += [f'pruned {entry}' for entry in linked.pruned]
                before = {name: (repo / name).is_symlink() for name in paths.BRAINSPACE_LINKS}
                mode = config.load_project_config(dotbrain_home, selected.project).mode
                errors = adopter_repos.wire_repo(repo, selected.brainspace, dotbrain_home, run,
                            skip_beads_link=mode == 'none' or not (selected.brainspace / '.beads').exists())
                target.errors += errors
                target.data['checkout_changes'] += [f'attached {name}' for name, existed in before.items()
                                                    if not existed and (repo / name).is_symlink()]
            synced = beads.pull_beads_for_all(dotbrain_home, projects=[selected.project], run=run)
            target.errors += synced.errors
            tracker_changes = _tracker_changes(synced)
            target.data['shared_tracker_changes'] += tracker_changes
            target.changes += [f'shared tracker: {entry}' for entry in tracker_changes]
            target.findings += [{'severity': 'warning', 'message': entry} for entry in synced.warnings]
            # Hydration can create the execution store; attach it only after it succeeds.
            if selected.checkout is not None and not synced.errors:
                repo = selected.checkout
                mode = config.load_project_config(dotbrain_home, selected.project).mode
                missing = not (repo / '.beads').is_symlink()
                target.errors += adopter_repos.wire_repo(repo, selected.brainspace, dotbrain_home, run,
                                                        skip_beads_link=mode == 'none')
                if missing and (repo / '.beads').is_symlink():
                    target.data['checkout_changes'].append('attached .beads')
        except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, yaml.YAMLError) as exc:
            target.errors.append(str(exc))
        target.changes += [f'checkout: {entry}' for entry in target.data['checkout_changes']]
        if target.errors:
            target.status = 'partial' if target.changes else 'failure'
            result.errors += target.errors
        else:
            result.refreshed.append(selected.project)
        result.logs += target.changes
        result.warnings += [item['message'] for item in target.findings]
    return result


def refresh_project(dotbrain_home: Path, project: str, *, runtime: str = 'all',
                    run: Runner = _default_run) -> RefreshResult:
    return refresh_projects(dotbrain_home, project=project, runtime=runtime, run=run)


def unwire_project(
    *, dotbrain_home: Path, repo: Path | None = None, project: str | None = None,
    run: Runner = _default_run,
) -> UnwireResult:
    targets = project_selection.select_projects(dotbrain_home, project=project, repo=repo,
                                                require_checkout=True, run=run)
    target = targets[0]
    adopter_repos.ensure_wiring_matches(target.checkout, dotbrain_home, target.project)
    result = unwire_repo(target.checkout, dotbrain_home=dotbrain_home, run=run)
    result.project = target.project
    return result
