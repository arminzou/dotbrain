import json
from pathlib import Path

from dotbrain import owned_copy, resource_loader
from dotbrain.skills import LinkResult

PLUGIN = "dotbrain"
KIND = "plugin"
ENABLE = "agy plugin enable dotbrain"


def plugin_dir(config_dir: Path) -> Path:
    return config_dir / "plugins" / PLUGIN


def skills_dir(config_dir: Path) -> Path:
    return config_dir / "skills"


def owned(config_dir: Path) -> bool:
    return owned_copy.owned(plugin_dir(config_dir))


def state(config_dir: Path) -> str:
    return owned_copy.state(plugin_dir(config_dir), resource_loader.ANTIGRAVITY_PLUGIN_FILES)


def activation(config_dir: Path) -> str:
    path = config_dir / "config.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8").removeprefix("\ufeff"))
    except FileNotFoundError:
        return "enabled"
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    for key in ("plugins", PLUGIN, "enabled"):
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected an object containing {key}")
        if key not in value:
            return "enabled"
        value = value[key]
    if not isinstance(value, bool):
        raise ValueError(f"{path}: plugins.dotbrain.enabled must be a boolean")
    return "enabled" if value else "disabled"


def deliver(config_dir: Path, *, run=None) -> LinkResult:
    target = plugin_dir(config_dir)
    result = LinkResult()
    current = state(config_dir)
    if current == "foreign":
        result.warnings.append(f"{target} exists and was not created by dotbrain; skipping")
    elif current != "current":
        preserved = owned_copy.install(target, resource_loader.ANTIGRAVITY_PLUGIN_FILES)
        if preserved:
            result.notices.append(f"modified or ambiguous retired resources preserved at {preserved}; inspect before removing")
        result.linked.append(f"antigravity/plugins/{PLUGIN}")
    return result


def remove(config_dir: Path, *, run=None) -> LinkResult:
    target = plugin_dir(config_dir)
    return LinkResult(pruned=[str(target)] if owned_copy.remove(target) else [])
