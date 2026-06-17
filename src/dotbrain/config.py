"""Config store: global ``config.yaml`` + per-project ``project.yaml`` (ADR-0030).

``config.yaml`` (data root, version 3) holds global infrastructure defaults
(``beads.server``).  ``projects/<name>/project.yaml`` (version 1) holds
per-project identity (beads mode, database, remote).  The old
``dotbrain.yaml`` is read transparently as a fallback when ``config.yaml``
is absent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
    """Effective per-project beads config from ``project.yaml``."""
    mode: str = "embedded"  # embedded | server | none
    remote: str = ""
    database: str = ""


@dataclass
class DotbrainConfig:
    """Parsed representation of config.yaml (schema v3)."""
    version: int = 3
    beads_server: BeadsServer = field(default_factory=BeadsServer)


# ---------------------------------------------------------------------------
# Global config (config.yaml)
# ---------------------------------------------------------------------------

def _config_path(dotbrain_root: Path) -> Path:
    return Path(dotbrain_root) / "config.yaml"


def _old_config_path(dotbrain_root: Path) -> Path:
    return Path(dotbrain_root) / "dotbrain.yaml"


def load_config(dotbrain_root: Path) -> DotbrainConfig:
    """Load ``config.yaml``; transparently reads old ``dotbrain.yaml`` as fallback."""
    import yaml  # deferred: only needed when this function is called

    path = _config_path(dotbrain_root)
    if not path.is_file():
        old = _old_config_path(dotbrain_root)
        if old.is_file():
            return _parse_old_format(old)

    if not path.is_file():
        return DotbrainConfig()

    data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    server = (data.get("beads") or {}).get("server") or {}
    return DotbrainConfig(
        version=int(data.get("version", 3)),
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

    data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    server = (data.get("beads") or {}).get("server") or {}
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
# Per-project config (projects/<name>/project.yaml)
# ---------------------------------------------------------------------------

def _project_config_path(dotbrain_root: Path, name: str) -> Path:
    return Path(dotbrain_root) / "projects" / name / "project.yaml"


def default_beads_mode(dotbrain_root: Path) -> str:
    """Effective default beads mode for a project that doesn't set one.

    Follows infrastructure: a configured shared sql-server (``beads.server.host``
    in config.yaml) makes ``server`` the default, so every wired project uses it;
    otherwise the default is ``embedded``. Projects override per-project by
    setting ``mode`` explicitly in ``project.yaml``.
    """
    return "server" if load_config(dotbrain_root).beads_server.host else "embedded"


def load_project_config(dotbrain_root: Path, name: str) -> ProjectBeads:
    """Read ``projects/<name>/project.yaml``, resolving defaults.

    The default mode follows :func:`default_beads_mode` (server when a shared
    server is configured, else embedded); database defaults to the project name.
    Old ``dotbrain.yaml`` ``projects:<name>`` entries take precedence over a
    default (seeded) ``project.yaml``.
    """
    import yaml

    default_mode = default_beads_mode(dotbrain_root)

    # Read project.yaml if it exists.
    file_beads: ProjectBeads | None = None
    path = _project_config_path(dotbrain_root, name)
    if path.is_file():
        data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
        beads = data.get("beads") or {}
        file_beads = ProjectBeads(
            mode=str(beads.get("mode", default_mode)),
            remote=str(beads.get("remote", "")),
            database=str(beads.get("database", name)),
        )

    # Check old dotbrain.yaml — its explicit entries override a default project.yaml.
    old = _old_config_path(dotbrain_root)
    if old.is_file():
        data: dict[str, Any] = yaml.safe_load(old.read_text()) or {}
        projects = data.get("projects") or {}
        if name in projects:
            entry = (projects[name] or {}).get("beads") or {}
            old_beads = ProjectBeads(
                mode=str(entry.get("mode", default_mode)),
                remote=str(entry.get("remote", "")),
                database=str(entry.get("database", name)),
            )
            # If project.yaml exists and deviates from defaults, it wins.
            # If project.yaml is all defaults (seeded template), old format wins.
            if file_beads is not None and _is_beads_deviation(dotbrain_root, name, file_beads):
                return file_beads
            return old_beads

    if file_beads is not None:
        return file_beads
    return ProjectBeads(mode=default_mode, database=name)


def load_project_skills(dotbrain_root: Path, name: str) -> tuple[str, ...]:
    """Read the operator's per-project skill list from project.yaml ``skills:``.

    Returns deduped extras with the brain-coupled required core excluded; the
    tool always force-wires the required core on top of these.
    """
    import yaml

    from dotbrain import skills

    path = _project_config_path(dotbrain_root, name)
    if not path.is_file():
        return ()
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        return ()
    return skills._clean(data.get("skills"), exclude=skills.project_baseline())


def write_project_config(dotbrain_root: Path, name: str, beads: ProjectBeads) -> str | None:
    """Write ``projects/<name>/project.yaml``. Returns a log line or None if unchanged."""
    import yaml

    path = _project_config_path(dotbrain_root, name)
    existing = load_project_config(dotbrain_root, name)

    if (existing.mode == beads.mode
            and existing.remote == beads.remote
            and existing.database == (beads.database or name)):
        return None

    resolved = ProjectBeads(
        mode=beads.mode,
        remote=beads.remote,
        database=beads.database if beads.database != name else "",
    )

    doc: dict[str, Any] = {"beads": {"mode": resolved.mode}}
    if resolved.remote:
        doc["beads"]["remote"] = resolved.remote
    if resolved.database:
        doc["beads"]["database"] = resolved.database

    # This rewrite drops comments; carry the operator's per-project skills across
    # so a beads-deviation write never strands them.
    existing_skills = load_project_skills(dotbrain_root, name)
    if existing_skills:
        doc["skills"] = list(existing_skills)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(doc, default_flow_style=False, sort_keys=False))
    return f"wrote beads config for {name} to {path}"


# ---------------------------------------------------------------------------
# Public mutation helpers (used by wire / migrate / workflows)
# ---------------------------------------------------------------------------

def record_project_beads(dotbrain_root: Path, name: str, beads: ProjectBeads) -> str | None:
    """Persist a project's beads config in project.yaml.

    Only writes when the config deviates from the resolved defaults (mode differs
    from the config-driven default mode, or a custom remote/database).  A default
    call never overwrites a manual declaration (e.g. mode: none) that already
    exists.  Returns a log line when the file changed, else None.
    """
    if not _is_beads_deviation(dotbrain_root, name, beads):
        return None
    return write_project_config(dotbrain_root, name, beads)


def migrate_legacy_skill_manifest(dotbrain_root: Path, name: str) -> str | None:
    """Fold a legacy ``.brain/agents/skills.yaml`` into project.yaml and remove it.

    The per-project skill list used to live in a tool-managed manifest under
    ``.brain/agents/``; it now lives in ``project.yaml`` ``skills:``. This folds any
    extras across (without losing them) and deletes the stale file. Idempotent.
    """
    import yaml

    from dotbrain import skills

    legacy = Path(dotbrain_root) / "projects" / name / ".brain" / "agents" / "skills.yaml"
    if not legacy.is_file():
        return None

    data = yaml.safe_load(legacy.read_text()) or {}
    extras: tuple[str, ...] = ()
    if isinstance(data, dict):
        extras = skills._clean(data.get("skills", data.get("extra")), exclude=skills.project_baseline())
    if extras:
        _append_project_skills(dotbrain_root, name, extras)
    legacy.unlink()

    suffix = f" ({len(extras)} skill(s))" if extras else ""
    return f"migrated legacy skills manifest for {name} into project.yaml{suffix}"


def _append_project_skills(dotbrain_root: Path, name: str, extras: tuple[str, ...]) -> None:
    """Append a ``skills:`` block to project.yaml, preserving existing content.

    No-op when the file already declares ``skills:`` (the operator owns it then).
    """
    import re

    path = _project_config_path(dotbrain_root, name)
    block = "skills:\n" + "".join(f"  - {skill}\n" for skill in extras)
    if path.is_file():
        text = path.read_text()
        if re.search(r"(?m)^skills:", text):
            return
        if text and not text.endswith("\n"):
            text += "\n"
        path.write_text(text + "\n" + block)
        return
    header = "# Per-project skills, linked on top of the brain-coupled required core.\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + block)


def _is_beads_deviation(dotbrain_root: Path, name: str, beads: ProjectBeads) -> bool:
    return (
        beads.mode != default_beads_mode(dotbrain_root)
        or bool(beads.remote)
        or bool(beads.database and beads.database != name)
    )


def remove_project_beads(dotbrain_root: Path, name: str) -> str | None:
    """Drop a project's per-project config. Returns a log line or None if absent."""
    path = _project_config_path(dotbrain_root, name)
    if path.is_file():
        os.remove(path)
        return f"removed project.yaml for {name}"

    # Old-format cleanup: remove from dotbrain.yaml projects section
    old = _old_config_path(dotbrain_root)
    if old.is_file():
        import yaml
        data: dict[str, Any] = yaml.safe_load(old.read_text()) or {}
        projects = data.get("projects")
        if projects and name in projects:
            return _remove_from_old_projects_section(old, name)

    return None


