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
        capture_output=True, encoding="utf-8", stdin=subprocess.DEVNULL,
    )


# --------------------------------------------------------------------------- Brainspace links


@dataclass
class ReconcileResult:
    created: list[str] = field(default_factory=list)
    repaired: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    collisions: list[str] = field(default_factory=list)


def _symlink_directory(path: Path, target_str: str) -> None:
    """Create a directory symlink at ``path`` or raise a clear privilege failure."""
    try:
        path.symlink_to(target_str, target_is_directory=True)
    except OSError as exc:
        message = paths.symlink_privilege_message(exc)
        if message is None:
            raise
        raise RuntimeError(f"{path}: {message}") from exc


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
            if paths.symlink_target_matches(os.readlink(path), target_str):
                continue
            path.unlink()
            _symlink_directory(path, target_str)
            result.repaired.append(name)
            continue

        if path.exists():
            result.collisions.append(name)
            continue

        _symlink_directory(path, target_str)
        result.created.append(name)

    return result


def reconcile_worktree(worktree_root: Path, run: Runner = _default_run) -> ReconcileResult:
    """Repair a worktree's Brainspace links so they point at the main checkout."""
    worktree_root = Path(worktree_root).resolve()
    if not (worktree_root / ".git").is_file():
        return ReconcileResult()

    try:
        result = run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=worktree_root,
            check=True,
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
    if raw.startswith(("~/", "~\\")):
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
                l.strip() for l in pointer.read_text(encoding="utf-8").splitlines()
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
        return f"~/{path.relative_to(home).as_posix()}"
    except ValueError:
        return path.as_posix()


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
    existing = (
        exclude_file.read_text(encoding="utf-8").splitlines()
        if exclude_file.is_file()
        else []
    )
    if line in existing:
        return
    body = exclude_file.read_text(encoding="utf-8") if exclude_file.is_file() else ""
    if body and not body.endswith("\n"):
        body += "\n"
    exclude_file.write_text(body + line + "\n", encoding="utf-8", newline="\n")


def remove_exclude_line(exclude_file: Path, line: str) -> None:
    exclude_file = Path(exclude_file)
    if not exclude_file.is_file():
        return
    lines = exclude_file.read_text(encoding="utf-8").splitlines(keepends=True)
    filtered = [existing for existing in lines if existing.rstrip("\r\n") != line]
    if len(filtered) != len(lines):
        exclude_file.write_text("".join(filtered), encoding="utf-8", newline="\n")


def git_exclude_file(repo: Path, run: Runner = _default_run) -> Path | None:
    """Return the shared exclude file used by a repo and all its worktrees."""
    res = run(["git", "-C", str(repo), "rev-parse", "--git-common-dir"], check=False)
    raw = (res.stdout or "").strip() if res.returncode == 0 else ""
    if not raw:
        return None
    common_dir = Path(raw)
    if not common_dir.is_absolute():
        common_dir = Path(repo) / common_dir
    return common_dir.resolve() / "info" / "exclude"


def ensure_local_exclude_line(repo: Path, line: str, run: Runner = _default_run) -> None:
    exclude_file = git_exclude_file(repo, run)
    if exclude_file is not None:
        ensure_exclude_line(exclude_file, line)


def remove_local_exclude_line(repo: Path, line: str, run: Runner = _default_run) -> None:
    exclude_file = git_exclude_file(repo, run)
    if exclude_file is not None:
        remove_exclude_line(exclude_file, line)


def reconcile_link_excludes(
    repo: Path,
    *,
    linked: Sequence[str] = (),
    pruned: Sequence[str] = (),
    run: Runner = _default_run,
) -> None:
    """Add and remove exact repo-relative excludes for reconciled links."""
    exclude_file = git_exclude_file(repo, run)
    if exclude_file is None:
        return
    for entry in linked:
        ensure_exclude_line(exclude_file, f"/{entry.strip('/').replace(os.sep, '/')}")
    for entry in pruned:
        remove_exclude_line(exclude_file, f"/{entry.strip('/').replace(os.sep, '/')}")


def materialize_workspace(
    repo: Path,
    brainspace: Path,
    name: str,
    run: Runner = _default_run,
) -> str | None:
    """Replace a dotbrain-owned workspace link with a project-owned directory."""
    workspace = Path(repo) / name
    expected = Path(brainspace) / name
    if workspace.is_symlink():
        if not paths.symlink_target_matches(os.readlink(workspace), str(expected)):
            return f"{workspace} is not a dotbrain workspace link; leaving it unchanged"
        workspace.unlink()
    elif workspace.exists() and not workspace.is_dir():
        return f"{workspace} exists and is not a directory; leaving it unchanged"
    workspace.mkdir(parents=True, exist_ok=True)
    remove_local_exclude_line(repo, f"/{name}", run)
    return None


