"""Helpers for launching agent sessions in git worktrees."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

Run = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class CodexWorktreePlan:
    """Concrete commands needed to start a Codex session in a worktree."""

    repo: Path
    name: str
    base: str
    worktree: Path
    create_command: tuple[str, ...]
    codex_command: tuple[str, ...]


def slugify_name(value: str) -> str:
    """Return a branch/worktree-safe slug for a human task name."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    if not slug:
        raise ValueError("worktree name cannot be empty")
    return slug


def repo_root(path: Path, run: Run = subprocess.run) -> Path:
    """Resolve the enclosing git toplevel for ``path``."""
    result = run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def codex_worktree_plan(
    repo: Path,
    name: str,
    *,
    base: str = "main",
    prompt: str | None = None,
    codex_args: Sequence[str] = (),
) -> CodexWorktreePlan:
    """Build the commands for a Codex worktree session."""
    resolved_repo = Path(repo).resolve()
    slug = slugify_name(name)
    worktree = resolved_repo / ".codex" / "worktrees" / slug
    create_command = (
        "git",
        "worktree",
        "add",
        "-b",
        slug,
        str(worktree),
        base,
    )
    codex_command = ("codex", "-C", str(worktree), *codex_args)
    if prompt:
        codex_command = (*codex_command, prompt)
    return CodexWorktreePlan(
        repo=resolved_repo,
        name=slug,
        base=base,
        worktree=worktree,
        create_command=create_command,
        codex_command=codex_command,
    )


def create_codex_worktree(plan: CodexWorktreePlan, run: Run = subprocess.run) -> None:
    """Create the worktree if it does not already exist."""
    if plan.worktree.exists():
        return
    plan.worktree.parent.mkdir(parents=True, exist_ok=True)
    run(plan.create_command, cwd=plan.repo, check=True)


def launch_codex(plan: CodexWorktreePlan) -> None:
    """Replace this process with ``codex`` inside the prepared worktree."""
    os.execvp(plan.codex_command[0], list(plan.codex_command))


# shlex.quote()'s safe-char set treats backslash as unsafe (a POSIX shell metacharacter), so it
# quotes every Windows path purely for containing `\`, even without a space. This is a display
# preview, not something meant to be pasted verbatim into either shell, so backslash is added to the
# safe set: quote only for genuinely ambiguous content (spaces, quotes, etc.), consistent across OSes.
_UNSAFE_CHARS = re.compile(r"[^\w@%+=:,./\\-]", re.ASCII)


def _quote_for_display(token: str) -> str:
    if token and not _UNSAFE_CHARS.search(token):
        return token
    return "'" + token.replace("'", "'\"'\"'") + "'"


def shell_join(command: Sequence[str]) -> str:
    """Quote a command for display."""
    return " ".join(_quote_for_display(arg) for arg in command)
