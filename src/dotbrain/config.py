"""Config store: global ``config.yaml`` + per-project ``.brain/project.yaml``.

``config.yaml`` (data root, version 3) holds global infrastructure defaults
(``beads.server``).  ``brainspaces/<name>/.brain/project.yaml`` (version 1) holds
per-project identity (beads mode, database, remote).  The old
``dotbrain.yaml`` is read transparently as a fallback when ``config.yaml``
is absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotbrain import paths


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


DEFAULT_PROJECT_AGENTS: tuple[str, ...] = ("claude", "codex")


@dataclass
class DotbrainConfig:
    """Parsed representation of config.yaml (schema v3)."""
    version: int = 3
    beads_server: BeadsServer = field(default_factory=BeadsServer)


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


def load_project_agents(dotbrain_home: Path, name: str) -> tuple[str, ...]:
    """Read declared agent workspaces from ``brainspaces/<name>/.brain/project.yaml``.

    Missing ``agents`` preserves legacy behavior by enabling both packaged agent
    workspaces. An explicit empty list disables agent workspace seeding.
    """
    import yaml

    path = _project_config_path(dotbrain_home, name)
    if not path.is_file():
        return DEFAULT_PROJECT_AGENTS

    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))

    raw_agents = data.get("agents")
    if raw_agents is None:
        return DEFAULT_PROJECT_AGENTS

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
