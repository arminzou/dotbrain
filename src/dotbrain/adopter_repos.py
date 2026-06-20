"""Adopter repo attachment, detachment, and Brainspace link reconciliation.

A Brainspace is a project's private context store; an adopter repo is an external checkout wired
into it. This module owns everything repo-facing:

- Brainspace link reconciliation (the symlink primitive shared by repo and worktree wiring);
- repo path resolution for a Brainspace (``repo_for_brainspace``);
- the foreign-dotbrain guards that refuse to hijack a repo already wired elsewhere;
- ``.git/info/exclude`` and agent-context pointer (AGENTS.md/CLAUDE.md) management;
- repo attachment (``wire_repo``), verification, and detachment (``unwire_repo``).

It depends only on ``paths``: every other concept module points into it, never the reverse.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from dotbrain import paths

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


# --------------------------------------------------------------------------- Brainspace links


@dataclass
class ReconcileResult:
    created: list[str] = field(default_factory=list)
    repaired: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    collisions: list[str] = field(default_factory=list)


def reconcile(directory: Path, targets: dict[str, Path]) -> ReconcileResult:
    """Reconcile a Brainspace link mapping into one directory."""
    directory = Path(directory)
    result = ReconcileResult()

    for name, target in targets.items():
        path = directory / name
        target = Path(target)
        target_str = str(target)

        if not target.exists():
            result.skipped.append(name)
            continue

        if path.is_symlink():
            if os.readlink(path) == target_str:
                continue
            path.unlink()
            path.symlink_to(target_str)
            result.repaired.append(name)
            continue

        if path.exists():
            result.collisions.append(name)
            continue

        path.symlink_to(target_str)
        result.created.append(name)

    return result


def reconcile_worktree(worktree_root: Path, run: Runner = subprocess.run) -> ReconcileResult:
    """Repair a worktree's Brainspace links so they point at the main checkout."""
    worktree_root = Path(worktree_root).resolve()
    if not (worktree_root / ".git").is_file():
        return ReconcileResult()

    try:
        result = run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=worktree_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return ReconcileResult()

    common_dir_raw = result.stdout.strip()
    common_dir = (
        Path(common_dir_raw)
        if Path(common_dir_raw).is_absolute()
        else (worktree_root / common_dir_raw).resolve()
    )
    main_root = common_dir.parent
    targets = {name: main_root / name for name in paths.BRAINSPACE_LINKS}
    return reconcile(worktree_root, targets)


# --------------------------------------------------------------------------- repo path resolution


def expand_path(raw: str, home: Path | None = None) -> Path:
    """Expand a tilde-prefixed path to absolute. Mirrors bootstrap.sh expand_path.

    Uses string offset (not pattern stripping) to avoid bash's tilde-in-pattern expansion bug.
    """
    h = Path(home) if home is not None else Path.home()
    if raw == "~":
        return h
    if raw.startswith("~/"):
        return h / raw[2:]
    return Path(raw)


def repo_for_brainspace(
    brainspace: Path,
    dotbrain_home: Path,
    repo_base: Path | None = None,
    home: Path | None = None,
) -> Path | None:
    """Resolve the adopter repo path for a Brainspace. Mirrors bootstrap.sh repo_for_brainspace.

    Resolution order:
    1. <brainspace>/.repo.local (machine-local override)
    2. <brainspace>/.repo (committed canonical pointer)
    3. dotbrain_home itself when brainspace.name == "dotbrain"
    4. repo_base/<brainspace.name> when the directory exists
    """
    for pointer_name in (".repo.local", ".repo"):
        pointer = brainspace / pointer_name
        if pointer.is_file():
            lines = [
                l.strip() for l in pointer.read_text().splitlines()
                if l.strip() and not l.strip().startswith("#")
            ]
            if lines:
                return expand_path(lines[0], home)
    if brainspace.name == "dotbrain":
        return Path(dotbrain_home).resolve()
    if repo_base:
        candidate = Path(repo_base) / brainspace.name
        if candidate.is_dir():
            return candidate
    return None


# --------------------------------------------------------------------------- pure helpers


def abbrev_home(path: Path, home: Path | None = None) -> str:
    """Render ``path`` with ``$HOME`` collapsed to ``~`` (mirrors the script's abbrev_home)."""
    home = Path(home) if home is not None else Path.home()
    path = Path(path)
    if path == home:
        return "~"
    try:
        return f"~/{path.relative_to(home)}"
    except ValueError:
        return str(path)


def is_dotbrain_repo(repo: Path, dotbrain_home: Path) -> bool:
    return Path(repo).resolve() == Path(dotbrain_home).resolve()


def target_is_outside_repo(repo: Path, path: Path) -> bool:
    """True when ``path`` resolves to a location outside ``repo`` (broken target -> inside)."""
    repo_real = Path(repo).resolve()
    try:
        target_real = Path(path).resolve(strict=True)
    except OSError:
        return False
    return repo_real != target_real and repo_real not in target_real.parents


