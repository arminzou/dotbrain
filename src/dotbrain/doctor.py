"""Read-only health checks with shared project selection and bounded probes."""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dotbrain import adopter_repos, assets, beads, config, paths, projects, resource_loader, site, skills, subagents
from dotbrain.results import CommandResult, TargetResult

Runner = Callable[..., subprocess.CompletedProcess[str]]
PROBE_TIMEOUT = 15
DIAGNOSIS_ERRORS = (ValueError, TypeError, AttributeError, RuntimeError, OSError, UnicodeError, yaml.YAMLError, subprocess.SubprocessError)


def _default_run(argv, *, cwd=None, check=True, timeout=PROBE_TIMEOUT, env=None):
    return subprocess.run(list(argv), cwd=cwd, check=check, timeout=timeout, env=env,
                          capture_output=True, encoding="utf-8", stdin=subprocess.DEVNULL)


@dataclass
class Finding:
    status: str
    message: str
    suggestion: str = ""


@dataclass
class DoctorReport:
    machine: list[Finding] = field(default_factory=list)
    projects: dict[str, list[Finding]] = field(default_factory=dict)
    checkouts: dict[str, str | None] = field(default_factory=dict)


def _check_binary(name: str) -> Finding:
    return (Finding("ok", f"{name} available") if shutil.which(name) else
            Finding("error", f"{name} not found on PATH", f"install {name} or add it to PATH"))


def _check_dotbrain_config(root: Path) -> Finding:
    try:
        config.load_config(root)
        return Finding("ok", "config.yaml readable (defaults apply when absent)")
    except DIAGNOSIS_ERRORS as exc:
        return Finding("error", f"config.yaml unreadable: {exc}", "check config.yaml syntax")


def _check_templates(root: Path) -> Finding:
    return (Finding("ok", "package templates/brain present") if resource_loader.resource("templates/brain/AGENTS.md").is_file()
            else Finding("error", "package templates/brain missing", "reinstall dotbrain"))


def _agent_source(root: Path, name: str, runtime: str) -> tuple[Path, str]:
    """Expected link and content; packaged sources are read without writing cache."""
    paths.validate_project_name(name)
    directory, suffix = subagents.RUNTIME_SPEC[runtime]
    source = paths.confined_path(paths.confined_path(root, "agents"), f"{directory}/{name}{suffix}")
    if source.is_file():
        return source, source.read_text(encoding="utf-8")
    packaged = resource_loader.resource(f"agents/{directory}/{name}{suffix}")
    if not packaged.is_file():
        raise ValueError(f"subagent '{name}' has no definition for runtime '{runtime}'")
    return (paths.confined_path(root, f".cache/agents/{directory}/{name}{suffix}"),
            packaged.read_text(encoding="utf-8"))


def _check_assets(root: Path, receiver: Path, selected: tuple[str, ...], kind: str, runtime: str) -> list[Finding]:
    if not selected:
        return [Finding("ok", f"{runtime}: no {kind} selected in this scope")]
    if receiver.is_symlink() or (receiver.exists() and not receiver.is_dir()):
        return [Finding("error", f"{receiver}: foreign asset directory", "preserve it and resolve the conflict before refresh")]
    findings = []
    for name in selected:
        try:
            if kind == "skills":
                source = skills._resolve_skill_source(root, name)
                dest = receiver / Path(name).name
                healthy = source is not None and dest.is_symlink() and dest.resolve() == source.resolve() and dest.is_dir()
            else:
                source, body = _agent_source(root, name, runtime)
                dest = receiver / f"{name}{subagents.RUNTIME_SPEC[runtime][1]}"
                if runtime == "codex":
                    desired = subagents.GENERATED_NOTICE + "\n" + subagents.MANAGED_MARKER + "\n\n" + body
                    healthy = subagents.is_managed_copy(dest) and dest.read_text(encoding="utf-8") == desired
                else:
                    healthy = dest.is_symlink() and dest.resolve() == source.resolve() and dest.is_file() and dest.read_text(encoding="utf-8") == body
            if not healthy:
                findings.append(Finding("error", f"{dest}: selected {kind} delivery is missing, stale, or points to the wrong source", f"run dotbrain {kind} link in this scope"))
        except DIAGNOSIS_ERRORS as exc:
            findings.append(Finding("error", str(exc), "correct the selected asset source"))
    if not findings:
        findings.append(Finding("ok", f"{receiver}: {len(selected)} selected {kind} healthy"))
    return findings