def _remove_from_old_projects_section(path: Path, name: str) -> str | None:
    """Drop ``projects.<name>`` from a legacy dotbrain.yaml, preserving other text."""
    import yaml

    data: dict[str, Any] = yaml.safe_load(path.read_text()) or {}
    projects: dict[str, Any] = data.get("projects") or {}
    if name not in projects:
        return None
    del projects[name]

    text = path.read_text()
    kept: list[str] = []
    in_section = False
    in_entry = False
    for line in text.splitlines():
        if in_entry:
            if line and not line[0].isspace():
                in_entry = False
            else:
                continue
        if in_section:
            if line.startswith(f"  {name}:"):
                in_entry = True
                continue
            if line and not line[0].isspace():
                in_section = False

        if line.startswith("projects:"):
            in_section = True
            continue
        kept.append(line)

    while kept and not kept[-1].strip():
        kept.pop()
    out = "\n".join(kept) + "\n"
    if projects:
        out += "\n" + _render_old_projects_section(projects)
    path.write_text(out)
    return f"removed beads deviation for {name} from dotbrain.yaml"


def _render_old_projects_section(projects: dict[str, Any]) -> str:
    lines = ["projects:"]
    for pname in sorted(projects):
        entry = projects[pname]
        beads = (entry or {}).get("beads") or {}
        lines.append(f"  {pname}:")
        lines.append("    beads:")
        mode = beads.get("mode", "embedded")
        if mode != "embedded":
            lines.append(f"      mode: {mode}")
        remote = beads.get("remote", "")
        if remote:
            lines.append(f"      remote: {remote}")
        database = beads.get("database", "")
        if database:
            lines.append(f"      database: {database}")
    return "\n".join(lines) + "\n"
