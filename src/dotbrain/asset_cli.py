"""Rendering adapter for scoped asset commands."""
import subprocess

import typer
import yaml

from dotbrain import assets, brainspaces, paths, projects, runtimes, skill_sources
from dotbrain.results import CommandResult, TargetResult, render


def report(kind, operation, home, runtime, project, json_output, scope="project", repo=None, all_projects=False,
           select=(), deselect=()):
    """List or link assets; ``select``/``deselect`` first change the scope's skills: selection."""
    result = CommandResult(f"{'subagents' if kind == 'agents' else kind} {operation}")
    exit_code = 1
    try:
        root = home.expanduser().resolve() if home else paths.resolve_dotbrain_home()
        runtimes.select(runtime)
        if operation == "list":
            rows = assets.catalog(root, kind, runtime, project)
            warnings = [] if project is None else brainspaces.unknown_agent_warnings(paths.brainspace(root, project), root)
            result.targets.append(TargetResult(project=project, scope="catalog", data={"assets": rows},
                                               findings=[{"severity": "warning", "message": m} for m in warnings]))
        else:
            if scope not in {"project", "global"}:
                raise ValueError("--scope must be project or global")
            if scope == "global" and (project is not None or repo is not None or all_projects):
                raise ValueError("--scope global conflicts with project selectors")
            if (select or deselect) and all_projects:
                raise ValueError("skill entries cannot be combined with --all; use --scope global for every project")
            targets = [None] if scope == "global" else projects.select_projects(root, project=project, repo=repo, all_projects=all_projects)
            for target in targets:
                if target is not None and runtime != "all":
                    try:
                        assets.project_workspaces(root, target, "all")
                    except (ValueError, OSError, yaml.YAMLError):
                        continue
                    assets.project_workspaces(root, target, runtime)
            for target in targets:
                item = TargetResult(project=target.project if target else None, checkout=str(target.checkout) if target and target.checkout else None, scope=scope)
                result.targets.append(item)
                try:
                    if target and target.checkout is None and all_projects:
                        item.findings.append({"severity": "warning", "message": paths.NO_CHECKOUT})
                        continue
                    if target is not None:
                        item.findings += [{"severity": "warning", "message": message}
                                          for message in brainspaces.unknown_agent_warnings(target.brainspace, root)]
                    if select or deselect:
                        item.changes += skill_sources.change_selection(
                            root, skill_sources.selection_file(root, target.brainspace if target else None),
                            add=tuple(select), remove=tuple(deselect))
                    linked = assets.link_global(root, kind, runtime) if target is None else assets.link_project(root, target, kind, runtime)
                    item.changes += [f"delivered {name}" for name in linked.linked] + [f"pruned {name}" for name in linked.pruned]
                    item.errors.extend(linked.warnings)
                    item.findings += [{"severity": "warning", "message": m} for m in linked.notices]
                    if item.errors:
                        item.status = "failure"
                except (ValueError, RuntimeError, OSError, yaml.YAMLError, subprocess.SubprocessError) as exc:
                    item.status = "failure"
                    item.errors.append(str(exc))
            failures = sum(item.status == "failure" for item in result.targets)
            if failures:
                result.status = "failure" if failures == len(result.targets) else "partial"
    except (ValueError, RuntimeError, OSError, yaml.YAMLError, subprocess.SubprocessError) as exc:
        result.status = "failure"
        result.errors.append(str(exc))
        exit_code = 2 if isinstance(exc, ValueError) else 1
    render(result, json_output=json_output)
    if result.status != "success":
        raise typer.Exit(exit_code)
