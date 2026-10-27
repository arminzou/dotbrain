"""Per-runtime evidence table for the no-model container UAT.

Each row records how a runtime is installed in ``uat/Dockerfile`` and which model-free, login-free
commands show what dotbrain delivered to it. A listing's ``proves`` is one of ``skills``, ``agents``,
``plugin-hooks`` or ``convention``; a runtime with no usable listing has ``listings == ()`` and is
covered by the install check plus the hook only. All commands ran in the built image (probed with
the versions below), with no login, credentials or model call.
"""

from __future__ import annotations

from dataclasses import dataclass

# The plugin runtimes install the packaged plugin from a local marketplace: copy the checkout's
# `.claude-plugin/` and `plugin/` into MARKETPLACE first. No network or login is involved.
MARKETPLACE = "/opt/market"


@dataclass(frozen=True)
class Listing:
    argv: tuple[str, ...]
    proves: str  # skills | agents | plugin-hooks | convention
    note: str = ""
    setup: tuple[tuple[str, ...], ...] = ()  # commands to run first, in the checkout


@dataclass(frozen=True)
class Runtime:
    name: str
    version: str
    install: str  # the Dockerfile step, for the record
    listings: tuple[Listing, ...] = ()
    note: str = ""  # why listings is empty or limited

    @property
    def binary(self) -> str:
        return "agent" if self.name == "cursor" else self.name

    @property
    def plugin_steps(self) -> tuple[tuple[str, ...], ...]:
        return tuple(step for listing in self.listings for step in listing.setup)

    @property
    def install_hook_only(self) -> bool:
        return not self.listings


_CLAUDE_PLUGIN = (("claude", "plugin", "marketplace", "add", MARKETPLACE),
                  ("claude", "plugin", "install", "dotbrain@dotbrain"))
_CODEX_PLUGIN = (("codex", "plugin", "marketplace", "add", MARKETPLACE),
                 ("codex", "plugin", "add", "dotbrain@dotbrain"))

RUNTIMES: tuple[Runtime, ...] = (
    Runtime("claude", "2.1.311", "npm install --global @anthropic-ai/claude-code@2.1.311", (
        Listing(("claude", "plugin", "list"), "plugin-hooks", "dotbrain@dotbrain, scope user, status enabled",
                _CLAUDE_PLUGIN),
        Listing(("claude", "plugin", "details", "dotbrain"), "plugin-hooks",
                "its component inventory: the SessionStart, Stop and SessionEnd hooks"),
        # A local slash command: runs logged out and makes no model call.
        Listing(("claude", "-p", "/context"), "agents",
                "the Custom Agents table lists the `dotbrain-<role>` agents and the Skills table the selected "
                "skill, all delivered by bootstrap/refresh; the plugin's own skills (`dotbrain:*`) are not "
                "evidence of delivery"),
    )),
    Runtime("codex", "0.164.0", "npm install --global @openai/codex@0.164.0", (
        Listing(("codex", "debug", "prompt-input"), "skills",
                "skill roots and names, including the selected skill refresh delivered; does NOT include the "
                "SessionStart hook's convention text"),
        Listing(("codex", "plugin", "list"), "plugin-hooks", "plugin installed and enabled", _CODEX_PLUGIN),
    ), "the checkout's .codex/agents are not listed by any command"),
    Runtime("opencode", "1.18.35", "npm install --global opencode-ai@1.18.35", (
        Listing(("opencode", "debug", "skill"), "skills", "JSON with each skill's name and location"),
        Listing(("opencode", "debug", "config"), "plugin-hooks", "the resolved config names the dotbrain plugin file"),
    ), "`opencode agent list` shows built-in agents only: dotbrain delivers none to OpenCode"),
    Runtime("pi", "1.4.0", "npm install --global @earendil-works/pi-coding-agent@1.4.0", (),
            "`pi list` shows packages only (none for the dotbrain extension); `pi --list-models` and "
            "`pi -p /skills` need a provider login"),
    Runtime("cursor", "2026.10.22-27dcf5f",
            "download the pinned agent-cli tarball, sha256-checked, link it as `agent`", (),
            "`agent status` is `Not logged in`; `agent models|agents|rules|skills` need auth; `agent mcp list` "
            "and `agent about` run but do not show delivered skills or hooks"),
    Runtime("hermes", "v0.22.0+119 (0e427d788d253630d38a3a51cd76849e73cd6925)",
            "the official install.sh pinned with --commit; no package-registry release", (
        Listing(("hermes", "plugins", "list", "--plain", "--no-bundled"), "plugin-hooks",
                "the dotbrain plugin: enabled, source user"),
    ), "`hermes skills list` shows built-in skills only; `hermes hooks list` covers shell hooks, not plugins"),
)


def runtime(name: str) -> Runtime:
    return next(r for r in RUNTIMES if r.name == name)
