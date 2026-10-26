"""Scoped asset reconciliation and local catalogs shared by CLI and lifecycle callers."""
import os
from pathlib import Path

from dotbrain import adopter_repos, config, cursor, hermes, opencode, paths, pi, projects, runtimes, skills, subagents

# The owned plugin delivery of each runtime that has no marketplace install.
HOME_DELIVERY = {"hermes": hermes, "opencode": opencode, "pi": pi, "cursor": cursor}


def machine_agents(home: Path) -> tuple[str, ...]:
    """Runtimes set up on this machine, by CLI presence or owned delivery."""
    # Cursor keeps its bundle in the data root; the others keep a plugin in their runtime home.
    return tuple(
        rt.name for rt in runtimes.RUNTIMES.values()
        if (HOME_DELIVERY[rt.name].owned(home if rt.name == "cursor" else runtimes.user_dir(rt, Path.home()))
            if rt.name in HOME_DELIVERY else runtimes.installed(rt))
    )


def project_agents(home: Path, name: str) -> tuple[str, ...]:
    """An explicit project list is exact; otherwise follow this machine's delivery."""
    return config.load_project_agents(home, name, defaults=machine_agents(home))


def project_workspaces(home: Path, target: projects.ProjectTarget, runtime: str) -> tuple[str, ...]:
    """Workspaces of the recognized declared runtimes; unrecognized declarations are skipped."""
    wanted = runtimes.select(runtime)
    declared = runtimes.recognized(project_agents(home, target.project))
    if runtime != "all" and wanted[0] not in declared:
        raise ValueError(f"runtime '{runtime}' is not declared for project '{target.project}'")
    return tuple(rt.workspace for rt in (declared if runtime == "all" else wanted))


def link_project(home: Path, target: projects.ProjectTarget, kind: str, runtime: str = "all", *, run=adopter_repos._default_run,
                 packaged: bool = False) -> skills.LinkResult:
    """Deliver project skills or custom subagents; ``packaged`` also reconciles packaged subagents."""
    workspaces = project_workspaces(home, target, runtime)
    if kind == "agents":
        # Only runtimes with native subagent delivery receive agents; skills go to every runtime.
        workspaces = tuple(ws for ws in workspaces if runtimes.for_workspace(ws).subagents)
        if runtime != "all" and not workspaces:
            raise ValueError(f"runtime '{runtime}' has no native subagent delivery")
    if target.checkout is None or not target.checkout.is_dir():
        raise ValueError(f"project '{target.project}' has no available checkout")
    adopter_repos.ensure_wiring_matches(target.checkout, home, target.project)
    workspace_dirs = {ws: target.checkout / ws for ws in workspaces}
    for ws, directory in workspace_dirs.items():
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError(f"{directory}: workspace must be a checkout-local directory; run dotbrain refresh to migrate legacy workspace links")
        receiver = (target.checkout / runtimes.for_workspace(ws).skill_path if kind == "skills"
                    else directory / kind)
        conflict = skills.project_directory_conflict(target.checkout, receiver.relative_to(target.checkout).as_posix())
        if conflict:
            raise ValueError(conflict)
    legacy = target.brainspace / ".brain/agents/skills.yaml"
    if kind == "skills" and legacy.exists():
        raise ValueError(f"{legacy}: legacy selection; move skills into .brain/project.yaml")
    if kind == "skills":
        other_workspaces = tuple(ws for ws in workspaces if ws != ".cursor")
        result = skills.link_project(home, target.brainspace, other_workspaces,
                                     config.load_project_skills(home, target.project), workspace_dirs=workspace_dirs)
        if ".cursor" in workspaces:
            cursor_result = cursor.deliver(home, workspace_dirs[".cursor"] / "skills",
                                           config.load_project_skills(home, target.project),
                                           scopes=(target.checkout, Path.home()))
            for field in ("linked", "pruned", "warnings", "notices"):
                getattr(result, field).extend(getattr(cursor_result, field))
    else:
        names = config.load_project_subagents(home, target.project)
        roles = config.load_project_packaged(home, target.project)[1] if packaged else None
        result = subagents.link_project_subagents(home, target.brainspace, workspaces, names,
                                                  workspace_dirs=workspace_dirs, packaged=roles)
    linked_entries = []
    for workspace in workspaces:
        relative = runtimes.for_workspace(workspace).skill_path if kind == "skills" else f"{workspace}/agents"
        directory = target.checkout / relative
        if directory.is_dir():
            for entry in directory.iterdir():
                roots = (home / "skills", home / ".cache/skills") if kind == "skills" else (home / "agents", home / ".cache/agents")
                if kind == "skills" and cursor.owned(home):
                    roots += (cursor.plugin_dir(home),)
                if (entry.is_symlink() and any(skills._points_into(entry, root) for root in roots)) or (kind == "agents" and subagents.is_managed_copy(entry)):
                    linked_entries.append(f"{relative}/{entry.name}")
    if linked_entries or result.pruned:
        adopter_repos.reconcile_link_excludes(target.checkout, linked=tuple(linked_entries), pruned=tuple(result.pruned), run=run)
    return result


