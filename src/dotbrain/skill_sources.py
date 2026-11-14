"""The skill library in ``~/dotbrain/skills`` and the selections that deliver it.

External skill repositories are Git submodules of the dotbrain home under ``skills/<name>``, so
home sync shares them by commit. Selections are the ``skills:`` lists in ``config.yaml`` (global)
and a Brainspace's ``.brain/project.yaml``. Editing a selection changes only that list, keeps
comments and layout, and refuses when re-reading the file would show any other difference.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from pathlib import Path

import yaml

from dotbrain import home_sync, paths, skills

Runner = home_sync.Runner
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


# ---------------------------------------------------------------------------
# Selections
# ---------------------------------------------------------------------------

def _scalar(value: str) -> str:
    """``value`` as a YAML list item: plain when it reads back unchanged, else a quoted string."""
    awkward = not value or value[0] in "-?:,[]{}#&*!|>'\"%@`" or ": " in value or " #" in value
    return json.dumps(value) if awkward or yaml.safe_load(value) != value else value


def set_list(text: str, key: str, values: list[str], where: str) -> str:
    """``text`` with the top-level ``key`` set to ``values``, everything else byte-for-byte."""
    before = yaml.safe_load(text) or {}
    if not isinstance(before, dict):
        raise ValueError(f"{where}: expected a YAML mapping")
    lines = text.splitlines(keepends=True)
    found = next((i for i, line in enumerate(lines) if re.match(rf"{re.escape(key)}\s*:", line)), None)
    flow = "[" + ", ".join(_scalar(value) for value in values) + "]"
    if found is None:
        tail = "" if not text or text.endswith("\n") else "\n"
        body = "".join(f"  - {_scalar(value)}\n" for value in values)
        new = text + tail + (f"{key}:\n{body}" if values else f"{key}: []\n")
    else:
        rest = re.sub(r"\s+#.*$", "", lines[found].split(":", 1)[1]).strip()
        if rest.startswith("[") and rest.endswith("]"):
            lines[found] = f"{key}: {flow}\n"
        elif rest == "":
            items, indent, end = [], None, found + 1
            while end < len(lines):
                stripped = lines[end].strip()
                if stripped and not stripped.startswith("#"):
                    if not (lines[end][0] in " \t-" and (stripped == "-" or stripped.startswith("- "))):
                        break
                    items.append(end)
                    indent = indent if indent is not None else lines[end][:len(lines[end]) - len(lines[end].lstrip())]
                end += 1
            def item(index: int) -> object:
                parsed = yaml.safe_load(lines[index].strip())
                return parsed[0] if isinstance(parsed, list) and len(parsed) == 1 else None

            existing = {item(index) for index in items}
            fresh = [f"{indent if indent is not None else '  '}- {_scalar(value)}\n"
                     for value in values if value not in existing]
            at = (items[-1] if items else found) + 1
            lines[at:at] = fresh  # new entries after the existing ones, which keep their comments
            lines = [line for index, line in enumerate(lines) if index not in items or item(index) in values]
            if not values:
                lines[found] = f"{key}: []\n"
        else:
            raise ValueError(f"{where}: cannot change {key}: safely in this layout; edit it by hand")
        new = "".join(lines)
    try:
        safe = (yaml.safe_load(new) or {}) == {**before, key: list(values)}
    except yaml.YAMLError:
        safe = False
    if not safe:
        raise ValueError(f"{where}: cannot change {key}: safely in this layout; edit it by hand")
    return new


def selection_file(home: Path, brainspace: Path | None) -> Path:
    """The global ``config.yaml``, or the Brainspace's ``project.yaml``."""
    path = (paths.confined_path(home, "config.yaml") if brainspace is None
            else paths.confined_path(brainspace, ".brain/project.yaml"))
    if not path.is_file():
        raise ValueError(f"{path}: missing; run {'dotbrain bootstrap' if brainspace is None else 'dotbrain refresh'}")
    return path


