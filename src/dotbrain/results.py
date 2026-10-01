"""Small finite command result contract, shared by text and JSON rendering."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import sys

import typer
from typer.core import TyperGroup
try:
    from click.exceptions import UsageError, Exit
except ImportError:
    from typer._click.exceptions import UsageError, Exit


@dataclass
class TargetResult:
    project: str | None = None
    checkout: str | None = None
    scope: str = "project"
    status: str = "success"
    changes: list[str] = field(default_factory=list)
    findings: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    data: dict | None = None


@dataclass
class CommandResult:
    command: str
    status: str = "success"
    targets: list[TargetResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def render(result: CommandResult, *, json_output: bool = False) -> None:
    if json_output:
        typer.echo(json.dumps(asdict(result), ensure_ascii=True))
        return
    lines = [f"{result.command}: {result.status}"]
    for target in result.targets:
        lines.append(f"  {target.project or target.scope}: {target.status}")
        lines.extend(f"    {item}" for item in target.changes)
        if not target.changes and target.status == "success":
            lines.append("    unchanged")
        lines.extend(f"    {item['severity']}: {item['message']}" for item in target.findings)
        lines.extend(f"    error: {item}" for item in target.errors)
    lines.extend(f"  error: {item}" for item in result.errors)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    typer.echo("\n".join(lines).encode(encoding, errors="backslashreplace").decode(encoding))


class ResultGroup(TyperGroup):
    """Keep parser failures inside the JSON contract when JSON was requested."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        ctx.meta["result_json"] = "--json" in args
        ctx.meta["result_command"] = next((arg for arg in args if not arg.startswith("-")), "dotbrain")
        try:
            return super().parse_args(ctx, args)
        except UsageError as exc:
            self._json_error(ctx, exc)
            raise

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except UsageError as exc:
            self._json_error(ctx, exc)
            raise

    @staticmethod
    def _json_error(ctx: click.Context, exc: click.UsageError) -> None:
        if ctx.meta.get("result_json"):
            render(CommandResult(str(ctx.meta.get("result_command", "dotbrain")), "failure", errors=[exc.format_message()]), json_output=True)
            raise Exit(2)