def global_targets(configured: dict[str, str], selected, kind: str, user_home: Path, *, explicit: bool,
                   errors: list[str], dotbrain_home: Path,
                   profiles: dict[str, list[str]] | None = None,
                   notices: list[str] | None = None) -> dict[str, tuple[Path, ...]]:
    """Resolve global folders, including existing profiles, before any delivery or pruning.

    Such a runtime (Hermes, OpenCode, Pi) is opted in by an explicit --runtime request or by an
    existing owned plugin copy, so later unfiltered runs keep its delivery current.
    """
    targets = dict(configured)
    selected = tuple(selected)
    for rt in selected:
        if kind != "skills" or rt.name not in HOME_DELIVERY:
            continue
        directory = runtimes.user_dir(rt, user_home)
        owned = cursor.global_delivery(dotbrain_home) if rt.name == "cursor" else HOME_DELIVERY[rt.name].owned(directory)
        if not explicit and not owned:
            targets.pop(rt.key, None)
            continue
        destination = HOME_DELIVERY[rt.name].skills_dir(directory) if rt.home_env else user_home / ".cursor/skills"
        targets.setdefault(rt.key, str(destination))
    destinations = {key: (adopter_repos.expand_path(value, home=user_home),) for key, value in targets.items()}
    settings = {}
    for rt in selected:
        if rt.key not in ("claude-code", "codex"):
            continue
        default = runtimes.user_dir(rt, user_home)
        homes = [(default, f"default {rt.key} home")]
        legacy = adopter_repos.expand_path(configured.get(rt.key, f"~/{rt.workspace}/{kind}").replace("\\", "/"), home=user_home)
        if legacy.resolve() != (default / kind).resolve():
            homes.append((legacy.parent, f"{kind}.yaml targets.{rt.key}"))
            if notices is not None:
                notices.append(
                    f"{kind}.yaml targets.{rt.key}: retained custom target; proposed conversion: "
                    f"skills.yaml profiles.{rt.key}: [{str(legacy.parent)!r}]; "
                    "profiles deliver both skills and agents, so verify both selections on every machine before moving it"
                )
        homes.extend((adopter_repos.expand_path(value, home=user_home), f"skills.yaml profiles.{rt.key}")
                     for value in (profiles or {}).get(rt.key, ()))
        folders = []
        for directory, setting in homes:
            if directory != default and not directory.is_dir():
                continue
            folder = directory / kind
            folders.append(folder)
            settings[(rt.key, folder)] = setting
        destinations[rt.key] = tuple(folders)
    for rt in selected:
        # Every runtime dotbrain installs into keeps files in its home (Cursor: hooks.json), not only its skills folder.
        if rt.name in HOME_DELIVERY and rt.key in destinations:
            directory = runtimes.user_dir(rt, user_home)
            if paths.inside_wired_checkout(directory):
                errors.append(f"{rt.home_env or '~/' + rt.workspace}: {directory} is inside a wired checkout; "
                              "choose a runtime home outside it")
                destinations[rt.key] = ()
                continue
        safe = []
        for folder in destinations.get(rt.key, ()):
            # Check the home too: an asset symlink must not hide a checkout marker above it.
            if paths.inside_wired_checkout(folder.parent) or paths.inside_wired_checkout(folder):
                setting = settings.get((rt.key, folder), f"{kind}.yaml targets.{rt.key} / {rt.home_env or rt.workspace}")
                errors.append(f"{setting}: {folder} is inside a wired checkout; choose a global {kind} destination outside it")
            elif folder.resolve() not in {p.resolve() for p in safe}:
                safe.append(folder)
        if rt.key in destinations:
            destinations[rt.key] = tuple(safe)
    return destinations


