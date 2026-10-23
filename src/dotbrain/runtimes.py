"""The agent runtimes dotbrain delivers to: identity, asset destinations, and delivery capabilities.

Every command that recognizes a runtime reads this table. A runtime absent from it is unrecognized:
commands warn about and skip it when ``project.yaml`` declares it, since a newer dotbrain on another
machine may know it, and only an explicit ``--runtime`` request for it fails.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Runtime:
    name: str  # `agents:` declaration and --runtime value
    key: str  # global target key in skills.yaml and agents.yaml
    label: str  # display name
    workspace: str  # agent workspace directory, in a checkout and under the user's home
    # Packaged native subagent definitions as (resource directory, file suffix); None when dotbrain
    # does not deliver native subagents to this runtime.
    subagents: tuple[str, str] | None = None
    hooks: bool = False  # the dotbrain plugin supplies session hooks
    default: bool = False  # a default global target
    # Environment variable that relocates the runtime's user home; dotbrain copies its plugin there
    # and opts in by the presence of that owned copy rather than by a default global target.
    home_env: str | None = None
    # Where home_env points by default, relative to the user's home (the workspace when None), and
    # the runtime's own directory below it.
    home_default: str | None = None
    home_subdir: str = ""


RUNTIMES: dict[str, Runtime] = {
    "claude": Runtime("claude", "claude-code", "Claude", ".claude", ("claude", ".md"), hooks=True, default=True),
    "codex": Runtime("codex", "codex", "Codex", ".codex", ("codex", ".toml"), hooks=True, default=True),
    "hermes": Runtime("hermes", "hermes", "Hermes", ".hermes", hooks=True, home_env="HERMES_HOME"),
    "opencode": Runtime("opencode", "opencode", "OpenCode", ".opencode", hooks=True, home_env="XDG_CONFIG_HOME",
                        home_default=".config", home_subdir="opencode"),
    "pi": Runtime("pi", "pi", "Pi", ".pi", hooks=True, home_env="PI_CODING_AGENT_DIR", home_default=".pi/agent"),
    "cursor": Runtime("cursor", "cursor", "Cursor", ".cursor", hooks=True),
}


def find(value: str) -> Runtime | None:
    """The runtime with this name or global target key."""
    return next((rt for rt in RUNTIMES.values() if value in (rt.name, rt.key)), None)


def recognized(names) -> tuple[Runtime, ...]:
    """The recognized runtimes among declared names, in order and without duplicates."""
    return tuple(dict.fromkeys(rt for rt in map(find, names) if rt is not None))


def for_workspace(workspace: str) -> Runtime:
    return next(rt for rt in RUNTIMES.values() if rt.workspace == workspace)


def select(runtime: str) -> tuple[Runtime, ...]:
    """Runtimes an explicit --runtime value selects; an unrecognized value is an error."""
    if runtime == "all":
        return tuple(RUNTIMES.values())
    found = find(runtime)
    if found is None:
        raise ValueError(f"--runtime must be {', '.join(RUNTIMES)}, or all")
    return (found,)


def default_names() -> tuple[str, ...]:
    return tuple(rt.name for rt in RUNTIMES.values() if rt.default)


def global_targets(kind: str) -> dict[str, str]:
    """Default global destinations for ``skills`` or ``agents``, keyed by global target key."""
    return {rt.key: f"~/{rt.workspace}/{kind}" for rt in RUNTIMES.values()
            if rt.default and (kind == "skills" or rt.subagents)}


def installed(rt: Runtime) -> bool:
    """The runtime's CLI is on PATH."""
    return shutil.which(command(rt)) is not None


def command(rt: Runtime) -> str:
    return "agent" if rt.name == "cursor" else rt.name


def user_dir(rt: Runtime, user_home: Path) -> Path:
    """The runtime's directory under the user's home, honoring its relocation variable."""
    override = os.environ.get(rt.home_env) if rt.home_env else None
    base = Path(override).expanduser() if override else Path(user_home) / (rt.home_default or rt.workspace)
    return base / rt.home_subdir