def is_dotbrain_checkout(root: Path) -> bool:
    """True when ``root`` has the minimum structure expected of a dotbrain checkout."""
    root = Path(root).resolve()
    return (
        (root / ".git").exists()
        and any((root / d).is_dir() for d in paths.DATA_DIRS)
        and (root / "templates" / ".brain" / "AGENTS.md").is_file()
    )


def foreign_dotbrain_home_for_symlink(path: Path, link_name: str, dotbrain_home: Path) -> Path | None:
    """Return a foreign dotbrain root when ``path`` proves it already belongs to another checkout."""
    path = Path(path)
    if not path.is_symlink():
        return None
    try:
        target = path.resolve(strict=True)
    except OSError:
        return None
    if target.name != link_name:
        return None
    project_dir = target.parent
    data_dir = project_dir.parent
    if data_dir.name not in paths.DATA_DIRS:
        return None
    inferred_root = data_dir.parent.resolve()
    if inferred_root == Path(dotbrain_home).resolve():
        return None
    if not is_dotbrain_checkout(inferred_root):
        return None
    if target != paths.brainspace(inferred_root, project_dir.name) / link_name:
        return None
    return inferred_root


def ensure_not_wired_to_foreign_dotbrain(repo: Path, dotbrain_home: Path) -> None:
    """Refuse rewiring when an adopter Brainspace link already resolves into another dotbrain checkout."""
    repo = Path(repo)
    current_root = Path(dotbrain_home).resolve()
    for name in paths.BRAINSPACE_LINKS:
        link = repo / name
        foreign_root = foreign_dotbrain_home_for_symlink(link, name, current_root)
        if foreign_root is None:
            continue
        raise RuntimeError(
            f"{link} resolves into another dotbrain checkout at {foreign_root}; "
            f"unwire {repo} or repoint {name} before wiring it to {current_root}"
        )


def repo_root(repo: Path | None, run: Runner = _default_run) -> Path:
    cwd = Path(repo) if repo is not None else None
    argv = ["git", "rev-parse", "--show-toplevel"]
    try:
        res = run(argv, cwd=cwd, check=True)
    except subprocess.CalledProcessError:
        loc = str(cwd) if cwd else "current directory"
        raise ValueError(f"{loc} is not inside a git repository; run 'git init' first or use --no-repo --name <name>")
    return Path((res.stdout or "").strip()).resolve()


# --------------------------------------------------------------------------- excludes & symlinks


def ensure_exclude_line(exclude_file: Path, line: str) -> None:
    exclude_file = Path(exclude_file)
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_file.read_text().splitlines() if exclude_file.is_file() else []
    if line in existing:
        return
    body = (exclude_file.read_text() if exclude_file.is_file() else "")
    if body and not body.endswith("\n"):
        body += "\n"
    exclude_file.write_text(body + line + "\n")


def _git_dir(repo: Path, run: Runner) -> Path:
    res = run(["git", "-C", str(repo), "rev-parse", "--git-dir"], check=False)
    raw = (res.stdout or "").strip() if res.returncode == 0 else ""
    if not raw:
        return Path(repo) / ".git"
    git_dir = Path(raw)
    return git_dir if git_dir.is_absolute() else Path(repo) / git_dir


def ensure_local_exclude_line(repo: Path, line: str, run: Runner = _default_run) -> None:
    ensure_exclude_line(_git_dir(repo, run) / "info" / "exclude", line)


def ensure_symlink(repo: Path, name: str, target: Path) -> str | None:
    """Create/repair ``repo/name`` -> ``target``. Returns a warning if a real path is in the way."""
    path = Path(repo) / name
    target_str = str(target)
    if path.is_symlink():
        if os.readlink(path) == target_str:
            return None
        path.unlink()
    elif path.exists():
        return f"{path} exists and is not a symlink; leaving it unchanged"
    path.symlink_to(target_str)
    return None


def warn_if_tracked_external_symlink(repo: Path, name: str, run: Runner = _default_run) -> str | None:
    path = Path(repo) / name
    if not path.is_symlink() or not target_is_outside_repo(repo, path):
        return None
    res = run(["git", "-C", str(repo), "ls-files", "--error-unmatch", name], check=False)
    if res.returncode == 0:
        return f"{path} points outside {repo} but is tracked; remove it with git rm --cached {name}"
    return None


def append_pointer_to_file(file: Path, pointer: str) -> str | None:
    file = Path(file)
    if file.is_symlink():
        try:
            target = file.resolve(strict=True)
        except OSError:
            return f"{file} is a broken symlink; leaving it unchanged"
    else:
        target = file
    if not target.is_file():
        return f"{target} is not a regular file; leaving it unchanged"
    if "@.brain/CLAUDE.md" in target.read_text():
        return None
    with target.open("a") as handle:
        handle.write(f"\n{pointer}\n")
    return None