def link_global(home: Path, kind: str, runtime: str = "all", *, user_home: Path | None = None,
                run=hermes._default_run, skip: tuple[str, ...] = ()) -> skills.LinkResult:
    selected = tuple(rt for rt in runtimes.select(runtime) if rt.name not in skip)
    if kind == "agents" and runtime != "all" and not selected[0].subagents:
        raise ValueError(f"runtime '{runtime}' has no native subagent delivery")
    cfg = (skills.load_global_config(home / "skills/skills.yaml") if kind == "skills"
           else subagents.load_global_config(home))
    profiles = cfg.profiles if kind == "skills" else skills.load_global_config(home / "skills/skills.yaml").profiles
    user_home = user_home or Path.home()
    notices = []
    errors = []
    targets = global_targets(cfg.targets, selected, kind, user_home, explicit=runtime != "all",
                             profiles=profiles, notices=notices, errors=errors, dotbrain_home=home)
    for name in skip:
        targets.pop(runtimes.find(name).key, None)
    known = [rt.key for rt in selected if kind == "skills" or rt.subagents]
    # Targets for runtimes this version does not recognize are skipped, not failed.
    keys = [k for k in targets if k in known] if runtime == "all" else known
    if any(k not in targets for k in keys):
        raise ValueError(f"runtime '{runtime}' has no configured global target")
    result = skills.LinkResult(warnings=errors, notices=notices + [f"unsupported global {kind} runtime skipped: {k}"
                                        for k in targets if runtime == "all" and k not in keys])
    if kind == "skills" and runtime == "all":
        # Installed but never set up: say how, rather than deliver unasked and undo a removal.
        result.notices += [f"{rt.label} is installed; run `dotbrain bootstrap --runtime {rt.name}` to deliver dotbrain to it"
                           for rt in selected if rt.name in HOME_DELIVERY and rt.key not in targets and runtimes.installed(rt)]
    destinations = [(k, dest) for k in keys for dest in targets[k]]
    for _, dest in destinations:
        if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
            result.warnings.append(f"{dest}: foreign asset directory conflicts with delivery")
            return result
    resolved = {}
    if kind == "agents":
        errors = subagents.validate_selection(home, cfg.global_names, keys)
        if errors:
            result.warnings.extend(errors)
            return result
        resolved = {name: subagents._resolve_subagent_files(home, name) for name in cfg.global_names}
    for k, dest in destinations:
        try:
            if kind == "skills":
                linked = (cursor.deliver(home, dest, cfg.global_extra, scopes=(user_home,), global_scope=True) if k == "cursor" else
                          skills.link_into(home, dest, cfg.global_extra, label=k, prune_owned_only=True, preserve_collisions=True))
            else:
                linked = subagents.link_files_into(home, dest, [files[k] for files in resolved.values() if k in files],
                                                   label=k, preserve_collisions=True, runtime=k)
        except ValueError as exc:  # a write refused inside a wired checkout stops this runtime only
            result.warnings.append(f"{k}: {exc}")
            continue
        for field in ("linked", "pruned", "stashed", "warnings", "notices"):
            getattr(result, field).extend(getattr(linked, field))
        if kind == "skills" and k == "cursor":
            delivered_hooks = cursor.reconcile_hooks(user_home)
            result.linked += delivered_hooks.linked
            result.warnings += delivered_hooks.warnings
        rt = runtimes.find(k)
        if kind == "skills" and rt.home_env:
            # The plugin carries the Brain-coupled skills this runtime has no marketplace install for.
            try:
                delivered = HOME_DELIVERY[rt.name].deliver(runtimes.user_dir(rt, user_home), run=run)
            except ValueError as exc:
                result.warnings.append(f"{k}: {exc}")
                continue
            result.linked += delivered.linked
            result.warnings += delivered.warnings
    return result


def catalog(home: Path, kind: str, runtime: str = "all", project: str | None = None) -> list[dict]:
    wanted = runtimes.select(runtime)
    selected: set[str] = set()
    if project is not None:
        target = projects.select_projects(home, project=project)[0]
        selected = set(skills.resolve_selection(home, config.load_project_skills(home, target.project)) if kind == "skills" else
                       config.load_project_subagents(home, target.project))
    if kind == "skills":
        skill_root = paths.confined_path(home, "skills")
        available = skills.discover_skills(skill_root)
        for name in available:
            paths.confined_path(skill_root, str(Path(name) / "SKILL.md"))
        return [{"name": name, "source": str(paths.confined_path(skill_root, name)),
                 "selected": name in selected, "runtimes": [rt.name for rt in wanted]}
                for name in available]
    entries: dict[str, dict] = {}
    for k, (directory, suffix) in subagents.runtime_spec().items():
        if runtimes.find(k) not in wanted:
            continue
        names = {p.stem for p in (home / "agents" / directory).glob(f"*{suffix}") if p.is_file()}
        for name in sorted(names):
            source = str(paths.confined_path(home / "agents", f"{directory}/{name}{suffix}"))
            entry = entries.setdefault(name, {"name": name, "selected": name in selected, "sources": {}})
            entry["sources"][runtimes.find(k).name] = source
    return [entries[name] for name in sorted(entries)]