def _check_plugin(home: Path, runtime: str) -> list[Finding]:
    runtime_home = home / (".claude" if runtime == "claude-code" else ".codex")
    registry = runtime_home / "plugins/installed_plugins.json"
    if not registry.is_file():
        return [Finding("info", f"{runtime}: plugin installation is not locally verified", "inspect the runtime plugin manager; current session consumption is unknown")]
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        entries = (data.get("plugins") or {}).get("dotbrain@dotbrain", [])
        if isinstance(entries, dict):
            entries = [entries]
        for entry in entries:
            location = entry.get("installPath") if isinstance(entry, dict) else None
            if not isinstance(location, str):
                continue
            hook_file = Path(location).expanduser() / "hooks/hooks.json"
            if not hook_file.is_file():
                continue
            hooks = json.loads(hook_file.read_text(encoding="utf-8"))
            if isinstance(hooks, dict) and (hooks.get("hooks") or {}).get("SessionStart"):
                return [Finding("ok", f"{runtime}: registered dotbrain plugin has SessionStart hook files"),
                        Finding("info", f"{runtime}: hook trust, activation, and current session consumption are not verified", "inspect runtime hooks and start a new session after enabling them")]
        return [Finding("warn", f"{runtime}: registered dotbrain SessionStart hook files not found", "repair the dotbrain plugin installation")]
    except DIAGNOSIS_ERRORS as exc:
        return [Finding("warn", f"{runtime}: plugin installation check unavailable: {exc}", "inspect the runtime plugin manager")]


def _check_machine(root: Path, home: Path) -> list[Finding]:
    findings = [_check_binary("git"), _check_dotbrain_config(root), _check_templates(root)]
    if not root.is_dir():
        findings.append(Finding("error", "private data root does not exist", "run dotbrain bootstrap"))
    for kind in ("skills", "agents"):
        try:
            cfg = skills.load_global_config(root / "skills/skills.yaml") if kind == "skills" else subagents.load_global_config(root)
            selected = skills.resolve_selection(root, cfg.global_extra) if kind == "skills" else cfg.global_names
            for runtime, destination in cfg.targets.items():
                if runtime not in subagents.RUNTIME_SPEC:
                    findings.append(Finding("error", f"unsupported global runtime: {runtime}", "correct global asset targets"))
                    continue
                receiver = adopter_repos.expand_path(destination, home=home)
                findings.extend(_check_assets(root, receiver, selected, kind, runtime))
        except DIAGNOSIS_ERRORS as exc:
            findings.append(Finding("error", f"global {kind}: {exc}", "correct the global selection and run dotbrain bootstrap"))
    for runtime in subagents.RUNTIME_SPEC:
        findings.extend(_check_plugin(home, runtime))
    return findings


def _check_brainspace_links(repo: Path, brainspace: Path) -> list[Finding]:
    root = brainspace.parents[1]
    beads = config.load_project_config(root, brainspace.name)
    findings = []
    for name in (".brain", *((".beads",) if beads.mode != "none" else ())):
        expected = paths.confined_path(brainspace, name)
        link = repo / name
        if not link.is_symlink() or link.resolve() != expected.resolve() or not expected.is_dir():
            findings.append(Finding("error", f"{link}: missing, broken, or points to the wrong Brainspace", "run dotbrain refresh for this checkout"))
    for workspace in assets.project_workspaces(root, projects.ProjectTarget(brainspace.name, brainspace, repo), "all"):
        directory = repo / workspace
        if directory.is_symlink() or not directory.is_dir():
            findings.append(Finding("error", f"{directory}: workspace is not a checkout-local directory", "run dotbrain refresh"))
    return findings


