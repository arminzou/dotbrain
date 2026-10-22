"""Read Claude-format plugin installations shared by plugin health and Cursor discovery."""
import json
from pathlib import Path


def installed(runtime_home: Path) -> dict[str, list[dict]]:
    registry = runtime_home / "plugins/installed_plugins.json"
    if not registry.is_file():
        return {}
    data = json.loads(registry.read_text(encoding="utf-8"))
    plugins = data.get("plugins") or {}
    result = {}
    for name, entries in plugins.items():
        if isinstance(entries, dict):
            entries = [entries]
        if isinstance(entries, list):
            result[name] = [entry for entry in entries
                            if isinstance(entry, dict) and isinstance(entry.get("installPath"), str)]
    return result


def enabled_installs(scopes: tuple[Path, ...]) -> list[tuple[str, Path]]:
    """Enabled installations, with earlier scopes overriding later (project before user)."""
    enabled = {}
    for scope in reversed(scopes):
        for filename in ("settings.json", "settings.local.json"):
            settings = scope / ".claude" / filename
            if settings.is_file():
                enabled.update(json.loads(settings.read_text(encoding="utf-8")).get("enabledPlugins") or {})
    result = []
    for scope in scopes:
        for name, entries in installed(scope / ".claude").items():
            if enabled.get(name) is not True:
                continue
            for entry in entries:
                project = entry.get("projectPath")
                if project and Path(project).resolve() not in {s.resolve() for s in scopes}:
                    continue
                result.append((name, Path(entry["installPath"]).expanduser()))
    return result
