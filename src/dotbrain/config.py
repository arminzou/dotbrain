"""Config store: global ``config.yaml`` + per-project ``.brain/project.yaml``.

``config.yaml`` (data root, version 3) holds global infrastructure defaults
(``beads.server``, ``sync``).  ``brainspaces/<name>/.brain/project.yaml`` (version 1) holds
per-project identity (beads mode, database, remote).  The old
``dotbrain.yaml`` is read transparently as a fallback when ``config.yaml``
is absent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotbrain import paths, resource_loader


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BeadsServer:
    """Shared beads sql-server defaults from ``beads.server`` in config.yaml."""
    host: str = ""
    port: str = "3307"
    user: str = "beads"
    ssh_host: str = ""


@dataclass
class ProjectBeads:
    """Effective per-project beads config from ``.brain/project.yaml``."""
    mode: str = "embedded"  # embedded | server | none
    remote: str = ""
    database: str = ""


_SIZE_UNITS = {"": 1, "B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}


@dataclass
class SyncConfig:
    """Home sync settings from the optional ``sync:`` section of config.yaml."""
    enabled: bool = True
    max_file_size: int = 1024 ** 2  # bytes


@dataclass
class DotbrainConfig:
    """Parsed representation of config.yaml (schema v3)."""
    version: int = 3
    beads_server: BeadsServer = field(default_factory=BeadsServer)
    sync: SyncConfig = field(default_factory=SyncConfig)


# ---------------------------------------------------------------------------
# Global config (config.yaml)
# ---------------------------------------------------------------------------

def _config_path(dotbrain_home: Path) -> Path:
    return Path(dotbrain_home) / "config.yaml"


def _old_config_path(dotbrain_home: Path) -> Path:
    return Path(dotbrain_home) / "dotbrain.yaml"


def _mapping(value: Any, location: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{location}: expected a YAML mapping")
    return value


def parse_size(value: Any, location: str) -> int:
    """Parse a byte count: an integer, or a string such as ``"500KB"`` or ``"1MB"`` (1 KB = 1024 bytes)."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    if isinstance(value, str):
        match = re.fullmatch(r"\s*(\d+)\s*([KMG]?B?)\s*", value.upper())
        if match and match.group(2) in _SIZE_UNITS:
            return int(match.group(1)) * _SIZE_UNITS[match.group(2)]
    raise ValueError(f"{location}: expected a byte count such as 1048576, \"500KB\", or \"1MB\"")


def _parse_sync(data: dict, location: str) -> SyncConfig:
    section = _mapping(data.get("sync"), f"{location}: sync")
    enabled = section.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"{location}: sync.enabled must be true or false")
    size = section.get("max-file-size")
    return SyncConfig(enabled=enabled, max_file_size=SyncConfig.max_file_size if size is None
                      else parse_size(size, f"{location}: sync.max-file-size"))


def load_config(dotbrain_home: Path) -> DotbrainConfig:
    """Load ``config.yaml``; transparently reads old ``dotbrain.yaml`` as fallback."""
    import yaml  # deferred: only needed when this function is called

    path = _config_path(dotbrain_home)
    if not path.is_file():
        old = _old_config_path(dotbrain_home)
        if old.is_file():
            return _parse_old_format(old)

    if not path.is_file():
        return DotbrainConfig()

    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    beads = _mapping(data.get("beads"), f"{path}: beads")
    server = _mapping(beads.get("server"), f"{path}: beads.server")
    try:
        version = int(data.get("version", 3))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path}: version must be an integer") from exc
    return DotbrainConfig(
        version=version,
        beads_server=BeadsServer(
            host=str(server.get("host", "")),
            port=str(server.get("port", "3307")),
            user=str(server.get("user", "beads")),
            ssh_host=str(server.get("ssh_host", "")),
        ),
        sync=_parse_sync(data, str(path)),
    )


