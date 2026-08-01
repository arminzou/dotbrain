"""Read-only health check for dotbrain: machine readiness, project wiring, beads drift.

Self-contained diagnostic module. No filesystem mutations — pure inspections only.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from dotbrain import config, paths, resource_loader
from dotbrain.adopter_repos import is_dotbrain_repo
from dotbrain.brainspaces import _hook_command_present
from dotbrain.bootstrap import _global_hook_command

# Same shape as bootstrap.Runner; injected so tests can record without real subprocess calls.
Runner = Callable[..., subprocess.CompletedProcess[str]]


def _default_run(
    argv: list[str], *, cwd: Path | None = None, check: bool = True, timeout: int | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv, cwd=cwd, check=check, capture_output=True, encoding="utf-8", timeout=timeout,
    )


@dataclass
class Finding:
    status: str       # "ok", "warn", "error"
    message: str
    suggestion: str = ""


@dataclass
class DoctorReport:
    machine: list[Finding] = field(default_factory=list)
    projects: dict[str, list[Finding]] = field(default_factory=dict)


# --------------------------------------------------------------------------- machine readiness


def _check_binary(name: str) -> Finding:
    if shutil.which(name):
        return Finding("ok", f"{name} available")
    return Finding("error", f"{name} not found on PATH",
                   f"install {name} or add it to PATH")


def _check_binary_dolt() -> Finding:
    """dolt is a server-hosting dep (server host only), not a client requirement. Warn, not error."""
    if shutil.which("dolt"):
        return Finding("ok", "dolt available")
    return Finding("warn", "dolt not found on PATH",
                   "dolt is a server-host dependency; install only if this machine hosts beads")


def _check_dotbrain_config(root: Path) -> Finding:
    try:
        config.load_config(root)
    except Exception as exc:
        return Finding("error", f"config.yaml unreadable: {exc}",
                       "check config.yaml syntax")
    return Finding("ok", "config.yaml readable")


def _check_global_skills_config(root: Path) -> Finding:
    path = root / "skills" / "skills.yaml"
    if path.is_file():
        return Finding("ok", "operator skills config present")
    return Finding("ok", "using packaged required-core skills only")


def _check_templates(root: Path) -> Finding:
    if resource_loader.resource("templates/brain/AGENTS.md").is_file():
        return Finding("ok", "package templates/brain present")
    return Finding("error", "package templates/brain missing",
                   "installed package is missing bundled templates")


def _check_global_hook(home: Path, settings_rel: str, script_name: str,
                       dotbrain_home: Path, label: str) -> Finding:
    target = home / settings_rel
    if not target.is_file():
        return Finding("warn", f"{label} settings not found at {target}",
                       f"run 'dotbrain bootstrap' to install hooks")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return Finding("warn", f"{label} settings unreadable",
                       f"check {target} for syntax errors")
    if not isinstance(data, dict):
        return Finding("warn", f"{label} settings malformed")
    entries = data.get("hooks", {}).get("SessionStart", [])
    expected = _global_hook_command(script_name, dotbrain_home, home)
    if _hook_command_present(entries, expected):
        return Finding("ok", f"{label} SessionStart hook installed")
    return Finding("warn", f"{label} SessionStart hook missing",
                   f"run 'dotbrain bootstrap' or 'dotbrain wire --all'")


def _check_machine(root: Path, home: Path) -> list[Finding]:
    findings: list[Finding] = [
        _check_binary("bd"),
        _check_binary_dolt(),
        _check_dotbrain_config(root),
        _check_global_skills_config(root),
        _check_templates(root),
        _check_global_hook(home, ".claude/settings.json",
                          "claude-worktree-bootstrap.sh", root, "Claude"),
        _check_global_hook(home, ".codex/hooks.json",
                          "codex-worktree-bootstrap.sh", root, "Codex"),
    ]
    return findings


# --------------------------------------------------------------------------- project wiring


def _check_repo_file(brainspace: Path) -> tuple[Finding | None, Path | None]:
    """Returns (finding_or_None, resolved_repo_path_or_None).

    finding is None when the repo exists and is valid; the caller proceeds with wiring checks.
    resolved_repo_path is None for brain-only projects or when the target is missing.
    """
    repo_file = brainspace / ".repo"
    if not repo_file.is_file():
        return (Finding("error", f".repo file missing in {brainspace.name}",
                        "run 'dotbrain wire --repo <repo>' to wire a code repo"),
                None)
    content = repo_file.read_text(encoding="utf-8").strip()
    if content.startswith("(brain-only)"):
        return (Finding("ok", "brain-only project (no code repo)"), None)
    resolved = Path(content).expanduser().resolve() if content else None
    if not resolved or not resolved.is_dir():
        return (Finding("error", f".repo target not found: {content}",
                        f"update {brainspace.name}/.repo or run 'dotbrain wire'"),
                None)
    return (None, resolved)  # repo exists; wiring checks follow


def _check_brainspace_links(repo: Path, brainspace: Path) -> list[Finding]:
    findings: list[Finding] = []
    for name in paths.BRAINSPACE_LINKS:
        link = repo / name
        if not link.is_symlink():
            findings.append(Finding("warn", f"{repo}/{name} not wired",
                                     f"run 'dotbrain wire --repo {repo}'"))
            continue
        try:
            link.resolve(strict=True)
        except OSError:
            findings.append(Finding("error", f"{repo}/{name} broken symlink",
                                     f"run 'dotbrain wire --repo {repo}' to repair"))
    return findings


def _check_repo_excludes(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    present = paths.exclude_entries(repo)
    for entry in paths.EXCLUDE_ENTRIES:
        if entry not in present:
            findings.append(Finding("warn",
                                     f"{repo}/.git/info/exclude missing {entry}",
                                     f"run 'dotbrain wire --repo {repo}' to repair"))
    return findings


# Wire's idempotency marker in append_pointer_to_file: ".brain/AGENTS.md" substring.
# Doctor mirrors this so its "missing pointer" finding can actually be fixed by dotbrain wire.
_WIRE_POINTER_MARKER = ".brain/AGENTS.md"


def _check_agent_pointer(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    for name in ("AGENTS.md", "CLAUDE.md"):
        file = repo / name
        if not file.exists():
            continue
        try:
            target = file.resolve(strict=True) if file.is_symlink() else file
        except OSError:
            continue
        try:
            if _WIRE_POINTER_MARKER not in target.read_text(encoding="utf-8"):
                findings.append(Finding("warn",
                                         f"{file} missing dotbrain pointer",
                                         f"run 'dotbrain wire --repo {repo}' to repair"))
        except OSError:
            pass
    return findings


def _check_project_wiring(brainspace: Path, dotbrain_home: Path) -> list[Finding]:
    findings: list[Finding] = []

    repo_finding, resolved = _check_repo_file(brainspace)
    if repo_finding is not None:
        findings.append(repo_finding)
        if repo_finding.status == "error":
            return findings
    if resolved is None:
        return findings  # brain-only or repo target missing

    # The dotbrain repo itself isn't an adopter — skip wiring checks on it.
    if is_dotbrain_repo(resolved, dotbrain_home):
        return [Finding("ok", "dotbrain repo (not an adopter)")]

    findings += _check_brainspace_links(resolved, brainspace)
    findings += _check_repo_excludes(resolved)
    if paths.INJECT_ADOPTER_POINTER:
        findings += _check_agent_pointer(resolved)
    return findings


# --------------------------------------------------------------------------- beads state


def _check_beads_state(
    brainspace: Path, name: str, dotbrain_home: Path, *, run: Runner = _default_run,
) -> list[Finding]:
    findings: list[Finding] = []
    beads_cfg = config.load_project_config(dotbrain_home, name)

    if beads_cfg.mode == "none":
        return [Finding("ok", "beads disabled (mode: none)")]

    beads_dir = brainspace / ".beads"
    if not beads_dir.is_dir() or not (beads_dir / "metadata.json").is_file():
        return [Finding("warn", ".beads not initialized",
                        f"run 'dotbrain beads load --name {name}' or 'dotbrain wire --all'")]

    if beads_cfg.mode == "server":
        try:
            run(["bd", "dolt", "test"], cwd=brainspace, check=True, timeout=15)
            findings.append(Finding("ok", "beads server reachable"))
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip().splitlines()
            msg = detail[-1] if detail else "bd dolt test failed"
            findings.append(Finding("error", f"beads server unreachable: {msg}",
                                     "check beads.server.host in dotbrain.yaml"))
        except FileNotFoundError:
            findings.append(Finding("error", "bd not found; skipping beads connectivity check",
                                     "install bd to check beads server connectivity"))
        except subprocess.TimeoutExpired:
            findings.append(Finding("error", "beads server timed out",
                                     "check connectivity to beads server"))
    else:
        findings.append(Finding("ok", f"beads mode: {beads_cfg.mode}"))

    try:
        result = run(["bd", "-C", str(brainspace), "ready"], cwd=brainspace, check=False, timeout=15)
        if result.returncode != 0:
            msg = (result.stderr or "").strip().splitlines()
            snippet = msg[-1] if msg else "bd ready returned non-zero"
            findings.append(Finding("warn", f"bd ready failed: {snippet}",
                                     "beads tracker may need attention: bd doctor, bd dolt pull"))
        else:
            findings.append(Finding("ok", "bd ready responds"))
    except FileNotFoundError:
        findings.append(Finding("error", "bd not found; skipping beads check"))

    return findings


# --------------------------------------------------------------------------- orchestration


def run_doctor(
    dotbrain_home: Path, home: Path | None = None, *, run: Runner = _default_run,
) -> DoctorReport:
    home = Path(home) if home is not None else Path.home()
    root = dotbrain_home.resolve()

    report = DoctorReport(
        machine=_check_machine(root, home),
    )

    brainspaces = paths.brainspaces(root)
    if not brainspaces:
        report.machine.append(Finding("warn", f"no Brainspaces in {paths.data_dir(root).name}/",
                                       "create a project with 'dotbrain wire'"))
        return report

    for brainspace in brainspaces:
        name = brainspace.name
        findings: list[Finding] = []

        wiring_findings = _check_project_wiring(brainspace, root)
        findings += wiring_findings

        if shutil.which("bd"):
            findings += _check_beads_state(brainspace, name, root, run=run)

        if findings:
            report.projects[name] = findings

    return report
