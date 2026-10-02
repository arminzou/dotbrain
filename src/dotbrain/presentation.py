"""Human CLI layouts; machine results and exit decisions stay with their callers."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import os
import re
import sys

from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

from dotbrain.adopter_repos import abbrev_home


def console() -> Console:
    return Console(highlight=False, markup=False, force_terminal=sys.stdout.isatty())


def render_help(command, ctx) -> str:
    output = console()
    if ctx.terminal_width:
        output.width = ctx.terminal_width
    if ctx.color is False:
        output = Console(width=output.width, color_system=None, highlight=False, markup=False)

    def rows(title, entries):
        if not entries:
            return
        output.print()
        output.print(Text(title + ":", style="bold green"))
        if output.width < 65:
            for name, description in entries:
                output.print(Padding(Text(name.strip(), style="bold cyan"), (0, 0, 0, 2)))
                output.print(Padding(Text(description), (0, 0, 0, 4)))
            return
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold cyan", overflow="fold", max_width=max(12, output.width // 2))
        grid.add_column(overflow="fold")
        for name, description in entries:
            grid.add_row(Text(name), Text(description))
        output.print(Padding(grid, (0, 0, 0, 2)))

    with output.capture() as captured:
        if command.help:
            output.print(Text(command.help.split("\f", 1)[0].strip()))
            output.print()
        pieces = command.collect_usage_pieces(ctx)
        usage = " ".join([ctx.command_path, *pieces]).replace("COMMAND [ARGS]...", "<COMMAND>")
        usage = re.sub(r"(?<= )([A-Z][A-Z0-9_]*)(?=\s|\.|$)", r"<\1>", usage)
        output.print(Text.assemble(("Usage: ", "bold green"), (usage, "bold cyan")))
        if hasattr(command, "list_commands"):
            entries = []
            for name in command.list_commands(ctx):
                child = command.get_command(ctx, name)
                if child is not None and not child.hidden:
                    description = child.short_help or (child.help or "").split("\f", 1)[0].split("\n\n", 1)[0]
                    entries.append((name, " ".join(description.split())))
            rows("Commands", entries)
        arguments, options = [], []
        for param in command.get_params(ctx):
            record = param.get_help_record(ctx)
            if record:
                name, description = record
                # Put short aliases first and delimit value placeholders like uv.
                name = ", ".join(sorted(name.split(", "), key=lambda part: not part.startswith("-") or part.startswith("--")))
                name = re.sub(r"(?<= )([A-Z][A-Z0-9_]*)$", r"<\1>", name)
                if hasattr(param, "opts") and any(opt.startswith("-") for opt in param.opts):
                    options.append(("    " + name if name.startswith("--") else name, description))
                else:
                    arguments.append((name, description))
        rows("Arguments", arguments)
        rows("Global options" if ctx.parent is None else "Options", options)
        if command.epilog:
            output.print()
            output.print(Text(command.epilog))
    return "\n".join(line.rstrip() for line in captured.get().splitlines())


def shorten(value: object, checkout: str | None = None) -> str:
    message = str(value)
    for root, replacement in ((checkout, "."), (str(Path.home()), "~")):
        if root:
            # Match path boundaries, including the native and portable Windows spelling.
            for spelling in dict.fromkeys((root, root.replace("\\", "/"))):
                message = re.sub(re.escape(spelling.rstrip("/\\") or spelling) + r"(?=[/\\]|$)",
                                 lambda match: replacement, message,
                                 flags=re.IGNORECASE if os.name == "nt" else 0)
    return message


def text(value: object, output: Console, style: str = "", checkout: str | None = None) -> Text:
    value = shorten(value, checkout)
    return Text(value.encode(output.encoding, errors="backslashreplace").decode(output.encoding), style=style)


def line(output: Console, value: object = "", style: str = "", checkout: str | None = None, indent: int = 0) -> None:
    for part in str(value).splitlines() or [""]:
        content = text(part, output, style, checkout)
        output.print(Padding(content, (0, 0, 0, indent), expand=False) if indent else content)


def symbol(output: Console, success: bool) -> str:
    value = "✓" if success else "✗"
    try:
        value.encode(output.encoding)
        return value
    except UnicodeEncodeError:
        return "[ok]" if success else "[x]"


def table(output: Console, columns: list[str], rows: list[list[object]]) -> None:
    # Stack fields on narrow terminals instead of squeezing paths into tiny columns.
    if output.width < 65:
        for row in rows:
            line(output, row[0], "bold")
            for name, value in zip(columns[1:], row[1:]):
                line(output, f"{name}: {value.plain if isinstance(value, Text) else value}", indent=2)
            line(output)
        return
    grid = Table(box=None, padding=(0, 1), header_style="bold", show_edge=False)
    for index, name in enumerate(columns):
        grid.add_column(name, overflow="fold", style="bold" if index == 0 else "")
    for row in rows:
        grid.add_row(*(value if isinstance(value, Text) else text(value, output) for value in row))
    output.print(grid)


def _messages(output: Console, messages: list[str], severity: str, checkout: str | None = None) -> None:
    for message, count in Counter(messages).items():
        suffix = f" ({count} occurrences)" if count > 1 else ""
        line(output, f"{severity}: {message}{suffix}", "red" if severity == "error" else "yellow", checkout, 2)


def _human_status(target) -> str:
    if target.status == "success" and any(f["message"] == "Brain-only project: no checkout assets" for f in target.findings):
        return "skipped"
    return target.status


def render_operation(result, *, preview: bool = False) -> None:
    output = console()
    label = {"success": "Completed", "partial": "Partially completed", "failure": "Failed"}[result.status]
    if preview:
        label = "Preview" if result.status == "success" else "Preview · " + label
    outcome_style = "red" if result.status == "failure" else "yellow" if result.status == "partial" else "cyan" if preview else "green"
    output.print(Text.assemble(text(result.command, output, "bold"), text(" · " + label, output, outcome_style)))
    _messages(output, result.errors, "error")
    if result.command == "beads list-db" and result.targets:
        names = result.targets[0].data["databases"]
        if names:
            table(output, ["Database"], [[name] for name in names])
        line(output, f"{len(names)} databases" if names else "No databases found", "dim")
        return
    for target in sorted(result.targets, key=lambda item: item.status != "failure"):
        line(output)
        label = target.project or target.scope
        if target.data and "database" in target.data:
            label += " · " + target.data["database"]
        if target.checkout:
            label += " · " + abbrev_home(Path(target.checkout))
        elif target.project:
            label += " · Brain-only"
        line(output, label, "bold")
        _messages(output, target.errors, "error", target.checkout)
        for finding in target.findings:
            line(output, f"{finding['severity']}: {finding['message']}",
                 "yellow" if finding["severity"] == "warning" else "dim", target.checkout, 2)
        groups: dict[str, list[str]] = {}
        for change in target.changes:
            category = "Changes"
            if change.startswith("shared Brain:"):
                category, change = "Shared Brain", change.removeprefix("shared Brain:").strip()
            elif change.startswith("shared tracker:"):
                category, change = "Shared tracker", change.removeprefix("shared tracker:").strip()
            elif any(prefix in change for prefix in (".codex/", "codex/")):
                category = "Codex resources"
            elif any(prefix in change for prefix in (".claude/", "claude-code/", "claude/")):
                category = "Claude resources"
            groups.setdefault(category, []).append(change)
        for name, changes in groups.items():
            if len(groups) > 1:
                line(output, name, "dim", indent=2)
            for change in changes:
                line(output, change, "cyan" if result.command == "site build" else "", checkout=target.checkout, indent=4 if len(groups) > 1 else 2)
        if target.data and target.data.get("pre_count") is not None:
            line(output, f"Issues before: {target.data['pre_count']}; after: {target.data['post_count']}", "dim", indent=2)
        if not target.changes and not target.errors and not target.findings:
            line(output, "No actions planned" if preview else "Already up to date", "dim", indent=2)
        if _human_status(target) == "skipped":
            line(output, "Skipped", "dim", indent=2)
        elif len(result.targets) > 1 and target.status == "failure":
            line(output, "Failed", "red", indent=2)
    if len(result.targets) > 1:
        counts = Counter(_human_status(item) for item in result.targets)
        labels = {"success": "planned" if preview else "completed", "failure": "failed", "skipped": "skipped"}
        line(output, " · ".join(f"{count} {labels[name]}" for name, count in counts.items()), "dim")


def _runtimes(names) -> str:
    return ", ".join(sorted({{"claude": "Claude", "claude-code": "Claude", "codex": "Codex"}.get(name, name) for name in names})) or "none"


def render_catalog(result) -> None:
    output = console()
    target = result.targets[0]
    kind = result.command.split()[0]
    line(output, kind.capitalize() + (f" · Selection for {target.project}" if target.project else " · Available"), "bold")
    rows = target.data["assets"]
    columns = ["Name", *(["Selected"] if target.project else []), "Runtime", "Source"]
    rendered = []
    for row in rows:
        sources = row.get("sources", {_runtimes(row.get("runtimes", [])): row.get("source", "")})
        for runtime, source in sources.items():
            rendered.append([row["name"], *(["yes" if row["selected"] else "no"] if target.project else []),
                             _runtimes([runtime]) if "sources" in row else runtime, source])
    footer = []
    if rendered and len({row[-2] for row in rendered}) == 1:
        footer.append("Runtimes: " + rendered[0][-2])
        columns.remove("Runtime")
        for row in rendered:
            row.pop(-2)
    # A shared source prefix is display context; each source remains reconstructible.
    prefixes = [row[-1].replace("\\", "/") for row in rendered]
    if prefixes and all(value.startswith("bundled:") for value in prefixes):
        prefix = "bundled:agents/"
    elif prefixes and all(Path(value).is_absolute() for value in prefixes):
        try:
            prefix = os.path.commonpath([str(Path(value).parent) for value in prefixes]).replace("\\", "/").rstrip("/") + "/"
        except ValueError:
            prefix = ""
    else:
        prefix = ""
    if prefix and all(value.startswith(prefix) for value in prefixes) and (prefix.startswith("bundled:") or len(Path(prefix).parts) > 1):
        footer.append("Source root: " + prefix.rstrip("/"))
        for row, value in zip(rendered, prefixes):
            row[-1] = value.removeprefix(prefix)
    if rendered:
        table(output, columns, rendered)
    noun = kind[:-1] if len(rows) == 1 else kind
    line(output, " · ".join([f"{len(rows)} {noun} available", *footer]) if rows else f"No {kind} found", "dim")


def _wiring(record) -> str:
    if record["brain_only"]:
        return "No checkout"
    problems = [f"{name} {status}" for name, status in record["wiring"].items() if status != "healthy"]
    return ", ".join(problems) or "Healthy"


def render_projects(result) -> None:
    output = console()
    if result.command == "projects list":
        records = [target.data for target in result.targets]
        valid = [record for record in records if "error" not in record]
        shared_runtime = bool(valid) and len(valid) == len(records) and len({_runtimes(row["runtimes"]) for row in valid}) == 1
        shared_tracker = bool(valid) and len(valid) == len(records) and len({row["beads"]["mode"] for row in valid}) == 1
        columns = ["Project", "Checkout", "Wiring", *([] if shared_runtime else ["Runtimes"]), *([] if shared_tracker else ["Tracker"])]
        rows = []
        for record in records:
            failure = "error" in record
            wiring = "Declaration error" if failure else _wiring(record)
            rows.append([record["project"], abbrev_home(Path(record["checkout"])) if record["checkout"] else "Brain-only",
                         text(wiring, output, "red" if failure or wiring not in {"Healthy", "No checkout"} else "green"),
                         *([] if shared_runtime else ["unknown" if failure else _runtimes(record["runtimes"])]),
                         *([] if shared_tracker else ["unknown" if failure else record["beads"]["mode"]])])
        if rows:
            table(output, columns, rows)
        else:
            line(output, "No projects found", "dim")
        for target in result.targets:
            if target.errors:
                line(output, target.project, "bold red")
                _messages(output, target.errors, "error", target.checkout)
        footer = [f"{len(records)} projects"]
        if shared_runtime:
            footer.append("Runtimes: " + _runtimes(valid[0]["runtimes"]))
        if shared_tracker:
            footer.append("Tracker: " + valid[0]["beads"]["mode"])
        line(output, " · ".join(footer), "dim")
        return
    for target in result.targets:
        record = target.data
        line(output, target.project, "bold")
        table(output, ["Property", "Value"], [["Checkout", record["checkout"] or "Brain-only"],
              ["Runtimes", _runtimes(record["runtimes"])], ["Tracker", record["beads"]["mode"]], ["Wiring", _wiring(record)]])
        line(output, "Paths", "bold")
        table(output, ["Path", "Location"], [["Brainspace", record["brainspace"]],
              *[[name, value or "disabled"] for name, value in record["paths"].items()]])
        line(output, "Settings", "bold")
        def settings(values, prefix=""):
            for key, value in values.items():
                name = prefix + key
                if isinstance(value, dict) and value:
                    yield from settings(value, name + ".")
                else:
                    yield [name, ", ".join(map(str, value)) if isinstance(value, list) else str(value)]
        table(output, ["Setting", "Value"], list(settings(record["settings"])))
        line(output, "Selections", "bold")
        table(output, ["Selection", "Names"], [["Configured skills", ", ".join(record["skills"]["configured"]) or "none"],
              ["Effective skills", ", ".join(record["skills"]["effective"]) or "none"],
              ["Additional subagents", ", ".join(record["subagents"]) or "none"]])


def render_doctor(report, *, verbose: bool = False) -> None:
    output = console()
    groups = [("Machine", None, report.machine)] + [(name, report.checkouts.get(name), findings) for name, findings in report.projects.items()]
    counts = Counter(finding.status for _, _, findings in groups for finding in findings)
    line(output, "Doctor", "bold")
    def counted(count, noun):
        return f"{count} {noun}{'' if count == 1 else 's'}"
    passed = counted(counts["ok"], "check") + " passed"
    line(output, counted(counts["error"], "problem") + " · " + counted(counts["warn"], "warning") + " · " + passed, "dim")
    statuses = [("error", "red"), ("warn", "yellow")] + ([("ok", "green")] if verbose else [])
    for status, style in statuses:
        for name, checkout, findings in groups:
            selected = [finding for finding in findings if finding.status == status]
            if not selected:
                continue
            line(output)
            marker = symbol(output, False) if status == "error" else "!" if status == "warn" else symbol(output, True)
            line(output, f"{marker} {name}" + (" · " + abbrev_home(Path(checkout)) if checkout else ""), "bold " + style)
            combined = {}
            for finding in selected:
                match = re.match(r"^(claude-code|claude|codex): (.*)$", finding.message)
                key = (match[2] if match else finding.message, finding.suggestion)
                combined.setdefault(key, []).append(match[1] if match else "")
            for (message, suggestion), runtimes in combined.items():
                prefix = _runtimes(runtimes) + ": " if all(runtimes) else ""
                line(output, prefix + message, checkout=checkout, indent=2)
                if suggestion:
                    line(output, ("Fix: " if status == "error" else "Next: ") + suggestion, "cyan", checkout, 2)
    if not verbose:
        line(output)
        line(output, f"{symbol(output, True)} {passed}. Use -v for details.", "dim")