def _parse_old_format(path: Path) -> DotbrainConfig:
    """Read beads.server from a legacy dotbrain.yaml, ignoring projects: section."""
    import yaml

    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    beads = _mapping(data.get("beads"), f"{path}: beads")
    server = _mapping(beads.get("server"), f"{path}: beads.server")
    return DotbrainConfig(
        version=3,
        beads_server=BeadsServer(
            host=str(server.get("host", "")),
            port=str(server.get("port", "3307")),
            user=str(server.get("user", "beads")),
            ssh_host=str(server.get("ssh_host", "")),
        ),
    )


# ---------------------------------------------------------------------------
# Per-project config (<data-dir>/<name>/.brain/project.yaml)
# ---------------------------------------------------------------------------

def _project_config_path(dotbrain_home: Path, name: str) -> Path:
    """Canonical ``.brain/project.yaml`` path."""
    return paths.confined_path(paths.brainspace(dotbrain_home, name), ".brain/project.yaml")


def default_beads_mode(dotbrain_home: Path) -> str:
    """Effective default beads mode for a project that doesn't set one.

    Follows infrastructure: a configured shared sql-server (``beads.server.host``
    in config.yaml) makes ``server`` the default, so every wired project uses it;
    otherwise the default is ``embedded``. Projects override per-project by
    setting ``mode`` explicitly in ``.brain/project.yaml``.
    """
    return "server" if load_config(dotbrain_home).beads_server.host else "embedded"


def load_project_config(dotbrain_home: Path, name: str) -> ProjectBeads:
    """Read ``brainspaces/<name>/.brain/project.yaml``, resolving defaults.

    The default mode follows :func:`default_beads_mode` (server when a shared
    server is configured, else embedded); database defaults to the project name.
    Old ``dotbrain.yaml`` ``projects:<name>`` entries take precedence over a
    default (seeded) ``.brain/project.yaml``.
    """
    import yaml

    default_mode = default_beads_mode(dotbrain_home)

    # Read .brain/project.yaml if it exists.
    file_beads: ProjectBeads | None = None
    path = _project_config_path(dotbrain_home, name)
    if path.is_file():
        data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
        beads = _mapping(data.get("beads"), f"{path}: beads")
        file_beads = ProjectBeads(
            mode=str(beads.get("mode", default_mode)),
            remote=str(beads.get("remote", "")),
            database=str(beads.get("database", name)),
        )

    # Explicit old dotbrain.yaml entries override a default .brain/project.yaml.
    old = _old_config_path(dotbrain_home)
    if old.is_file():
        data = _mapping(yaml.safe_load(old.read_text(encoding="utf-8")), str(old))
        projects = _mapping(data.get("projects"), f"{old}: projects")
        project = _mapping(projects.get(name), f"{old}: projects.{name}")
        entry = _mapping(project.get("beads"), f"{old}: projects.{name}.beads")
        if entry:
            old_beads = ProjectBeads(
                mode=str(entry.get("mode", default_mode)),
                remote=str(entry.get("remote", "")),
                database=str(entry.get("database", name)),
            )
            # If .brain/project.yaml exists and deviates from defaults, it wins.
            # If .brain/project.yaml is all defaults (seeded template), old format wins.
            if file_beads is not None and _is_beads_deviation(dotbrain_home, name, file_beads):
                return file_beads
            return old_beads

    if file_beads is not None:
        return file_beads
    return ProjectBeads(mode=default_mode, database=name)


def load_project_skills(dotbrain_home: Path, name: str) -> tuple[str, ...]:
    """Read the operator's per-project skill list from ``.brain/project.yaml`` ``skills:``.
    """
    import yaml

    from dotbrain import skills

    path = _project_config_path(dotbrain_home, name)
    if not path.is_file():
        return ()
    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    return skills._clean(data.get("skills"))


def load_project_subagents(dotbrain_home: Path, name: str) -> tuple[str, ...]:
    """Read per-project subagent declarations from ``.brain/project.yaml``."""
    import yaml

    from dotbrain import skills

    path = _project_config_path(dotbrain_home, name)
    if not path.is_file():
        return ()
    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    return skills._clean(data.get("subagents"))


