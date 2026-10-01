"""Read-only project selection and local discovery."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from dotbrain import adopter_repos, config, paths, skills


@dataclass(frozen=True)
class ProjectTarget:
    project: str
    brainspace: Path
    checkout: Path | None


def _named(home: Path, name: str) -> ProjectTarget:
    brainspace = paths.brainspace(home, name)
    if not brainspace.is_dir():
        raise ValueError(f"project {name!r} does not exist; use 'dotbrain projects list'")
    paths.confined_path(brainspace, ".brain")
    paths.confined_path(brainspace, ".beads")
    return ProjectTarget(name, brainspace, adopter_repos.repo_for_brainspace(brainspace, home))


def _wired(home: Path, checkout: Path) -> ProjectTarget:
    link = checkout / ".brain"
    if not link.is_symlink():
        raise ValueError(f"{checkout} is not wired; run 'dotbrain wire' first or select --project <name>")
    destination = link.resolve()
    name = destination.parent.name
    target = _named(home, name)
    expected = paths.confined_path(target.brainspace, ".brain")
    if destination != expected.resolve() or not destination.is_dir():
        raise ValueError(f"{link} conflicts with the selected data root or Brainspace")
    try:
        adopter_repos.ensure_wiring_matches(checkout, home, name)
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc
    return ProjectTarget(name, target.brainspace, checkout)


def select_projects(
    home: Path, *, project: str | None = None, repo: Path | None = None,
    all_projects: bool = False, cwd: Path | None = None, require_checkout: bool = False,
    run: adopter_repos.Runner = adopter_repos._default_run,
) -> list[ProjectTarget]:
    """Resolve all selectors before callers perform any mutation."""
    if all_projects and (project is not None or repo is not None):
        raise ValueError("--all cannot be combined with --project or --repo")
    if all_projects:
        targets = [_named(home, p.name) for p in paths.brainspaces(home)]
    elif repo is not None:
        target = _wired(home, adopter_repos.repo_root(repo, run))
        if project is not None and paths.validate_project_name(project) != target.project:
            raise ValueError("--project does not match the checkout's wired Brainspace")
        targets = [target]
    elif project is not None:
        targets = [_named(home, project)]
    else:
        targets = [_wired(home, adopter_repos.repo_root(cwd or Path.cwd(), run))]
    for target in targets:
        if require_checkout and (target.checkout is None or not target.checkout.is_dir()):
            raise ValueError(f"project {target.project!r} has no available checkout; select a wired --repo")
    return targets


def inspect_project(home: Path, target: ProjectTarget, *, expand_assets: bool = True) -> dict:
    """Report declarations and wiring without probing the tracker."""
    declaration_path = paths.confined_path(target.brainspace, ".brain/project.yaml")
    declarations = (yaml.safe_load(declaration_path.read_text(encoding="utf-8")) or {}
                    if declaration_path.is_file() else {})
    if not isinstance(declarations, dict):
        raise ValueError(f"{declaration_path}: expected a YAML mapping")
    beads = config.load_project_config(home, target.project)
    runtimes = config.load_project_agents(home, target.project)
    wiring: dict[str, str] = {}
    if target.checkout is not None:
        for name in (".brain", *((".beads",) if beads.mode != "none" else ())):
            link = target.checkout / name
            expected = paths.confined_path(target.brainspace, name)
            wiring[name] = ("healthy" if link.is_symlink() and link.resolve() == expected.resolve()
                            and expected.is_dir() else "conflict" if link.exists() or link.is_symlink()
                            else "missing")
    entries = config.load_project_skills(home, target.project)
    return {
        "project": target.project, "brainspace": str(target.brainspace),
        "checkout": str(target.checkout) if target.checkout is not None else None,
        "brain_only": target.checkout is None, "runtimes": list(runtimes),
        "paths": {"brain": str(paths.confined_path(target.brainspace, ".brain")),
                  "execution": str(paths.confined_path(target.brainspace, ".beads"))
                  if beads.mode != "none" else None,
                  "configuration": str(declaration_path)},
        "settings": {**declarations, "agents": list(runtimes), "beads": asdict(beads)},
        "beads": asdict(beads), "wiring": wiring,
        "skills": {"configured": list(entries),
                   **({"effective": list(skills.resolve_selection(home, entries))} if expand_assets else {})},
        "subagents": list(config.load_project_subagents(home, target.project)),
    }


def list_projects(home: Path) -> list[dict]:
    records = []
    for target in select_projects(home, all_projects=True):
        try:
            records.append(inspect_project(home, target, expand_assets=False))
        except (ValueError, RuntimeError, OSError, yaml.YAMLError) as exc:
            records.append({"project": target.project,
                            "checkout": str(target.checkout) if target.checkout else None,
                            "error": str(exc)})
    return records
