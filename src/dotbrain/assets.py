"""Scoped asset reconciliation and local catalogs shared by CLI and lifecycle callers."""
from pathlib import Path

from dotbrain import adopter_repos, config, paths, projects, resource_loader, skills, subagents


def runtime_key(runtime: str) -> str:
    if runtime not in {"claude", "codex", "all"}:
        raise ValueError("--runtime must be claude, codex, or all")
    return "claude-code" if runtime == "claude" else runtime


def project_workspaces(home: Path, target: projects.ProjectTarget, runtime: str) -> tuple[str, ...]:
    key = runtime_key(runtime)
    declared = config.load_project_agents(home, target.project)
    supported = {"claude": ".claude", "claude-code": ".claude", "codex": ".codex"}
    unknown = set(declared) - set(supported)
    if unknown:
        raise ValueError(f"unsupported declared runtimes: {', '.join(sorted(unknown))}")
    workspaces = tuple(dict.fromkeys(supported[item] for item in declared))
    wanted = ".claude" if key == "claude-code" else ".codex"
    if key != "all" and wanted not in workspaces:
        raise ValueError(f"runtime '{runtime}' is not declared for project '{target.project}'")
    return workspaces if key == "all" else (wanted,)


def link_project(home: Path, target: projects.ProjectTarget, kind: str, runtime: str = "all", *, run=adopter_repos._default_run) -> skills.LinkResult:
    workspaces = project_workspaces(home, target, runtime)
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
        result = skills.link_project(home, target.brainspace, workspaces,
                                     config.load_project_skills(home, target.project), workspace_dirs=workspace_dirs)
    else:
        names = subagents.project_link_set(config.load_project_subagents(home, target.project))
        result = subagents.link_project_subagents(home, target.brainspace, workspaces, names, workspace_dirs=workspace_dirs)
    linked_entries = []
    for workspace in workspaces:
        directory = workspace_dirs[workspace] / ("skills" if kind == "skills" else "agents")
        if directory.is_dir():
            for entry in directory.iterdir():
                roots = (home / "skills", home / ".cache/skills") if kind == "skills" else (home / "agents", home / ".cache/agents")
                if (entry.is_symlink() and any(skills._points_into(entry, root) for root in roots)) or (kind == "agents" and subagents.is_managed_copy(entry)):
                    linked_entries.append(f"{workspace}/{kind}/{entry.name}")
    if linked_entries or result.pruned:
        adopter_repos.reconcile_link_excludes(target.checkout, linked=tuple(linked_entries), pruned=tuple(result.pruned), run=run)
    return result


def link_global(home: Path, kind: str, runtime: str = "all", *, user_home: Path | None = None) -> skills.LinkResult:
    key = runtime_key(runtime)
    cfg = (skills.load_global_config(home / "skills/skills.yaml") if kind == "skills"
           else subagents.load_global_config(home))
    keys = [k for k in cfg.targets if k in subagents.RUNTIME_SPEC] if key == "all" else [key]
    if any(k not in cfg.targets for k in keys):
        raise ValueError(f"runtime '{runtime}' has no configured global target")
    result = skills.LinkResult()
    destinations = {k: adopter_repos.expand_path(cfg.targets[k], home=user_home or Path.home()) for k in keys}
    for dest in destinations.values():
        if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
            return skills.LinkResult(warnings=[f"{dest}: foreign asset directory conflicts with delivery"])
    resolved = {}
    if kind == "agents":
        errors = subagents.validate_selection(home, cfg.global_names, keys)
        if errors:
            return skills.LinkResult(warnings=errors)
        resolved = {name: subagents._resolve_subagent_files(home, name) for name in cfg.global_names}
    for k in keys:
        dest = destinations[k]
        if kind == "skills":
            linked = skills.link_into(home, dest, cfg.global_extra, label=k, prune_owned_only=True, preserve_collisions=True)
        else:
            linked = subagents.link_files_into(home, dest, [files[k] for files in resolved.values()],
                                               label=k, preserve_collisions=True, runtime=k)
        for field in ("linked", "pruned", "stashed", "warnings"):
            getattr(result, field).extend(getattr(linked, field))
    return result


def catalog(home: Path, kind: str, runtime: str = "all", project: str | None = None) -> list[dict]:
    key = runtime_key(runtime)
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
                 "selected": name in selected, "runtimes": ["claude", "codex"] if key == "all" else [runtime]}
                for name in available]
    entries: dict[str, dict] = {}
    for k, (directory, suffix) in subagents.RUNTIME_SPEC.items():
        if key != "all" and key != k:
            continue
        names = {p.stem for p in (home / "agents" / directory).glob(f"*{suffix}") if p.is_file()}
        bundled = resource_loader.resource(f"agents/{directory}")
        names.update(Path(p.name).stem for p in bundled.iterdir() if p.is_file() and p.name.endswith(suffix))
        for name in sorted(names):
            private = paths.confined_path(home / "agents", f"{directory}/{name}{suffix}")
            source = str(private) if private.is_file() else f"bundled:agents/{directory}/{name}{suffix}"
            entry = entries.setdefault(name, {"name": name, "selected": name in selected, "sources": {}})
            entry["sources"]["claude" if k == "claude-code" else k] = source
    return [entries[name] for name in sorted(entries)]