# The packaged roles are whatever packaged definitions ship; the Codex set is the canonical list.
PACKAGED_ROLES = tuple(sorted(rel.stem for rel, _ in resource_loader.iter_resource_files("agents/codex")
                              if rel.suffix == ".toml"))
PROJECT_VERSION = 2


def load_project_packaged(dotbrain_home: Path, name: str) -> tuple[int, tuple[str, ...]]:
    """Read ``version`` and ``packaged-subagents`` from ``.brain/project.yaml``.

    On a version-2 file the list is the whole truth: absent or empty means none.
    An unversioned (version 1) file without the list keeps every packaged role.
    """
    import yaml

    path = _project_config_path(dotbrain_home, name)
    if not path.is_file():
        return PROJECT_VERSION, PACKAGED_ROLES
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    roles = ", ".join(PACKAGED_ROLES)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping; packaged-subagents takes roles from: {roles}")
    version = data.get("version", 1)
    raw = data.get("packaged-subagents")
    if raw is None:
        return version, (PACKAGED_ROLES if version == 1 else ())
    entries = raw if isinstance(raw, list) else [raw]
    listed = tuple(dict.fromkeys(str(entry).strip() for entry in entries if str(entry).strip()))
    unknown = [entry for entry in listed if entry not in PACKAGED_ROLES]
    if unknown:
        raise ValueError(f"{path}: unknown packaged subagent {', '.join(unknown)}; packaged roles: {roles}")
    return version, listed


def upgrade_project_packaged(dotbrain_home: Path, name: str) -> str | None:
    """Append ``version: 2`` and every packaged role to an unversioned ``project.yaml`` once.

    Appends text instead of re-dumping YAML so existing lines and comments survive.
    """
    import yaml

    version, _ = load_project_packaged(dotbrain_home, name)
    path = _project_config_path(dotbrain_home, name)
    if version != 1 or not path.is_file():
        return None
    existing = path.read_bytes()
    eol = "\r\n" if b"\r\n" in existing else "\n"
    roles = "".join(f"  - {role}\n" for role in PACKAGED_ROLES)
    lead = "\n" if not existing.endswith(b"\n") else ""
    block = (f"{lead}version: {PROJECT_VERSION}\n"
             f"# Packaged subagents delivered to this project; remove a role to stop delivering it.\n"
             f"packaged-subagents:\n{roles}").replace("\n", eol).encode("utf-8")
    # Some valid layouts (flow or indented roots, document markers, kept block scalars)
    # cannot take a top-level append; refuse them rather than change their meaning.
    # Anchors, aliases and merge keys make the meaning check unsafe (aliases can recurse); refuse them.
    text = existing.decode("utf-8")
    shared = any(isinstance(token, (yaml.AnchorToken, yaml.AliasToken))
                 or (isinstance(token, yaml.ScalarToken) and token.plain and token.value == "<<")
                 for token in yaml.scan(text))
    try:
        safe = not shared and yaml.safe_load(text + block.decode("utf-8")) == {
            **yaml.safe_load(text), "version": PROJECT_VERSION, "packaged-subagents": list(PACKAGED_ROLES)}
    except (yaml.YAMLError, RecursionError):
        safe = False
    if not safe:
        raise ValueError(f"{path}: cannot append the packaged-subagents record to this layout; add "
                         f"'version: {PROJECT_VERSION}' and 'packaged-subagents: [{', '.join(PACKAGED_ROLES)}]' by hand")
    with path.open("ab") as handle:  # bytes: keep the file's own line endings
        handle.write(block)
    return f"upgraded {path.name} to version {PROJECT_VERSION} with packaged-subagents: {', '.join(PACKAGED_ROLES)}"


