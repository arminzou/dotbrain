"""Read Claude-format plugin installations shared by plugin health and Cursor discovery."""
import json
from pathlib import Path

from dotbrain import resource_loader


def is_current(entry: dict) -> bool:
    """Compare a Dotbrain registry entry with the packaged plugin version."""
    with resource_loader.plugin_tree() as source:
        version = json.loads((source / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))["version"]
    return entry.get("version") == version


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


def enabled_installs(scopes: tuple[Path, ...], *, include_stale: bool = True) -> list[tuple[str, Path]]:
    """Cursor's selection for workspace scopes followed by the user home."""
    if not scopes:
        return []

    def settings(scope, filename):
        path = scope / ".claude" / filename
        return (json.loads(path.read_text(encoding="utf-8")).get("enabledPlugins") or {}) if path.is_file() else {}

    def normalized(path):
        return str(path).replace("\\", "/").rstrip("/") or "/"

    user = settings(scopes[-1], "settings.json")
    workspaces = [(normalized(scope.resolve()), {**settings(scope, "settings.json"),
                                                **settings(scope, "settings.local.json")})
                  for scope in scopes[:-1]]
    disabled = {name for _, enabled in workspaces for name, value in enabled.items() if value is False}
    result = []
    for name, entries in installed(scopes[-1] / ".claude").items():
        if name in disabled:
            continue
        chosen = None
        # A matching enabled project/local installation wins in registry order, then user fallback.
        for workspace, enabled in workspaces:
            if enabled.get(name) is True:
                chosen = next((entry for entry in entries if entry.get("scope") in ("project", "local")
                               and entry.get("projectPath") and normalized(entry["projectPath"]) == workspace), None)
            if chosen is None and user.get(name) is True:
                chosen = next((entry for entry in entries if entry.get("scope") == "user"), None)
            if chosen is not None:
                break
        if not workspaces and user.get(name) is True:
            chosen = next((entry for entry in entries if entry.get("scope") == "user"), None)
        if chosen is not None:
            if name == "dotbrain@dotbrain" and not include_stale and not is_current(chosen):
                continue
            result.append((name, Path(chosen["installPath"]).expanduser()))
    return result
