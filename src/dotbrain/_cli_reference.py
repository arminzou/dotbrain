"""Generator for ``docs/cli-reference.md``.

The page is rendered from the Typer app's command objects: each visible command's description,
usage line, and an options table, grouped by task. ``test_cli_reference.py`` regenerates and diffs
against the committed file, failing when the CLI surface drifts. Regenerate with::

    uv run python -m dotbrain._cli_reference
"""

from __future__ import annotations

import re
from pathlib import Path

import typer

from .cli import app

_REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PATH = _REPO_ROOT / "docs" / "cli-reference.md"

# Every visible leaf command belongs to exactly one group; render() fails on one that does not, so a
# new command cannot ship without a place on the page. A group is (title, intro, guide, commands).
GROUPS: list[tuple[str, str, str | None, list[str]]] = [
    ("Setup", "Prepare a machine and check its health.", "getting-started",
     ["bootstrap", "doctor"]),
    ("Projects", "Connect code repos to Brainspaces and keep them in sync.", "wiring",
     ["wire", "refresh", "unwire", "projects list", "projects show"]),
    ("Skills and agents", "Link skills and vendor-native subagents into agent runtimes.", "skills",
     ["skills list", "skills link", "agents list", "agents link"]),
    ("Beads", "Manage the Beads tracker's state and backend.", "beads-backend",
     ["beads sync", "beads migrate", "beads list-db", "beads drop-db"]),
    ("Brain site", "Set up and run a Brain's private site.", "brain-site",
     ["site init", "site dev", "site build", "site preview"]),
    ("Internal", "Run by the plugin's hooks, not by hand.", "session-context",
     ["hook session-start"]),
]

_GUIDE_TITLES = {
    "getting-started": "Getting started",
    "wiring": "Wiring",
    "skills": "Skills",
    "beads-backend": "Beads backend",
    "brain-site": "Brain site",
    "session-context": "Session context",
}

_INTRO = """# CLI Reference

Every public `dotbrain` command, grouped by task. Run any command with `--help` for the same
information in the terminal.

Human reports group changes and problems by target, shorten home paths to `~`, and use tables
for catalogs and project inspection. Empty lists, previews, and skipped work are explicit.
Doctor shows problems and warnings first; use `doctor -v` to include every healthy check.
Colors follow terminal capabilities; redirected output stays plain.

Finite reports support `--json`: stdout contains one result with command, overall status,
per-target results, and errors. Finding severities are `info`, `warning`, and `error`; warnings
alone do not cause failure. Exit codes are `0` for success, `1` for operational failure or a
partially failed batch, and `2` for invalid invocation or selection.

JSON consumers must replace checks for `severity: advisory` with `severity: warning`.
The old severity is no longer emitted; other result fields and exit codes are unchanged.

"""


def _commands() -> dict[str, object]:
    """Visible leaf commands by path, skipping hidden commands and groups."""
    found: dict[str, object] = {}

    def walk(cmd: object, path: list[str]) -> None:
        subs = getattr(cmd, "commands", None)
        if not subs:
            found[" ".join(path)] = cmd
            return
        for name, sub in subs.items():
            if not getattr(sub, "hidden", False):
                walk(sub, path + [name])

    walk(typer.main.get_command(app), [])
    return found


def _code_options(text: str) -> str:
    """Set ``--flags`` and RST ``literals`` in help text as Markdown code."""
    text = re.sub(r"``([^`]+)``", r"`\1`", text)
    text = re.sub(r"(?<![`\w-])(--[a-z][a-z-]*)", r"`\1`", text)
    # Outside code spans, a placeholder like <name> would be read as an HTML tag by the page.
    parts = text.split("`")
    parts[::2] = [p.replace("<", "&lt;").replace(">", "&gt;") for p in parts[::2]]
    return "`".join(parts)


def _paragraphs(text: str) -> str:
    """Rejoin docstring lines wrapped for the terminal into Markdown paragraphs."""
    paras = [" ".join(line.strip() for line in p.splitlines()) for p in text.strip().split("\n\n")]
    return "\n\n".join(_code_options(p) for p in paras if p)


def _cell(text: str) -> str:
    return _code_options(text).replace("|", "\\|") or "—"


def _anchor(path: str) -> str:
    return "dotbrain-" + path.replace(" ", "-")


def _summary(cmd: object) -> str:
    help_text = (getattr(cmd, "help", None) or "").strip()
    first = _paragraphs(help_text.split("\n\n")[0]) if help_text else ""
    return first.split(". ")[0].rstrip(".") + "." if first else ""


def _render_command(path: str, cmd: object) -> str:
    params = [p for p in cmd.params if not getattr(p, "hidden", False)]
    arguments = [p for p in params if p.param_type_name == "argument"]
    options = [p for p in params if p.param_type_name == "option"]

    usage = f"dotbrain {path}"
    if options:
        usage += " [OPTIONS]"
    for arg in arguments:
        usage += f" {arg.name.upper()}" if arg.required else f" [{arg.name.upper()}]"

    out = [f"### `dotbrain {path}` {{#{_anchor(path)}}}", ""]
    if cmd.help:
        out += [_paragraphs(cmd.help), ""]
    out += ["```text", usage, "```", ""]
    if arguments:
        out += ["| Argument | Description |", "| --- | --- |"]
        out += [f"| `{a.name.upper()}` | {_cell(getattr(a, 'help', '') or '')} |" for a in arguments]
        out.append("")
    if options:
        out += ["| Option | Default | Description |", "| --- | --- | --- |"]
        for opt in options:
            name = ", ".join(f"`{o}`" for o in opt.opts + opt.secondary_opts)
            if not opt.is_flag:
                name += f" *{opt.type.name}*"
            default = "—" if opt.is_flag or opt.default in (None, "") else f"`{opt.default}`"
            out.append(f"| {name} | {default} | {_cell(opt.help or '')} |")
        out.append("")
    return "\n".join(out)


def render() -> str:
    commands = _commands()
    grouped = [path for *_, paths in GROUPS for path in paths]
    missing = sorted(set(commands) - set(grouped))
    unknown = sorted(set(grouped) - set(commands))
    if missing or unknown:
        raise ValueError(f"CLI reference groups out of date: ungrouped {missing}, unknown {unknown}")

    out = [_INTRO.rstrip("\n"), "", "## Commands at a Glance", "", "| Command | Does |", "| --- | --- |"]
    for _, _, _, paths in GROUPS:
        for path in paths:
            out.append(f"| [`{path}`](#{_anchor(path)}) | {_cell(_summary(commands[path]))} |")
    out.append("")

    for title, intro, guide, paths in GROUPS:
        out += [f"## {title}", "", intro]
        if guide:
            out[-1] += f" See [{_GUIDE_TITLES[guide]}]({guide}.md)."
        out.append("")
        out += [_render_command(path, commands[path]) for path in paths]
    return "\n".join(out).rstrip("\n") + "\n"


def main() -> None:
    REFERENCE_PATH.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {REFERENCE_PATH}")


if __name__ == "__main__":
    main()