def load_project_agents(dotbrain_home: Path, name: str, *, defaults: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Read declared agent workspaces from ``brainspaces/<name>/.brain/project.yaml``.

    Missing ``agents`` uses the supplied machine defaults.
    An explicit empty list disables agent workspace seeding.
    """
    import yaml

    path = _project_config_path(dotbrain_home, name)
    if not path.is_file():
        return defaults

    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))

    raw_agents = data.get("agents")
    if raw_agents is None:
        return defaults

    entries = raw_agents if isinstance(raw_agents, list) else [raw_agents]
    cleaned: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        agent = str(entry).strip().lower()
        if not agent or agent in seen:
            continue
        seen.add(agent)
        cleaned.append(agent)
    return tuple(cleaned)


def write_project_config(dotbrain_home: Path, name: str, beads: ProjectBeads) -> str | None:
    """Write ``brainspaces/<name>/.brain/project.yaml``. Returns a log line or None if unchanged."""
    import yaml

    path = _project_config_path(dotbrain_home, name)
    existing = load_project_config(dotbrain_home, name)

    if (existing.mode == beads.mode
            and existing.remote == beads.remote
            and existing.database == (beads.database or name)):
        return None

    resolved = ProjectBeads(
        mode=beads.mode,
        remote=beads.remote,
        database=beads.database if beads.database != name else "",
    )

    doc = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.is_file() else {}
    if not isinstance(doc, dict) or not isinstance(doc.get("beads", {}), dict):
        raise ValueError(f"{path}: expected YAML mappings")
    doc.setdefault("beads", {})["mode"] = resolved.mode
    doc["beads"].pop("remote", None)
    doc["beads"].pop("database", None)
    if resolved.remote:
        doc["beads"]["remote"] = resolved.remote
    if resolved.database:
        doc["beads"]["database"] = resolved.database

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(doc, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
        newline="\n",
    )
    return f"wrote beads config for {name} to {path}"


# ---------------------------------------------------------------------------
# Public mutation helpers (used by wire / migrate / workflows)
# ---------------------------------------------------------------------------

def record_project_beads(dotbrain_home: Path, name: str, beads: ProjectBeads) -> str | None:
    """Persist a project's beads config in ``.brain/project.yaml``.

    Only writes when the config deviates from the resolved defaults (mode differs
    from the config-driven default mode, or a custom remote/database).  A default
    call never overwrites a manual declaration (e.g. mode: none) that already
    exists.  Returns a log line when the file changed, else None.
    """
    if not _is_beads_deviation(dotbrain_home, name, beads):
        return None
    return write_project_config(dotbrain_home, name, beads)


def _is_beads_deviation(dotbrain_home: Path, name: str, beads: ProjectBeads) -> bool:
    return (
        beads.mode != default_beads_mode(dotbrain_home)
        or bool(beads.remote)
        or bool(beads.database and beads.database != name)
    )


def _remove_from_old_projects_section(path: Path, name: str) -> str | None:
    """Remove owned legacy Beads keys, preserving unknown configuration values."""
    import yaml

    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    projects = _mapping(data.get("projects"), f"{path}: projects")
    if name not in projects:
        return None
    entry = _mapping(projects[name], f"{path}: projects.{name}")
    section = _mapping(entry.get("beads"), f"{path}: projects.{name}.beads")
    changed = any(key in section for key in ("mode", "remote", "database"))
    if not changed:
        return None
    for key in ("mode", "remote", "database"):
        section.pop(key, None)
    if not section:
        entry.pop("beads", None)
    if not entry:
        projects.pop(name)
    if not projects:
        data.pop("projects", None)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")
    return f"removed beads deviation for {name} from dotbrain.yaml"


def remove_legacy_project_beads(dotbrain_home: Path, name: str) -> str | None:
    """Clear legacy tracker overrides after an explicit backend migration."""
    paths.validate_project_name(name)
    old = _old_config_path(dotbrain_home)
    return _remove_from_old_projects_section(old, name) if old.is_file() else None