def change_selection(home: Path, path: Path, *, add: tuple[str, ...] = (), remove: tuple[str, ...] = ()) -> list[str]:
    """Add or remove ``skills:`` entries in one selection file. Returns what changed."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    current = list(skills._clean(data.get("skills") if isinstance(data, dict) else None))
    absent = [entry for entry in remove if entry not in current]
    if absent:
        raise ValueError(f"{path}: not selected: {', '.join(absent)}")
    wanted = [entry for entry in current if entry not in remove]
    wanted += [entry for entry in skills._clean(list(add)) if entry not in wanted]
    if wanted == current:
        return []
    skills.resolve_selection(home, wanted)  # every entry exists and no two skills collide
    path.write_bytes(set_list(text, "skills", wanted, str(path)).encode("utf-8"))
    return ([f"selected {entry} in {path}" for entry in wanted if entry not in current]
            + [f"deselected {entry} in {path}" for entry in current if entry not in wanted])


def selection_files(home: Path) -> list[Path]:
    """Every selection file: global first, then each Brainspace."""
    files = [paths.confined_path(home, "config.yaml")]
    files += [paths.confined_path(space, ".brain/project.yaml") for space in paths.brainspaces(home)]
    return [path for path in files if path.is_file()]


# ---------------------------------------------------------------------------
# Library: skill repositories as submodules of the home
# ---------------------------------------------------------------------------

def _repo_path(name: str) -> str:
    if not _NAME.fullmatch(name):
        raise ValueError(f"invalid skill repository name {name!r}; use letters, digits, '.', '_' or '-'")
    return f"skills/{name}"


def _require_home_repo(home: Path, run: Runner) -> Path:
    try:
        return home_sync._git_dir(home, run)
    except home_sync.SyncError as exc:
        raise ValueError(f"{exc}; skill repositories are submodules of the dotbrain home's Git repository") from exc


def _env(home: Path, run: Runner) -> dict:
    return {"GIT_SSH_COMMAND": home_sync._ssh_command(home, run)}


def _git(home: Path, run: Runner, *args: str, timeout: float | None = None) -> str:
    return home_sync._git(run, home, *args, env=_env(home, run), timeout=timeout).stdout


def repositories(home: Path) -> list[str]:
    """Names of the skill repositories the home declares."""
    return [path.removeprefix("skills/") for path in home_sync.declared_submodules(home)
            if path.startswith("skills/") and "/" not in path.removeprefix("skills/")]


def _commit(home: Path, run: Runner, message: str, *pathspecs: str) -> None:
    home_sync._git(run, home, "commit", "--quiet", "-m", message, "--", *pathspecs)


def add(home: Path, url: str, *, name: str | None = None, ref: str | None = None,
        run: Runner = home_sync.run_bounded) -> tuple[str, list[str]]:
    """Add ``url`` as ``skills/<name>`` and commit it. Returns (path, the skill entries it holds)."""
    _require_home_repo(home, run)
    name = name or re.sub(r"\.git$", "", url.rstrip("/").replace("\\", "/").rsplit("/", 1)[-1].rsplit(":", 1)[-1])
    path = _repo_path(name)
    if os.path.lexists(home / path):
        raise ValueError(f"{home / path} already exists; choose another --name")
    _git(home, run, "submodule", "add", "--quiet", "--", url, path, timeout=home_sync.SUBMODULE_TIMEOUT_SECONDS)
    try:
        if ref:
            home_sync._git(run, home / path, "checkout", "--quiet", "--detach", ref)
            home_sync._git(run, home, "add", "--", path)
        found = skills.discover_skills(home / path)
        if not found:
            raise ValueError(f"{url} contains no SKILL.md; nothing was added")
        _commit(home, run, f"home: add skill repository {path}", ".gitmodules", path)
    except Exception:
        _drop(home, path, run)
        raise
    return path, [f"{name}/{skill}" for skill in found]


def update(home: Path, names: tuple[str, ...] = (), *, ref: str | None = None,
           run: Runner = home_sync.run_bounded) -> tuple[list[str], dict[str, str]]:
    """Move skill repositories to their remote's latest commit, or one to ``ref``, and commit each move.

    Returns (changes, skipped name -> reason). A repository holding local work is skipped.
    """
    _require_home_repo(home, run)
    known = repositories(home)
    selected = list(names) or known
    if ref and len(selected) != 1:
        raise ValueError("--ref needs exactly one skill repository name")
    unknown = [name for name in selected if name not in known]
    if unknown:
        raise ValueError(f"not a skill repository of this home: {', '.join(unknown)}")
    changes: list[str] = []
    skipped: dict[str, str] = {}
    for name in selected:
        path = _repo_path(name)
        repository = home / path
        if not os.path.lexists(repository / ".git"):
            skipped[name] = "not cloned on this machine; run dotbrain sync"
            continue
        reason = home_sync.hold_reason(repository, run)
        if reason:
            skipped[name] = reason
            continue
        before = home_sync._git(run, repository, "rev-parse", "HEAD").stdout.strip()
        if ref:
            home_sync._git(run, repository, "fetch", "--quiet", "--tags", "origin", env=_env(home, run),
                           timeout=home_sync.SUBMODULE_TIMEOUT_SECONDS)
            home_sync._git(run, repository, "checkout", "--quiet", "--detach", ref)
        else:
            _git(home, run, "submodule", "update", "--quiet", "--remote", "--", path,
                 timeout=home_sync.SUBMODULE_TIMEOUT_SECONDS)
        after = home_sync._git(run, repository, "rev-parse", "HEAD").stdout.strip()
        if after == before:
            continue
        home_sync._git(run, home, "add", "--", path)
        _commit(home, run, f"home: update skill repository {path} to {after[:12]}", path)
        changes.append(f"updated {path} from {before[:12]} to {after[:12]}")
    return changes, skipped


def _deselection(home: Path, name: str) -> list[tuple[Path, tuple[str, ...]]]:
    """Each selection file with its entries inside ``skills/<name>``."""
    found = []
    for path in selection_files(home):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = tuple(entry for entry in skills._clean(data.get("skills") if isinstance(data, dict) else None)
                        if entry == name or entry.startswith(name + "/"))
        if entries:
            found.append((path, entries))
    return found


def remove(home: Path, name: str, *, run: Runner = home_sync.run_bounded) -> list[str]:
    """Deselect the repository's skills everywhere, then remove the submodule and commit."""
    _require_home_repo(home, run)
    path = _repo_path(name)
    if name not in repositories(home):
        raise ValueError(f"not a skill repository of this home: {name}")
    if os.path.lexists(home / path / ".git"):
        reason = home_sync.hold_reason(home / path, run)
        if reason:
            raise ValueError(f"{path} has {reason}; push or discard them first, nothing was removed")
    changes: list[str] = []
    selections = _deselection(home, name)
    for selection, entries in selections:
        changes += change_selection(home, selection, remove=entries)
    _drop(home, path, run)
    # One commit, so no machine ever receives a selection naming a repository it no longer has.
    _commit(home, run, f"home: remove skill repository {path}", ".gitmodules", path,
            *(selection.relative_to(home).as_posix() for selection, _ in selections))
    return changes + [f"removed {path}"]