def ensure_agent_context_pointer(repo: Path, pointer: str = paths.ADOPTER_POINTER) -> list[str]:
    repo = Path(repo)
    agents = repo / "AGENTS.md"
    claude = repo / "CLAUDE.md"
    if not agents.exists() and not claude.exists():
        agents.write_text(f"{pointer}\n")
        return []

    warnings: list[str] = []
    seen: set[Path] = set()
    for file in (agents, claude):
        if not file.exists():
            continue
        if file.is_symlink():
            try:
                target = file.resolve(strict=True)
            except OSError:
                warnings.append(f"{file} is a broken symlink; leaving it unchanged")
                continue
        else:
            target = file
        if target in seen:
            continue
        seen.add(target)
        warning = append_pointer_to_file(file, pointer)
        if warning:
            warnings.append(warning)
    return warnings


# --------------------------------------------------------------------------- attach / verify


def wire_repo(
    repo: Path,
    brainspace: Path,
    dotbrain_home: Path,
    run: Runner = _default_run,
    *,
    skip_beads_link: bool = False,
    workspace_links: Sequence[str] = (".claude", ".codex"),
) -> list[str]:
    """Link active Brainspace symlinks into ``repo`` and add local excludes."""
    repo = Path(repo)
    ensure_not_wired_to_foreign_dotbrain(repo, dotbrain_home)
    use_local_excludes = not is_dotbrain_repo(repo, dotbrain_home)
    warnings: list[str] = []
    active_links: tuple[str, ...] = (".brain", *(workspace_links or ()))
    if not skip_beads_link:
        active_links += (".beads",)
    targets = {name: Path(brainspace) / name for name in active_links}
    result = reconcile(repo, targets)
    for name in result.skipped:
        warnings.append(f"{targets[name]} is missing; skipping {repo}/{name}")
    for name in result.collisions:
        warnings.append(f"{repo / name} exists and is not a symlink; leaving it unchanged")
    for name in targets:
        if use_local_excludes:
            ensure_local_exclude_line(repo, f"/{name}", run)
        tracked = warn_if_tracked_external_symlink(repo, name, run)
        if tracked:
            warnings.append(tracked)
    return warnings


def verify_wiring(repo: Path, run: Runner = _default_run, *, expected_links: Sequence[str] = paths.BRAINSPACE_LINKS) -> list[str]:
    repo = Path(repo)
    warnings: list[str] = []
    for name in expected_links:
        link = repo / name
        if not link.is_symlink():
            warnings.append(f"{repo}/{name} is not wired")
            continue
        try:
            link.resolve(strict=True)
        except OSError:
            warnings.append(f"{repo}/{name} is a broken symlink")
    if shutil.which("bd") and (repo / ".beads").is_dir():
        res = run(["bd", "-C", str(repo), "ready"], check=False)
        if res.returncode != 0:
            warnings.append(f"bd ready failed in {repo}")
    return warnings


# --------------------------------------------------------------------------- detach


@dataclass
class UnwireResult:
    project: str = ""
    repo: Path | None = None
    logs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _git_exclude_file(repo: Path) -> Path | None:
    """Return .git/info/exclude for a repo or worktree; None if the layout is unrecognised."""
    git_marker = repo / ".git"
    if git_marker.is_dir():
        return git_marker / "info" / "exclude"
    if git_marker.is_file():
        content = git_marker.read_text().strip()
        if content.startswith("gitdir: "):
            raw = content[len("gitdir: "):]
            git_dir = Path(raw) if Path(raw).is_absolute() else repo / raw
            return git_dir / "info" / "exclude"
    return None


def unwire_repo(repo: Path, dry_run: bool = False) -> UnwireResult:
    """Remove agent workspace symlinks, exclude entries, and the adopter-context pointer.

    With ``dry_run`` the repo is left untouched; logs report what would be removed.
    """
    result = UnwireResult(repo=repo)
    verb = "would remove" if dry_run else "removed"

    for name in paths.BRAINSPACE_LINKS:
        link = repo / name
        if link.is_symlink():
            if not dry_run:
                link.unlink()
            result.logs.append(f"{verb} symlink {name}")

    exclude = _git_exclude_file(repo)
    if exclude and exclude.is_file():
        lines = exclude.read_text().splitlines(keepends=True)
        filtered = [l for l in lines if l.rstrip("\n") not in paths.EXCLUDE_ENTRIES]
        if len(filtered) < len(lines):
            if not dry_run:
                exclude.write_text("".join(filtered))
            result.logs.append(f"{verb} Brainspace ignore rules from .git/info/exclude")

    for fname in ("AGENTS.md", "CLAUDE.md"):
        f = repo / fname
        if not f.exists() or f.is_symlink():
            continue
        text = f.read_text()
        pointer_lines = set(paths.ADOPTER_POINTER.strip().splitlines())
        if any(pl in text for pl in pointer_lines):
            if not dry_run:
                cleaned = "\n".join(
                    l for l in text.splitlines() if l.strip() not in pointer_lines
                ).strip()
                f.write_text(cleaned + "\n" if cleaned else "")
            result.logs.append(f"{verb} agent-context pointer from {fname}")

    return result
