"""One-time migration of the retired global settings files into ``config.yaml`` version 4.

``skills/skills.yaml`` and ``agents/agents.yaml`` are merged into ``config.yaml``, backed up and
removed, and the ``agents/`` source directory becomes ``subagents/``. Every check runs in
:func:`plan` before :func:`apply` writes anything, so a refused migration changes no file.

The old files remain until ``config.yaml``, the source directory and every link are written
and verified; they are removed last. A durable pending config identifies our own prior write
on retry, including when cleanup already removed some of the old inputs.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from dotbrain import adopter_repos, assets, config, paths, resource_loader, runtimes, skills, subagents

CONFIG_VERSION = 4
SKILLS_FILE, AGENTS_FILE = paths.LEGACY_GLOBAL_FILES
# Where agents.yaml sits when an interrupted migration already renamed agents/ to subagents/.
MOVED_AGENTS_FILE = f"{paths.SUBAGENTS_DIR}/agents.yaml"
_KNOWN_KEYS = {SKILLS_FILE: {"version", "targets", "profiles", "global_extra", "extra"},
               AGENTS_FILE: {"version", "targets", "global"}}


@dataclass
class Plan:
    originals: dict[str, bytes]  # data-root relative path -> bytes, including config.yaml when it exists
    config_updated: bytes | None  # None when no legacy file needs merging
    rename_dir: bool  # move agents/ to subagents/
    remove_dir: bool  # agents/ holds nothing beyond empty folders and subagents/ already exists
    reports: list[str] = field(default_factory=list)
    relinks: list[tuple[Path, Path]] = field(default_factory=list)  # owned link -> source under subagents/


def _refuse(location: str, reason: str) -> ValueError:
    return ValueError(f"{location}: {reason}; global settings migration stopped and no file was changed")


def _read(path: Path, location: str) -> dict:
    """Parse a mapping, refusing layouts whose meaning a plain merge could change."""
    text = path.read_text(encoding="utf-8")
    try:
        tokens = list(yaml.scan(text))
        node = yaml.compose(text)
    except yaml.YAMLError as exc:
        raise _refuse(location, f"unparseable YAML ({exc.__class__.__name__})") from exc
    if any(isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken))
           for token in tokens):
        raise _refuse(location, "anchors, aliases, merge keys and tags are ambiguous")
    if node is None or (isinstance(node, yaml.ScalarNode) and node.tag.endswith(":null")):
        return {}
    if not isinstance(node, yaml.MappingNode):
        raise _refuse(location, "expected a YAML mapping")
    pending = [node]
    while pending:  # every nested mapping, since safe_load keeps only the last duplicate
        current = pending.pop()
        if isinstance(current, yaml.MappingNode):
            keys = [key.value for key, _ in current.value]
            if len(set(keys)) != len(keys):
                raise _refuse(location, "duplicate keys are ambiguous")
            pending.extend(value for _, value in current.value)
        elif isinstance(current, yaml.SequenceNode):
            pending.extend(current.value)
    return yaml.safe_load(text) or {}


def _convert_targets(data: dict, kind: str, location: str, user_home: Path,
                     profiles: dict[str, list[str]], reports: list[str]) -> None:
    """Drop targets equal to the default home; turn custom ones into profiles."""
    targets = data.get("targets") or {}
    if not isinstance(targets, dict):
        raise _refuse(location, "targets must be a mapping of runtime -> destination")
    for key, value in targets.items():
        rt = runtimes.find(str(key))
        if not isinstance(value, str) or not value.strip():
            raise _refuse(location, f"targets.{key} must be a destination path")
        if rt is None:
            raise _refuse(location, f"targets.{key} names an unknown runtime; remove it")
        if rt.key in ("claude-code", "codex"):
            default = runtimes.user_dir(rt, user_home) / kind
        else:  # the destination global delivery uses for this runtime
            found = assets.global_targets((rt,), kind, user_home, explicit=True, errors=[],
                                          dotbrain_home=user_home).get(rt.key, ())
            default = found[0] if found else None  # none when the home is rejected
        expanded = adopter_repos.expand_path(value.replace("\\", "/"), home=user_home)
        if default is not None and expanded.resolve() == default.resolve():
            reports.append(f"{location}: dropped targets.{key}, which names the default home")
            continue
        if rt.key not in ("claude-code", "codex"):
            # No profile equivalent: the runtime's home variable is the only way to relocate it.
            if rt.home_env:
                skills_dir = assets.HOME_DELIVERY[rt.name].skills_dir(Path("<home>") / rt.home_subdir).as_posix()
                hint = f"set {rt.home_env}=<home> instead; global skills then go to {skills_dir}"
            else:
                hint = f"{rt.label} global skills always go to {default.as_posix() if default else '~/' + rt.workspace + '/skills'}"
            reports.append(f"{location}: dropped targets.{key} ({rt.label}, folder {value}); {hint}")
            continue
        normalized = value.replace("\\", "/").rstrip("/")
        home, _, leaf = normalized.rpartition("/")
        if leaf != kind or not home:
            raise _refuse(location, f"targets.{key} does not end in /{kind}, so no runtime home matches it")
        homes = profiles.setdefault(rt.key, [])
        if home not in homes:
            homes.append(home)
        reports.append(f"{location}: converted targets.{key} to profiles.{rt.key}: [{home}]; "
                       "a profile receives both skills and subagents")


def _set_version(text: str) -> str:
    line = f"version: {CONFIG_VERSION}"
    updated, count = re.subn(r"^version:[^\n]*$", line, text, count=1, flags=re.MULTILINE)
    return updated if count else line + "\n" + text


def plan(root: Path, user_home: Path) -> Plan | None:
    """Validate every retired file and compute the merged ``config.yaml``; None when nothing remains."""
    root = Path(root)
    legacy_dir = paths.confined_path(root, paths.LEGACY_SUBAGENTS_DIR)
    pending_path = paths.confined_path(root, paths.GLOBAL_MIGRATION_PENDING)
    pending = pending_path.read_bytes() if pending_path.is_file() else None
    if (root / AGENTS_FILE).is_file() and (root / MOVED_AGENTS_FILE).is_file():
        raise _refuse(AGENTS_FILE, f"both {AGENTS_FILE} and {MOVED_AGENTS_FILE} hold settings")
    # Logical name -> path that holds it now.
    locations = {SKILLS_FILE: SKILLS_FILE,
                 AGENTS_FILE: AGENTS_FILE if (root / AGENTS_FILE).is_file() else MOVED_AGENTS_FILE}
    present = [name for name, where in locations.items() if paths.confined_path(root, where).is_file()]

    originals: dict[str, bytes] = {}
    reports: list[str] = []
    updated = None
    profiles = None
    if present:
        loaded = {}
        for name in present:
            path = root / locations[name]
            originals[locations[name]] = path.read_bytes()
            loaded[name] = data = _read(path, locations[name])
            unknown = sorted(str(key) for key in data if key not in _KNOWN_KEYS[name])
            if unknown:
                raise _refuse(name, f"unknown keys {', '.join(unknown)} cannot be carried into config.yaml")
        skill_data = loaded.get(SKILLS_FILE, {})
        agent_data = loaded.get(AGENTS_FILE, {})
        if "global_extra" in skill_data and "extra" in skill_data:
            raise _refuse(SKILLS_FILE, "both global_extra and extra are set")

        try:
            profiles = {key: list(homes) for key, homes in config.parse_profiles(skill_data.get("profiles"), SKILLS_FILE).items()}
        except ValueError as exc:
            raise _refuse(SKILLS_FILE, str(exc).removeprefix(f"{SKILLS_FILE}: ")) from exc
        _convert_targets(skill_data, "skills", SKILLS_FILE, user_home, profiles, reports)
        _convert_targets(agent_data, "agents", AGENTS_FILE, user_home, profiles, reports)
        names = skills._clean(agent_data.get("global"))
        dropped = [name for name in names if subagents.is_packaged(name)]
        if dropped:
            reports.append(f"{AGENTS_FILE}: dropped packaged subagents {', '.join(dropped)} from global; "
                           "packaged subagents are selected per project in project.yaml")
        merged = {
            "profiles": profiles,
            "skills": list(skills._clean(skill_data.get("global_extra", skill_data.get("extra")))),
            "subagents": [name for name in names if name not in dropped],
        }

        config_path = paths.confined_path(root, "config.yaml")
        if config_path.is_file():
            originals["config.yaml"] = config_path.read_bytes()
            text = originals["config.yaml"].decode("utf-8")
            current = _read(config_path, "config.yaml")
        else:
            text = resource_loader.resource("config.yaml").read_text(encoding="utf-8")
            current = yaml.safe_load(text) or {}
        missing = {}
        for key, value in merged.items():
            if key not in current:
                missing[key] = value
            elif current[key] != value and value and not (
                pending is not None and pending == originals.get("config.yaml") and _covered(value, current[key])
            ):
                # A value already holding every retired entry is this migration's own earlier write.
                raise _refuse("config.yaml", f"{key} conflicts with the value in the retired files")
        expected = {**current, "version": CONFIG_VERSION, **missing}
        profiles = config.parse_profiles(expected["profiles"], "config.yaml")
        text = _set_version(text)
        if missing:
            text += ("" if not text or text.endswith("\n") else "\n") + yaml.safe_dump(
                missing, sort_keys=False, default_flow_style=False)
        if yaml.safe_load(text) != expected:
            raise _refuse("config.yaml", "this YAML layout cannot be merged safely")
        updated = text.encode("utf-8")
        if pending is not None and pending != updated:
            raise _refuse(paths.GLOBAL_MIGRATION_PENDING, "settings changed during an unfinished migration")
    elif pending is not None:
        config_path = paths.confined_path(root, "config.yaml")
        if not config_path.is_file() or config_path.read_bytes() != pending:
            raise _refuse(paths.GLOBAL_MIGRATION_PENDING, "config.yaml differs from the unfinished migration")

    rename_dir = remove_dir = False
    if legacy_dir.is_dir():
        leftovers = [p for p in legacy_dir.rglob("*") if not p.is_dir() and p != root / AGENTS_FILE]
        if not (root / paths.SUBAGENTS_DIR).exists():
            rename_dir = True
        elif leftovers:
            raise _refuse(paths.LEGACY_SUBAGENTS_DIR, f"both {paths.LEGACY_SUBAGENTS_DIR}/ and "
                          f"{paths.SUBAGENTS_DIR}/ hold files; move custom subagent sources into {paths.SUBAGENTS_DIR}/")
        else:
            remove_dir = True
    if profiles is None:
        profiles = config.load_config(root).profiles
    relinks = _stale_links(root, user_home, profiles)
    if not (present or legacy_dir.is_dir() or relinks or pending is not None):
        return None
    return Plan(originals, updated, rename_dir, remove_dir, reports, relinks)


def _covered(retired, current) -> bool:
    if isinstance(retired, dict):
        return isinstance(current, dict) and all(_covered(homes, current.get(key, [])) for key, homes in retired.items())
    return isinstance(current, list) and all(item in current for item in retired)


def _stale_links(root: Path, user_home: Path, profiles: dict[str, list[str]]) -> list[tuple[Path, Path]]:
    """Global subagent links that still point into the legacy ``agents/`` directory.

    The rename moves sources for every runtime while a filtered bootstrap relinks only some, so the
    migration repoints these links itself in every Claude Code and Codex home.
    """
    legacy = (root / paths.LEGACY_SUBAGENTS_DIR).resolve()
    found = []
    for rt in runtimes.RUNTIMES.values():
        if not rt.subagents:
            continue
        homes = [runtimes.user_dir(rt, user_home)]
        homes += [adopter_repos.expand_path(home, home=user_home) for home in profiles.get(rt.key, ())]
        for home in homes:
            folder = home / "agents"
            if not folder.is_dir() or paths.inside_wired_checkout(folder):
                continue
            for entry in folder.iterdir():
                if not entry.is_symlink():
                    continue
                try:
                    relative = entry.resolve().relative_to(legacy)
                except (ValueError, OSError):
                    continue
                found.append((entry, root / paths.SUBAGENTS_DIR / relative))
    return found


def _write_atomic(target: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(prefix=".config-", suffix=".tmp", dir=target.parent, delete=False) as stream:
        staged = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if target.is_file():
            shutil.copymode(target, staged)
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)
    if target.read_bytes() != data:
        raise OSError(f"{target}: written content does not match")


def _relink(link: Path, source: Path) -> None:
    """Replace the link in one step, so a failure leaves the old, still-detectable link."""
    with tempfile.NamedTemporaryFile(prefix=f".{link.name}.", suffix=".dotbrain-tmp",
                                     dir=link.parent, delete=False) as stream:
        staged = Path(stream.name)
    try:
        staged.unlink()
        staged.symlink_to(os.path.relpath(source, link.parent))
        os.replace(staged, link)
    finally:
        staged.unlink(missing_ok=True)
    if link.resolve() != source.resolve():
        raise OSError(f"{link}: does not point to {source}")


def apply(root: Path, migration: Plan) -> list[str]:
    """Write and verify the new state, then remove the old files last.

    Delivery waits while old inputs or the pending config remain; the next bootstrap finishes
    whatever an interruption left undone.
    """
    root = Path(root)
    for name, original in migration.originals.items():
        if (root / name).read_bytes() != original:
            raise ValueError(f"{root / name}: changed during migration; rerun dotbrain bootstrap")
    logs = list(migration.reports)
    retired = [name for name in migration.originals if name != "config.yaml"]
    try:
        if retired:
            backup_root = paths.confined_path(root, ".cache/config-backups")
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = Path(tempfile.mkdtemp(prefix="global-settings-", dir=backup_root))
            for name, original in migration.originals.items():
                (backup / name).parent.mkdir(parents=True, exist_ok=True)
                (backup / name).write_bytes(original)
            logs.append(f"saved the original settings files to {backup}")
        if migration.config_updated is not None:
            # Persist the exact commit so a later process can distinguish retry from conflicting inputs.
            _write_atomic(root / paths.GLOBAL_MIGRATION_PENDING, migration.config_updated)
            _write_atomic(root / "config.yaml", migration.config_updated)
            logs.append(f"merged {', '.join(retired)} into config.yaml version {CONFIG_VERSION}")
        if migration.rename_dir:
            os.replace(root / paths.LEGACY_SUBAGENTS_DIR, root / paths.SUBAGENTS_DIR)
            logs.append(f"renamed {paths.LEGACY_SUBAGENTS_DIR}/ to {paths.SUBAGENTS_DIR}/")
        for link, source in migration.relinks:
            _relink(link, source)
            logs.append(f"repointed {link} to {source}")
        for name in retired:
            # The rename above carried agents/agents.yaml into subagents/.
            (root / (MOVED_AGENTS_FILE if name == AGENTS_FILE and migration.rename_dir else name)).unlink()
            logs.append(f"removed {name}")
        if migration.remove_dir:
            shutil.rmtree(root / paths.LEGACY_SUBAGENTS_DIR)
            logs.append(f"removed empty {paths.LEGACY_SUBAGENTS_DIR}/")
        (root / paths.GLOBAL_MIGRATION_PENDING).unlink(missing_ok=True)
    except OSError as exc:
        raise ValueError("; ".join(logs + [f"global settings migration interrupted ({exc}); settings are preserved "
                                           "and global delivery waits; rerun dotbrain bootstrap to finish"])) from exc
    return logs