def ensure_symlink(repo: Path, name: str, target: Path) -> str | None:
    """Create/repair ``repo/name`` -> ``target``. Returns a warning if a real path is in the way."""
    path = Path(repo) / name
    target_str = str(target)
    if path.is_symlink():
        if paths.symlink_target_matches(os.readlink(path), target_str):
            return None
        path.unlink()
    elif path.exists():
        return f"{path} exists and is not a symlink; leaving it unchanged"
    return _symlink_directory(path, target_str)


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
    text = target.read_text(encoding="utf-8")
    if "@.brain/CLAUDE.md" in text:
        return None
    if text and not text.endswith("\n"):
        text += "\n"
    target.write_text(f"{text}\n{pointer}\n", encoding="utf-8", newline="\n")
    return None


def ensure_agent_context_pointer(repo: Path, pointer: str = paths.ADOPTER_POINTER) -> list[str]:
    repo = Path(repo)
    agents = repo / "AGENTS.md"
    claude = repo / "CLAUDE.md"
    if not agents.exists() and not claude.exists():
        agents.write_text(f"{pointer}\n", encoding="utf-8", newline="\n")
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
    workspace_links: Sequence[str] = (),
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


def _managed_workspace_links(repo: Path, dotbrain_home: Path) -> list[Path]:
    root = Path(dotbrain_home).resolve()
    links: list[Path] = []
    for name in (".claude", ".codex"):
        workspace = Path(repo) / name
        if workspace.is_symlink():
            candidates = [workspace]
        elif workspace.is_dir():
            candidates = list(workspace.rglob("*"))
        else:
            continue
        for entry in candidates:
            if not entry.is_symlink():
                continue
            try:
                if entry.resolve().is_relative_to(root):
                    links.append(entry)
            except OSError:
                continue
    return links


def _remove_empty_workspace_dirs(repo: Path) -> list[Path]:
    removed: list[Path] = []
    for name in (".claude", ".codex"):
        workspace = Path(repo) / name
        for directory in sorted(
            (path for path in workspace.rglob("*") if path.is_dir() and not path.is_symlink()),
            key=lambda path: len(path.parts),
            reverse=True,
        ) if workspace.is_dir() and not workspace.is_symlink() else []:
            if not any(directory.iterdir()):
                directory.rmdir()
        if workspace.is_dir() and not workspace.is_symlink() and not any(workspace.iterdir()):
            workspace.rmdir()
            removed.append(workspace)
    return removed


def unwire_repo(
    repo: Path,
    dry_run: bool = False,
    *,
    dotbrain_home: Path | None = None,
    run: Runner = _default_run,
) -> UnwireResult:
    """Remove agent workspace symlinks, exclude entries, and the adopter-context pointer.

    With ``dry_run`` the repo is left untouched; logs report what would be removed.
    """
    result = UnwireResult(repo=repo)
    verb = "would remove" if dry_run else "removed"

    managed_links = _managed_workspace_links(repo, dotbrain_home) if dotbrain_home else []
    managed_entries = [link.relative_to(repo).as_posix() for link in managed_links]

    for name in paths.BRAINSPACE_LINKS:
        link = repo / name
        if link.is_symlink():
            if not dry_run:
                link.unlink()
            result.logs.append(f"{verb} symlink {name}")

    for link, entry in zip(managed_links, managed_entries):
        if not dry_run:
            link.unlink()
        result.logs.append(f"{verb} workspace link {entry}")

    exclude = git_exclude_file(repo, run)
    if exclude and exclude.is_file():
        lines = exclude.read_text(encoding="utf-8").splitlines(keepends=True)
        excludes = {*paths.EXCLUDE_ENTRIES, "/.claude", "/.codex"}
        excludes.update(f"/{entry}" for entry in managed_entries)
        filtered = [l for l in lines if l.rstrip("\r\n") not in excludes]
        if len(filtered) < len(lines):
            if not dry_run:
                exclude.write_text("".join(filtered), encoding="utf-8", newline="\n")
            result.logs.append(f"{verb} dotbrain ignore rules from .git/info/exclude")

    if not dry_run:
        for workspace in _remove_empty_workspace_dirs(repo):
            result.logs.append(f"removed empty workspace {workspace.name}")

    for fname in ("AGENTS.md", "CLAUDE.md"):
        f = repo / fname
        if not f.exists() or f.is_symlink():
            continue
        text = f.read_text(encoding="utf-8")
        pointer_lines = set(paths.ADOPTER_POINTER.strip().splitlines())
        if any(pl in text for pl in pointer_lines):
            if not dry_run:
                cleaned = "\n".join(
                    l for l in text.splitlines() if l.strip() not in pointer_lines
                ).strip()
                f.write_text(
                    cleaned + "\n" if cleaned else "",
                    encoding="utf-8",
                    newline="\n",
                )
            result.logs.append(f"{verb} agent-context pointer from {fname}")

    return result