def relink_all(home: Path) -> tuple[list[str], list[str]]:
    """Reconcile global and every checkout's skill links after the library changed. (changes, errors)"""
    from dotbrain import assets, projects

    changes: list[str] = []
    errors: list[str] = []
    targets = [None] + [target for target in projects.select_projects(home, all_projects=True) if target.checkout]
    for target in targets:
        where = "global" if target is None else target.project
        try:
            linked = assets.link_global(home, "skills") if target is None else assets.link_project(home, target, "skills")
        except (ValueError, RuntimeError, OSError, yaml.YAMLError) as exc:
            errors.append(f"{where}: {exc}")
            continue
        changes += [f"{where}: delivered {name}" for name in linked.linked]
        changes += [f"{where}: pruned {name}" for name in linked.pruned]
        errors += [f"{where}: {warning}" for warning in linked.warnings]
    return changes, errors


def _submodule_name(home: Path, path: str) -> str:
    text = (home / ".gitmodules").read_text(encoding="utf-8")
    for section, body in re.findall(r'^\[submodule "([^"]+)"\]\s*\n((?:(?!\[).*\n?)*)', text, re.MULTILINE):
        if re.search(rf"^\s*path\s*=\s*{re.escape(path)}\s*$", body, re.MULTILINE):
            return section
    return path


def _drop(home: Path, path: str, run: Runner) -> None:
    """Remove a submodule's checkout, declaration, record and cloned Git data."""
    module = _submodule_name(home, path)
    home_sync._git(run, home, "submodule", "deinit", "--quiet", "--force", "--", path, check=False)
    home_sync._git(run, home, "rm", "--quiet", "--force", "--", path)
    cloned = paths.confined_path(home_sync._git_dir(home, run) / "modules", module)
    if cloned.exists():
        shutil.rmtree(cloned, onerror=_writable_retry)  # ponytail: onexc replaces onerror from Python 3.12


def _writable_retry(function, target, _excinfo) -> None:
    """Git marks its objects read-only, which Windows refuses to delete."""
    os.chmod(target, stat.S_IWRITE)
    function(target)
