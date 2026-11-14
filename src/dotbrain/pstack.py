"""Explicit project-local delivery of the optional pstack mode."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

import yaml

from dotbrain import adopter_repos, beads, config, paths, resource_loader, run_cache, runtimes, skills

NAME = "dotbrain-pstack"
REVISION = "9cd6939b766cb920f1c44970d7c7ee1ec28bd0d6"
VERSION = "0.15.36"
CACHE = f".cache/integrations/{NAME}"
POINTER = f".{NAME}.json"
MARKER = ".dotbrain-managed.json"
RECEIVERS = {rt.name: f"{rt.skill_path}/{NAME}" for rt in runtimes.RUNTIMES.values()
             if rt.name in ("claude", "codex")}
REQUIRED = ("plugin.json", *(f"skills/{name}/SKILL.md" for name in (
    "poteto-mode", "how", "why", "architect", "arena", "tdd", "interrogate", "swarm",
    "no-comments", "unslop", "technical-writing", "reflect", "correct")))
TIMEOUT = 15


@run_cache.memo
def qualify(source: Path, run=adopter_repos._default_run) -> None:
    """Verify an explicit complete clean source checkout; never install or update it."""
    if not source.is_dir():
        raise ValueError(f"pstack.source {source}: source checkout missing; select the qualified pstack checkout")
    try:
        root = run(["git", "-C", str(source), "rev-parse", "--show-toplevel"], check=False, timeout=TIMEOUT)
        revision = run(["git", "-C", str(source), "rev-parse", "HEAD"], check=False, timeout=TIMEOUT)
        status = run(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"], check=False, timeout=TIMEOUT)
        tracked = run(["git", "-C", str(source), "ls-files", "-z"], check=False, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"pstack.source {source}: Git qualification unavailable: {exc}") from exc
    if any(result.returncode for result in (root, revision, status, tracked)):
        raise ValueError(f"pstack.source {source}: cannot inspect Git checkout; restore the qualified source")
    if Path(root.stdout.strip()).resolve() != source.resolve() or revision.stdout.strip() != REVISION:
        raise ValueError(f"pstack.source {source}: unqualified checkout; expected revision {REVISION}")
    if status.stdout.strip():
        raise ValueError(f"pstack.source {source}: unqualified dirty checkout; use a clean source at {REVISION}")
    names = set(tracked.stdout.split("\0")) - {""}
    missing = [name for name in REQUIRED if name not in names]
    for name in sorted(names):
        entry = paths.confined_path(source, name)
        if not entry.is_file():
            missing.append(name)
    if missing:
        raise ValueError(f"pstack.source {source}: incomplete checkout; missing {', '.join(missing[:5])}")
    try:
        manifest = json.loads((source / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"pstack.source {source}: invalid plugin.json: {exc}") from exc
    if not isinstance(manifest, dict) or (manifest.get("name"), manifest.get("version")) != ("pstack", VERSION):
        raise ValueError(f"pstack.source {source}: plugin.json must identify pstack {VERSION}")


def preflight(home: Path, project: str, *, run=adopter_repos._default_run,
              backend: bool = False) -> config.ProjectPstack:
    selection = config.load_project_pstack(home, project)
    if not selection.enabled:
        return selection
    if config.load_project_config(home, project).mode not in ("embedded", "server"):
        raise ValueError("pstack.enabled requires a Beads backend; set beads.mode to embedded or server")
    qualify(selection.source, run)
    if backend:
        brainspace = paths.brainspace(home, project)
        if not (brainspace / ".beads/metadata.json").is_file():
            raise RuntimeError("pstack requires an initialized Beads backend; run dotbrain beads sync")
        try:
            result = run(["bd", "--readonly", "dolt", "test"], cwd=brainspace,
                         env=beads._beads_env(brainspace), check=False, timeout=TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"pstack Beads backend unavailable: {exc}; check bd and tracker connectivity") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout or "connection check failed").strip()
            raise RuntimeError(f"pstack Beads backend unavailable: {detail}; run dotbrain doctor")
    return selection


def _fingerprint(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _record(data: dict) -> str:
    return json.dumps({**data, "fingerprint": _fingerprint(data)}, indent=2, sort_keys=True) + "\n"


def _read_record(path: Path) -> dict | None:
    if path.is_symlink() or skills._is_junction(path) or not path.is_file() or path.stat().st_size > 64_000:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        fingerprint = data.pop("fingerprint")
        return data if data.get("owner") == NAME and fingerprint == _fingerprint(data) else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def _files(directory: Path) -> dict[str, str] | None:
    if directory.is_symlink() or skills._is_junction(directory) or not directory.is_dir():
        return None
    result = {}
    for entry in directory.rglob("*"):
        if entry.is_symlink() or skills._is_junction(entry):
            return None
        if entry.is_file() and entry.relative_to(directory).as_posix() != MARKER:
            result[entry.relative_to(directory).as_posix()] = hashlib.sha256(entry.read_bytes()).hexdigest()
    return result


def _cache_root(home: Path) -> Path:
    root = home
    for part in Path(CACHE).parts:
        root = root / part
        if root.is_symlink() or skills._is_junction(root):
            raise ValueError(f"{root}: integration cache must be a real directory; preserve and inspect the redirected entry")
    return paths.confined_path(home, CACHE)


def owned_link(home: Path, link: Path) -> bool:
    """Attribute a mode link independently of current selection or source availability."""
    if not link.is_symlink():
        return False
    destination = link.resolve()
    root = _cache_root(home).resolve()
    return destination.parent == root and _read_record(destination / MARKER) is not None


def _intact(link: Path) -> bool:
    destination = link.resolve()
    record = _read_record(destination / MARKER)
    return record is not None and record.get("files") == _files(destination)


def _resources() -> dict[str, bytes]:
    return {relative.as_posix(): resource.read_bytes()
            for relative, resource in resource_loader.iter_resource_files(f"integrations/{NAME}")}


def _cache(home: Path) -> Path:
    files = _resources()
    hashes = {name: hashlib.sha256(body).hexdigest() for name, body in files.items()}
    root = _cache_root(home)
    destination = paths.confined_path(root, _fingerprint(hashes))
    if destination.exists() or destination.is_symlink():
        record = _read_record(destination / MARKER)
        if record is None or record.get("files") != hashes or _files(destination) != hashes:
            raise ValueError(f"{destination}: modified or foreign integration cache preserved; inspect it before retrying")
        return destination
    paths.refuse_checkout(destination)
    root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=root))
    try:
        for name, body in files.items():
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        (staging / MARKER).write_text(_record({"owner": NAME, "files": hashes}), encoding="utf-8", newline="\n")
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination


def _replace_link(link: Path, source: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    staging = link.parent / f".{NAME}-{uuid.uuid4().hex}.tmp"
    backup = link.parent / f".{NAME}-{uuid.uuid4().hex}.backup"
    try:
        adopter_repos._symlink_directory(staging, os.path.relpath(source, link.parent))
        if link.is_symlink():
            link.rename(backup)
        try:
            staging.rename(link)
        except OSError:
            if backup.is_symlink():
                backup.rename(link)
            raise
        if backup.is_symlink():
            backup.unlink()
    finally:
        if staging.is_symlink():
            staging.unlink()


def reconcile(home: Path, repo: Path, project: str, workspaces, *, runtime: str = "all",
              run=adopter_repos._default_run, selection: config.ProjectPstack | None = None) -> skills.LinkResult:
    selection = selection or preflight(home, project, run=run, backend=True)
    result = skills.LinkResult()
    pointer = repo / POINTER
    previous = _read_record(pointer)
    if (pointer.exists() or pointer.is_symlink()) and previous is None:
        return skills.LinkResult(warnings=[f"{pointer}: modified or foreign discovery record preserved"])
    selected = {runtimes.for_workspace(ws).name for ws in workspaces}
    modes = dict(previous.get("modes", {})) if previous else {}
    caches = dict(previous.get("caches", {})) if previous else {}
    touched = []
    for name, relative in RECEIVERS.items():
        if runtime != "all" and name != runtime:
            continue
        conflict = skills.project_directory_conflict(repo, str(Path(relative).parent))
        if conflict:
            result.warnings.append(conflict)
            continue
        link = repo / relative
        owned = owned_link(home, link)
        if link.exists() or link.is_symlink():
            if not owned or not _intact(link):
                result.warnings.append(f"{link}: modified or foreign mode preserved")
                modes.pop(name, None)
                caches.pop(name, None)
                continue
        if selection.enabled and name in selected:
            source = _cache(home)
            caches[name] = str(source)
            if not owned or link.resolve() != source.resolve():
                _replace_link(link, source)
                result.linked.append(relative)
            modes[name] = relative
            touched.append(relative)
        else:
            modes.pop(name, None)
            caches.pop(name, None)
            if owned:
                link.unlink()
                result.pruned.append(relative)
    if modes and selection.enabled:
        body = _record({"owner": NAME, "source": str(selection.source), "revision": REVISION,
                        "version": VERSION, "modes": modes, "caches": caches})
        if not pointer.is_file() or pointer.read_text(encoding="utf-8") != body:
            staging = repo / f"{POINTER}.{uuid.uuid4().hex}.tmp"
            try:
                staging.write_text(body, encoding="utf-8", newline="\n")
                os.replace(staging, pointer)
            finally:
                staging.unlink(missing_ok=True)
            result.linked.append(POINTER)
        touched.append(POINTER)
    elif previous is not None:
        pointer.unlink()
        result.pruned.append(POINTER)
    if touched or result.pruned:
        adopter_repos.reconcile_link_excludes(repo, linked=touched, pruned=result.pruned, run=run)
    return result


def unwire(home: Path, repo: Path, *, run=adopter_repos._default_run) -> skills.LinkResult:
    return reconcile(home, repo, "", (), run=run,
                     selection=config.ProjectPstack())


def delivery_issues(home: Path, repo: Path, workspaces, enabled: bool) -> list[str]:
    issues = []
    selected = {runtimes.for_workspace(ws).name for ws in workspaces}
    expected = {name: hashlib.sha256(body).hexdigest() for name, body in _resources().items()} if enabled else {}
    record = _read_record(repo / POINTER) or {}
    for name, relative in RECEIVERS.items():
        link = repo / relative
        conflict = skills.project_directory_conflict(repo, str(Path(relative).parent))
        if enabled and name in selected:
            if conflict:
                issues.append(conflict)
            elif not owned_link(home, link) or not _intact(link) or _files(link.resolve()) != expected:
                issues.append(f"{relative}: missing, modified, foreign, or stale pstack mode; run dotbrain refresh")
            elif (record.get("modes", {}).get(name) != relative
                  or record.get("caches", {}).get(name) != str(link.resolve())):
                issues.append(f"{POINTER}: missing or stale {name} mode selection; run dotbrain refresh")
        elif not conflict and owned_link(home, link):
            issues.append(f"{relative}: unselected pstack mode remains; run dotbrain refresh")
    if enabled and selected.intersection(RECEIVERS) and not discovery(repo):
        issues.append(f"{POINTER}: missing or stale pstack discovery; run dotbrain refresh")
    elif not enabled and _read_record(repo / POINTER) is not None:
        issues.append(f"{POINTER}: unselected pstack discovery remains; run dotbrain refresh")
    return issues


def discovery(repo: Path) -> bytes:
    """Return bounded local discovery only; startup never probes Git or Beads here."""
    try:
        path = repo / ".brain/project.yaml"
        data = config._mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
        selection = config.parse_pstack(data, str(path))
        record = _read_record(repo / POINTER)
        if (not selection.enabled or record is None or record.get("source") != str(selection.source)
                or record.get("revision") != REVISION or record.get("version") != VERSION):
            return b""
        modes = record.get("modes", {})
        locations = [relative + "/SKILL.md" for name, relative in RECEIVERS.items()
                     if modes.get(name) == relative and (repo / relative).is_symlink()
                     and not skills.project_directory_conflict(repo, str(Path(relative).parent))
                     and str((repo / relative).resolve()) == record.get("caches", {}).get(name)
                     and (repo / relative / "SKILL.md").is_file()]
        if not locations:
            return b""
        return ("## Selected workflow\n\n" + NAME + ": " + ", ".join(locations)
                + f". Dependency selection: {POINTER}. Restart sessions after selection changes.\n\n").encode()
    except (OSError, ValueError, TypeError, AttributeError, yaml.YAMLError):
        return b""
