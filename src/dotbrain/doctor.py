"""Read-only health checks with shared project selection and bounded probes."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dotbrain import adopter_repos, assets, beads, brainspaces, config, hermes, home_sync, opencode, paths, projects, resource_loader, runtimes, site, skills, subagents
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
    directory, suffix = subagents.runtime_spec()[runtime]
    if subagents.is_packaged(name):
        stem = subagents.delivered_stem(name, runtime)
        return (paths.confined_path(root, f".cache/agents/{directory}/{stem}{suffix}"),
                subagents.packaged_body(name, runtime))
    source = paths.confined_path(paths.confined_path(root, "agents"), f"{directory}/{name}{suffix}")
    if source.is_file():
        return source, source.read_text(encoding="utf-8")
    raise ValueError(f"subagent '{name}' has no definition for runtime '{runtime}'")


def _check_assets(root: Path, receiver: Path, selected: tuple[str, ...], kind: str, runtime: str) -> list[Finding]:
    if not selected:
        return [Finding("ok", f"{runtime}: no {kind} selected in this scope")]
    if receiver.is_symlink() or (receiver.exists() and not receiver.is_dir()):
        return [Finding("error", f"{receiver}: foreign asset directory", "preserve it and resolve the conflict before refresh")]
    findings = []
    for name in selected:
        if kind == "agents" and subagents.plugin_delivered(name, runtime):
            continue  # the plugin delivers it
        try:
            if kind == "skills":
                source = skills._resolve_skill_source(root, name)
                dest = receiver / Path(name).name
                healthy = source is not None and dest.is_symlink() and dest.resolve() == source.resolve() and dest.is_dir()
            else:
                source, body = _agent_source(root, name, runtime)
                dest = receiver / f"{subagents.delivered_stem(name, runtime)}{subagents.runtime_spec()[runtime][1]}"
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
    runtime_home = home / runtimes.find(runtime).workspace
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
                findings = [Finding("ok", f"{runtime}: registered dotbrain plugin has SessionStart hook files"),
                            Finding("info", f"{runtime}: hook trust, activation, and current session consumption are not verified", "inspect runtime hooks and start a new session after enabling them")]
                # Linking leaves packaged Claude Code agents to the plugin, so an older plugin leaves them undelivered.
                missing = [name for name in subagents.PROJECT_BASELINE if subagents.plugin_delivered(name, runtime)
                           and not (Path(location).expanduser() / "agents" / f"{name}.md").is_file()]
                if missing:
                    findings.append(Finding("warn", f"{runtime}: registered dotbrain plugin lacks packaged agents: {', '.join(missing)}",
                                            "update the dotbrain plugin"))
                return findings
        return [Finding("warn", f"{runtime}: registered dotbrain SessionStart hook files not found", "repair the dotbrain plugin installation")]
    except DIAGNOSIS_ERRORS as exc:
        return [Finding("warn", f"{runtime}: plugin installation check unavailable: {exc}", "inspect the runtime plugin manager")]


def _check_machine(root: Path, home: Path) -> list[Finding]:
    findings = [_check_binary("git"), _check_dotbrain_config(root), _check_templates(root)]
    if not root.is_dir():
        findings.append(Finding("error", "private data root does not exist", "run dotbrain bootstrap"))
    configured: set[str] = set()  # runtimes with a configured global target
    for kind in ("skills", "agents"):
        try:
            cfg = skills.load_global_config(root / "skills/skills.yaml") if kind == "skills" else subagents.load_global_config(root)
            selected = skills.resolve_selection(root, cfg.global_extra) if kind == "skills" else cfg.global_names
            configured.update(cfg.targets)
            targets = assets.global_targets(cfg.targets, runtimes.RUNTIMES.values(), kind, home, explicit=False)
            for runtime, destination in targets.items():
                recognized = runtimes.find(runtime)
                if recognized is None or recognized.key != runtime or (kind == "agents" and not recognized.subagents):
                    # A newer dotbrain sharing this home may know it; delivery skips it.
                    findings.append(Finding("warn", f"unsupported global {kind} runtime skipped: {runtime}",
                                            "correct global asset targets or upgrade dotbrain"))
                    continue
                receiver = adopter_repos.expand_path(destination, home=home)
                findings.extend(_check_assets(root, receiver, selected, kind, runtime))
        except DIAGNOSIS_ERRORS as exc:
            findings.append(Finding("error", f"global {kind}: {exc}", "correct the global selection and run dotbrain bootstrap"))
    for rt in runtimes.RUNTIMES.values():
        if rt.hooks and not rt.home_env:
            findings.extend(_check_plugin(home, rt.key))
        # An owned copy or a configured global target both mean this machine expects the plugin;
        # that copy, current (and enabled, for Hermes), is also what delivers the session hooks.
        if rt.home_env and (rt.key in configured or assets.HOME_DELIVERY[rt.name].owned(runtimes.user_dir(rt, home))):
            directory = runtimes.user_dir(rt, home)
            findings.extend(_check_opencode_plugin(directory, home) if rt.name == "opencode"
                            else _check_home_plugin(rt, directory))
    return findings


def _check_opencode_plugin(config_dir: Path, home: Path) -> list[Finding]:
    """Presence and freshness of dotbrain's own delivery in the OpenCode config, and skill copies
    OpenCode would also find in directories the user keeps."""
    try:
        state = opencode.state(config_dir)
        if state in ("missing", "foreign"):
            return _opencode_absent(config_dir, state)
        target = opencode.plugin_file(config_dir)
        findings = [Finding("ok", f"opencode: dotbrain plugin, with its session hooks, and skills current at {target}") if state == "current"
                    else Finding("warn", f"opencode: dotbrain delivery is stale at {config_dir}",
                                 "run dotbrain bootstrap --runtime opencode")]
        findings.extend(Finding("warn", f"opencode: skill {name} is also at {other}; OpenCode loads one of the two at random",
                                f"remove {other}, or move it out of OpenCode's skill directories")
                        for name, other in opencode.duplicate_skills(config_dir, home))
        return findings
    except DIAGNOSIS_ERRORS as exc:
        return [Finding("warn", f"opencode: plugin check unavailable: {exc}", "inspect the OpenCode config directory")]


def _opencode_absent(config_dir: Path, state: str) -> list[Finding]:
    if state == "missing":
        return [Finding("warn", "opencode: dotbrain plugin is not delivered", "run dotbrain bootstrap --runtime opencode")]
    if state == "foreign":
        return [Finding("warn", f"opencode: {opencode.foreign_entry(config_dir)} is not dotbrain's",
                        "move it aside, then run dotbrain bootstrap --runtime opencode")]
    return []


def _check_home_plugin(rt: runtimes.Runtime, directory: Path) -> list[Finding]:
    """Presence and freshness of dotbrain's own copy in a runtime's home, and Hermes activation."""
    adapter = assets.HOME_DELIVERY[rt.name]
    target = adapter.plugin_dir(directory)
    try:
        state = adapter.state(directory)
        if state in ("missing", "foreign"):
            return _plugin_absent(rt, directory, state)
        hooks = ", with its session hooks," if rt.hooks else ""
        findings = [Finding("ok", f"{rt.name}: dotbrain {adapter.KIND} copy{hooks} current at {target}") if state == "current"
                    else Finding("warn", f"{rt.name}: dotbrain {adapter.KIND} copy is stale at {target}", "run dotbrain bootstrap")]
        if adapter is hermes and (activation := hermes.activation(directory)) != "enabled":
            findings.append(Finding("warn", f"hermes: dotbrain plugin is {activation}", f"run {hermes.ENABLE}"))
        return findings
    except DIAGNOSIS_ERRORS as exc:
        return [Finding("warn", f"{rt.name}: {adapter.KIND} check unavailable: {exc}", f"inspect {directory}")]


def _plugin_absent(rt: runtimes.Runtime, directory: Path, state: str) -> list[Finding]:
    adapter = assets.HOME_DELIVERY[rt.name]
    if state == "missing":
        return [Finding("warn", f"{rt.name}: dotbrain {adapter.KIND} is not delivered", f"run dotbrain bootstrap --runtime {rt.name}")]
    if state == "foreign":
        return [Finding("warn", f"{rt.name}: {adapter.plugin_dir(directory)} is not dotbrain's {adapter.KIND} copy",
                        f"move it aside, then run dotbrain bootstrap --runtime {rt.name}")]
    return []


def _check_home_project(rt: runtimes.Runtime, directory: Path, repo: Path | None, selected: tuple[str, ...]) -> list[Finding]:
    """Home delivery a project declaring the runtime relies on; freshness is a machine check."""
    adapter = assets.HOME_DELIVERY[rt.name]
    findings = []
    try:
        findings.extend(_plugin_absent(rt, directory, adapter.state(directory)))
        if repo is not None and repo.is_dir() and selected and not adapter.trusted(directory, repo):
            # Both runtimes read <checkout>/<workspace>/skills only from trusted project roots.
            findings.append(Finding("warn", f"{rt.name}: project skills load only from a trusted checkout",
                                    adapter.trust_hint(repo)))
    except DIAGNOSIS_ERRORS as exc:
        findings.append(Finding("warn", f"{rt.name}: delivery check unavailable: {exc}", f"inspect {directory}"))
    return findings


def _check_home_sync(root: Path, run: Runner) -> list[Finding]:
    """Home sync state from local Git metadata only: no fetch, no writes."""
    try:
        settings = config.load_config(root).sync
        if not settings.enabled:
            return [Finding("info", "home sync disabled (sync.enabled: false)")]
        if not (root / ".git").exists():
            return [Finding("info", "home sync inactive: the dotbrain home is not a Git repository",
                            "initialize Git in the dotbrain home to sync it")]
        # Only reads go through here, so the bounded doctor runner fits home sync's Git calls.
        git = lambda argv, *, cwd=None, env=None, **_: run(argv, cwd=cwd, check=False, timeout=PROBE_TIMEOUT, env=env)
        state = home_sync._state(git, root)
        blockers = home_sync._blockers(home_sync._git_dir(root, git), state)
        findings = [Finding("error", f"home sync blocked: {blocker} in the dotbrain home",
                            "finish or abort it with git in the dotbrain home, then run dotbrain sync")
                    for blocker in blockers]
        if not state.detached:  # a detached HEAD has no upstream to compare
            ahead = state.ahead
            if state.upstream is None:
                findings.append(Finding("info", "home sync: no remote configured; sync commits stay local",
                                        "set an upstream for the dotbrain home's branch to share it"))
            elif ahead:
                findings.append(Finding("info", f"home sync: {ahead} local commit{'' if ahead == 1 else 's'} waiting "
                                        f"to be pushed to {state.upstream}", "run dotbrain sync"))
            else:
                findings.append(Finding("ok", f"home sync: nothing waiting for {state.upstream} (as last fetched)"))
        listed = home_sync._git(git, root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout
        findings.extend(Finding("warn", f"home sync: open conflict copy {path}",
                                "reconcile it with the original file, then delete the copy")
                        for path in sorted(set(listed.split("\0")))
                        if ".sync-conflict-" in Path(path).name and (root / path).exists())
        findings.extend(Finding("warn", f"home sync: {path} is over the size limit and stays uncommitted",
                                "commit it yourself, ignore it, or raise sync.max-file-size")
                        for path in state.changed
                        if not home_sync._is_nested_repo(root, path) and home_sync._too_large(root, path, settings.max_file_size))
        return findings
    except DIAGNOSIS_ERRORS as exc:
        return [Finding("warn", f"home sync check unavailable: {exc}", "check Git in the dotbrain home")]


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


# The bd release dotbrain's tracker calls and closure rules were last qualified on.
QUALIFIED_BD = (1, 3, 1)


def _check_bd_version(brainspace: Path, run: Runner) -> Finding:
    qualified = ".".join(map(str, QUALIFIED_BD))
    try:
        response = run(["bd", "--readonly", "version"], cwd=brainspace, check=False, timeout=PROBE_TIMEOUT,
                       env=beads._beads_env(brainspace))
    except (OSError, subprocess.SubprocessError) as exc:
        return Finding("error", f"bd version unavailable: {exc}", "install bd")
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", response.stdout or "")
    if not match:
        return Finding("info", f"bd version unrecognized; dotbrain is qualified on bd {qualified}")
    found = tuple(int(part) for part in match.groups())
    if found < QUALIFIED_BD:
        return Finding("warn", f"bd {match.group(0)} is older than {qualified}, the version dotbrain is qualified on",
                       f"upgrade bd to {qualified} or later")
    return Finding("ok", f"bd {match.group(0)} (qualified on {qualified})")


def _check_beads_state(brainspace: Path, name: str, dotbrain_home: Path, *, run: Runner = _default_run) -> list[Finding]:
    declaration = config.load_project_config(dotbrain_home, name)
    if declaration.mode == "none":
        return [Finding("ok", "beads disabled (mode: none)")]
    if declaration.mode not in {"embedded", "server"}:
        return [Finding("error", f"unsupported beads mode: {declaration.mode}", "correct project.yaml")]
    beads = paths.confined_path(brainspace, ".beads")
    if not (beads / "metadata.json").is_file():
        return [Finding("error", ".beads not initialized", "run dotbrain beads sync for this project")]
    findings = [_check_bd_version(brainspace, run)]
    if declaration.mode == "server":
        findings.append(_probe(["bd", "--readonly", "dolt", "test"], brainspace, run, "beads server"))
    findings.append(_probe(["bd", "--readonly", "-C", str(brainspace), "ready"], brainspace, run, "bd ready"))
    return findings


def _check_project(target: projects.ProjectTarget, root: Path, run: Runner, *, skip_absent: bool = False,
                   home: Path | None = None) -> list[Finding]:
    findings = []
    beads = config.load_project_config(root, target.project)
    workspaces = assets.project_workspaces(root, target, "all")
    findings.extend(Finding("warn", message, "correct project.yaml agents or upgrade dotbrain")
                    for message in brainspaces.unknown_agent_warnings(target.brainspace, root))
    selected = skills.resolve_selection(root, config.load_project_skills(root, target.project))
    agents = subagents.project_link_set(config.load_project_subagents(root, target.project))
    if not (target.brainspace / ".brain").is_dir():
        findings.append(Finding("error", "Brain directory missing", "run dotbrain refresh"))
    repo = target.checkout
    if repo is None:
        findings.append(Finding("warn", paths.NO_CHECKOUT,
                                f"run dotbrain wire --project {target.project} from its repository, or archive the Brainspace"))
    elif not repo.is_dir() and skip_absent and not (target.brainspace / ".repo.local").is_file():
        # A shared .repo may name a checkout that lives only on another machine.
        findings.append(Finding("skip", "checkout not on this machine; checkout checks skipped",
                                "add .repo.local to check a checkout here"))
    elif not repo.is_dir():
        findings.append(Finding("error", f"registered checkout missing: {repo}", "correct .repo.local or .repo"))
    else:
        findings.extend(_check_brainspace_links(repo, target.brainspace))
        entries = ["/.brain"] + (["/.beads"] if beads.mode != "none" else [])
        for workspace in workspaces:
            directory = repo / workspace
            if directory.is_symlink() or not directory.is_dir():
                continue
            rt = runtimes.for_workspace(workspace)
            runtime = rt.key
            findings.extend(_check_assets(root, directory / "skills", selected, "skills", runtime))
            entries.extend(f"/{workspace}/skills/{Path(name).name}" for name in selected)
            if rt.subagents is None:
                continue
            findings.extend(_check_assets(root, directory / "agents", agents, "agents", runtime))
            entries.extend(f"/{workspace}/agents/{subagents.delivered_stem(name, runtime)}{rt.subagents[1]}"
                           for name in agents if not subagents.plugin_delivered(name, runtime))
        try:
            findings.extend(_check_repo_excludes(repo, tuple(entries), run=run))
        except DIAGNOSIS_ERRORS as exc:
            findings.append(Finding("error", f"Git exclusions unavailable: {exc}", "check Git metadata"))
        if paths.INJECT_ADOPTER_POINTER:
            findings.extend(_check_agent_pointer(repo))
    for workspace in workspaces:
        rt = runtimes.for_workspace(workspace)
        if rt.name == "opencode":
            config_dir = runtimes.user_dir(rt, home or Path.home())
            try:
                findings.extend(_opencode_absent(config_dir, opencode.state(config_dir)))
            except DIAGNOSIS_ERRORS as exc:
                findings.append(Finding("warn", f"opencode: delivery check unavailable: {exc}", "inspect the OpenCode config directory"))
        elif rt.home_env:
            findings.extend(_check_home_project(rt, runtimes.user_dir(rt, home or Path.home()), repo, selected))
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
    report = DoctorReport(machine=_check_machine(root, home or Path.home()) + _check_home_sync(root, run), projects=errors)
    if all_projects and not targets and not errors:
        report.machine.append(Finding("warn", "no registered projects", "create a project with dotbrain wire"))
    for target in targets:
        report.checkouts[target.project] = str(target.checkout) if target.checkout else None
        try:
            report.projects[target.project] = _check_project(target, root, run, skip_absent=all_projects, home=home)
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
            item.findings.append({"severity": {"ok": "info", "info": "info", "skip": "info", "warn": "warning", "error": "error"}[finding.status], "message": message})
        if any(f.status == "error" for f in findings):
            item.status = "failure"
        elif any(f.status == "skip" for f in findings):
            item.status = "skipped"
        result.targets.append(item)
    failures = sum(item.status == "failure" for item in result.targets)
    if failures:
        result.status = "failure" if failures == len(result.targets) else "partial"
    return result