def _check_repo_excludes(repo: Path, entries: tuple[str, ...] = paths.EXCLUDE_ENTRIES, *, run: Runner = _default_run) -> list[Finding]:
    exclude = adopter_repos.git_exclude_file(repo, lambda argv, **kwargs: run(argv, timeout=PROBE_TIMEOUT, **kwargs))
    if exclude is None:
        return [Finding("error", f"{repo}: Git shared exclusion file could not be resolved", "check Git metadata")]
    present = set(exclude.read_text(encoding="utf-8").splitlines()) if exclude.is_file() else set()
    return [Finding("error", f"{exclude}: missing {entry}", "run dotbrain refresh") for entry in entries if entry not in present]


def _check_agent_pointer(repo: Path) -> list[Finding]:
    return [Finding("warn", f"{repo / name}: missing dotbrain pointer", "run dotbrain refresh")
            for name in ("AGENTS.md", "CLAUDE.md") if (repo / name).is_file()
            and ".brain/AGENTS.md" not in (repo / name).read_text(encoding="utf-8")]


def _check_brain_site(brainspace: Path, *, run: Runner = _default_run) -> list[Finding]:
    if not (brainspace / ".brain/site").is_dir():
        return []
    try:
        site.check_node(lambda argv, **kwargs: run(argv, timeout=PROBE_TIMEOUT, **kwargs))
        return [Finding("ok", "Brain site: Node available")]
    except (site.SiteError, OSError, subprocess.SubprocessError) as exc:
        return [Finding("warn", f"Brain site: {exc}", f"install Node {site.MIN_NODE_TEXT} or later to run dotbrain site")]


def _probe(argv: list[str], brainspace: Path, run: Runner, label: str) -> Finding:
    try:
        response = run(argv, cwd=brainspace, check=False, timeout=PROBE_TIMEOUT, env=beads._beads_env(brainspace))
        if response.returncode:
            lines = (response.stderr or response.stdout or "probe failed").strip().splitlines()
            return Finding("error", f"{label}: {lines[-1] if lines else 'probe failed'}", "check tracker configuration and connectivity")
        return Finding("ok", f"{label} responds in read-only mode")
    except subprocess.TimeoutExpired:
        return Finding("error", f"{label} timed out after {PROBE_TIMEOUT}s", "check tracker connectivity")
    except (OSError, subprocess.SubprocessError) as exc:
        return Finding("error", f"{label} unavailable: {exc}", "install bd and check tracker configuration")


def _check_beads_state(brainspace: Path, name: str, dotbrain_home: Path, *, run: Runner = _default_run) -> list[Finding]:
    declaration = config.load_project_config(dotbrain_home, name)
    if declaration.mode == "none":
        return [Finding("ok", "beads disabled (mode: none)")]
    if declaration.mode not in {"embedded", "server"}:
        return [Finding("error", f"unsupported beads mode: {declaration.mode}", "correct project.yaml")]
    beads = paths.confined_path(brainspace, ".beads")
    if not (beads / "metadata.json").is_file():
        return [Finding("error", ".beads not initialized", "run dotbrain beads sync for this project")]
    findings = []
    if declaration.mode == "server":
        findings.append(_probe(["bd", "--readonly", "dolt", "test"], brainspace, run, "beads server"))
    findings.append(_probe(["bd", "--readonly", "-C", str(brainspace), "ready"], brainspace, run, "bd ready"))
    return findings


