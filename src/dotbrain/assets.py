"""Scoped asset reconciliation and local catalogs shared by CLI and lifecycle callers."""
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


def link_project(home: Path, target: projects.ProjectTarget, kind: str, runtime: str = "all", *, run=adopter_repos._default_run) -> skills.LinkResult:
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
        receiver = directory / kind
        if receiver.is_symlink() or (receiver.exists() and not receiver.is_dir()):
            raise ValueError(f"{receiver}: foreign asset directory conflicts with delivery")
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
        names = subagents.project_link_set(config.load_project_subagents(home, target.project))
        result = subagents.link_project_subagents(home, target.brainspace, workspaces, names, workspace_dirs=workspace_dirs)
    linked_entries = []
    for workspace in workspaces:
        directory = workspace_dirs[workspace] / ("skills" if kind == "skills" else "agents")
        if directory.is_dir():
            for entry in directory.iterdir():
                roots = (home / "skills", home / ".cache/skills") if kind == "skills" else (home / "agents", home / ".cache/agents")
                if kind == "skills" and cursor.owned(home):
                    roots += (cursor.plugin_dir(home),)
                if (entry.is_symlink() and any(skills._points_into(entry, root) for root in roots)) or (kind == "agents" and subagents.is_managed_copy(entry)):
                    linked_entries.append(f"{workspace}/{kind}/{entry.name}")
    if linked_entries or result.pruned:
        adopter_repos.reconcile_link_excludes(target.checkout, linked=tuple(linked_entries), pruned=tuple(result.pruned), run=run)
    return result


def detected_targets(user_home: Path) -> dict[str, str]:
    """Global skill targets of the installed runtimes that opt in by plugin copy, as seeded config lines."""
    targets = {}
    for rt in runtimes.RUNTIMES.values():
        if rt.home_env and runtimes.installed(rt):
            directory = HOME_DELIVERY[rt.name].skills_dir(runtimes.user_dir(rt, user_home))
            try:
                targets[rt.key] = "~/" + directory.relative_to(user_home).as_posix()
            except ValueError:  # relocated outside the home
                targets[rt.key] = str(directory)
    return targets


def global_targets(configured: dict[str, str], selected, kind: str, user_home: Path, *, explicit: bool) -> dict[str, str]:
    """Configured global targets, plus the home target of each opted-in relocatable runtime.

    Such a runtime (Hermes, OpenCode, Pi) is opted in by an explicit --runtime request or by an
    existing owned plugin copy, so later unfiltered runs keep its delivery current.
    """
    targets = dict(configured)
    for rt in selected:
        directory = runtimes.user_dir(rt, user_home)
        if (rt.home_env and rt.key not in targets and kind == "skills"
                and (explicit or HOME_DELIVERY[rt.name].owned(directory))):
            targets[rt.key] = str(HOME_DELIVERY[rt.name].skills_dir(directory))
    return targets


def link_global(home: Path, kind: str, runtime: str = "all", *, user_home: Path | None = None,
                run=hermes._default_run) -> skills.LinkResult:
    selected = runtimes.select(runtime)
    if kind == "agents" and runtime != "all" and not selected[0].subagents:
        raise ValueError(f"runtime '{runtime}' has no native subagent delivery")
    cfg = (skills.load_global_config(home / "skills/skills.yaml") if kind == "skills"
           else subagents.load_global_config(home))
    user_home = user_home or Path.home()
    targets = global_targets(cfg.targets, selected, kind, user_home, explicit=runtime != "all")
    if kind == "skills" and runtimes.find("cursor") in selected and (runtime == "cursor" or cursor.global_delivery(home)):
        targets.setdefault("cursor", str(user_home / ".cursor/skills"))
    known = [rt.key for rt in selected if kind == "skills" or rt.subagents]
    # Targets for runtimes this version does not recognize are skipped, not failed.
    keys = [k for k in targets if k in known] if runtime == "all" else known
    if any(k not in targets for k in keys):
        raise ValueError(f"runtime '{runtime}' has no configured global target")
    result = skills.LinkResult(notices=[f"unsupported global {kind} runtime skipped: {k}"
                                        for k in targets if runtime == "all" and k not in keys])
    if kind == "skills" and runtime == "all":
        # Installed but never set up: say how, rather than deliver unasked and undo a removal.
        result.notices += [f"{rt.label} is installed; run `dotbrain bootstrap --runtime {rt.name}` to deliver dotbrain to it"
                           for rt in selected if rt.home_env and rt.key not in targets and runtimes.installed(rt)]
    destinations = {k: adopter_repos.expand_path(targets[k], home=user_home) for k in keys}
    for dest in destinations.values():
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
    for k in keys:
        dest = destinations[k]
        if kind == "skills":
            linked = (cursor.deliver(home, dest, cfg.global_extra, scopes=(user_home,), global_scope=True) if k == "cursor" else
                      skills.link_into(home, dest, cfg.global_extra, label=k, prune_owned_only=True, preserve_collisions=True))
        else:
            linked = subagents.link_files_into(home, dest, [files[k] for files in resolved.values() if k in files],
                                               label=k, preserve_collisions=True, runtime=k)
        for field in ("linked", "pruned", "stashed", "warnings", "notices"):
            getattr(result, field).extend(getattr(linked, field))
        if kind == "skills" and k == "cursor":
            delivered_hooks = cursor.reconcile_hooks(user_home)
            result.linked += delivered_hooks.linked
            result.warnings += delivered_hooks.warnings
        rt = runtimes.find(k)
        if kind == "skills" and rt.home_env:
            # The plugin carries the Brain-coupled skills this runtime has no marketplace install for.
            delivered = HOME_DELIVERY[rt.name].deliver(runtimes.user_dir(rt, user_home), run=run)
            result.linked += delivered.linked
            result.warnings += delivered.warnings
    return result


def catalog(home: Path, kind: str, runtime: str = "all", project: str | None = None) -> list[dict]:
    wanted = runtimes.select(runtime)
    selected: set[str] = set()
    if project is not None:
        target = projects.select_projects(home, project=project)[0]
        selected = set(skills.resolve_selection(home, config.load_project_skills(home, target.project)) if kind == "skills" else
                       subagents.project_link_set(config.load_project_subagents(home, target.project)))
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
        names.update(subagents.PROJECT_BASELINE)
        for name in sorted(names):
            private = paths.confined_path(home / "agents", f"{directory}/{name}{suffix}")
            if subagents.plugin_delivered(name, k):
                source = f"plugin:dotbrain:{name}"
            elif subagents.is_packaged(name):
                source = f"bundled:agents/{directory}/{name}{suffix}"
            else:
                source = str(private)
            entry = entries.setdefault(name, {"name": name, "selected": name in selected, "sources": {}})
            entry["sources"][runtimes.find(k).name] = source
    return [entries[name] for name in sorted(entries)]