def _check_project(target: projects.ProjectTarget, root: Path, run: Runner) -> list[Finding]:
    findings = []
    beads = config.load_project_config(root, target.project)
    workspaces = assets.project_workspaces(root, target, "all")
    selected = skills.resolve_selection(root, config.load_project_skills(root, target.project))
    agents = subagents.project_link_set(config.load_project_subagents(root, target.project))
    if not (target.brainspace / ".brain").is_dir():
        findings.append(Finding("error", "Brain directory missing", "run dotbrain refresh"))
    repo = target.checkout
    if repo is None:
        findings.append(Finding("ok", "Brain-only project: no checkout assets"))
    elif not repo.is_dir():
        findings.append(Finding("error", f"registered checkout missing: {repo}", "correct .repo.local or .repo"))
    else:
        findings.extend(_check_brainspace_links(repo, target.brainspace))
        entries = ["/.brain"] + (["/.beads"] if beads.mode != "none" else [])
        for workspace in workspaces:
            directory = repo / workspace
            if directory.is_symlink() or not directory.is_dir():
                continue
            runtime = subagents.WORKSPACE_RUNTIME[workspace]
            findings.extend(_check_assets(root, directory / "skills", selected, "skills", runtime))
            findings.extend(_check_assets(root, directory / "agents", agents, "agents", runtime))
            entries.extend(f"/{workspace}/skills/{Path(name).name}" for name in selected)
            entries.extend(f"/{workspace}/agents/{name}{subagents.RUNTIME_SPEC[runtime][1]}" for name in agents)
        try:
            findings.extend(_check_repo_excludes(repo, tuple(entries), run=run))
        except DIAGNOSIS_ERRORS as exc:
            findings.append(Finding("error", f"Git exclusions unavailable: {exc}", "check Git metadata"))
        if paths.INJECT_ADOPTER_POINTER:
            findings.extend(_check_agent_pointer(repo))
    findings.extend(_check_beads_state(target.brainspace, target.project, root, run=run))
    findings.extend(_check_brain_site(target.brainspace, run=run))
    return findings


def run_doctor(dotbrain_home: Path, home: Path | None = None, *, project: str | None = None,
               all_projects: bool = False, cwd: Path | None = None, run: Runner = _default_run) -> DoctorReport:
    root = Path(dotbrain_home).resolve()
    if all_projects and project is not None:
        raise ValueError("--all cannot be combined with --project")
    targets = []
    errors = {}
    bounded = lambda argv, **kwargs: run(argv, timeout=PROBE_TIMEOUT, **kwargs)
    if all_projects:
        for brainspace in paths.brainspaces(root):
            try:
                targets.extend(projects.select_projects(root, project=brainspace.name, run=bounded))
            except DIAGNOSIS_ERRORS as exc:
                errors[brainspace.name] = [Finding("error", f"project selection failed: {exc}", "correct project registration")]
    else:
        targets = projects.select_projects(root, project=project, cwd=cwd, run=bounded)
    report = DoctorReport(machine=_check_machine(root, home or Path.home()), projects=errors)
    if all_projects and not targets and not errors:
        report.machine.append(Finding("warn", "no registered projects", "create a project with dotbrain wire"))
    for target in targets:
        report.checkouts[target.project] = str(target.checkout) if target.checkout else None
        try:
            report.projects[target.project] = _check_project(target, root, run)
        except DIAGNOSIS_ERRORS as exc:
            report.projects[target.project] = [Finding("error", f"project diagnosis failed: {exc}", "correct the declaration or inaccessible paths")]
    return report


def as_result(report: DoctorReport) -> CommandResult:
    result = CommandResult("doctor")
    groups = [(None, "machine", report.machine)] + [(name, "project", findings) for name, findings in report.projects.items()]
    for name, scope, findings in groups:
        item = TargetResult(project=name, checkout=report.checkouts.get(name), scope=scope)
        for finding in findings:
            message = finding.message + (f"; {finding.suggestion}" if finding.suggestion else "")
            item.findings.append({"severity": {"ok": "info", "info": "info", "warn": "warning", "error": "error"}[finding.status], "message": message})
        if any(f.status == "error" for f in findings):
            item.status = "failure"
        result.targets.append(item)
    failures = sum(item.status == "failure" for item in result.targets)
    if failures:
        result.status = "failure" if failures == len(result.targets) else "partial"
    return result
