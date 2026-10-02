"""Small finite command result contract, shared by text and JSON rendering."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json

import typer
from typer.core import TyperCommand, TyperGroup
try:
    from typer._click import Context
    from typer._click.exceptions import UsageError
except ImportError:
    from click import Context
    from click.exceptions import UsageError


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


def render(result: CommandResult, *, json_output: bool = False, preview: bool = False) -> None:
    if json_output:
        typer.echo(json.dumps(asdict(result), ensure_ascii=True))
        return
    from dotbrain import presentation
    if result.command in {"projects list", "projects show"} and not result.errors:
        presentation.render_projects(result)
    elif result.command in {"skills list", "agents list"} and result.status == "success":
        presentation.render_catalog(result)
    else:
        presentation.render_operation(result, preview=preview)


class HelpCommand(TyperCommand):
    def get_help(self, ctx):
        from dotbrain.presentation import render_help
        return render_help(self, ctx)


class HelpGroup(TyperGroup):
    def get_help(self, ctx):
        from dotbrain.presentation import render_help
        return render_help(self, ctx)


class HelpTyper(typer.Typer):
    def __init__(self, **kwargs):
        kwargs.setdefault("cls", HelpGroup)
        super().__init__(**kwargs)

    def command(self, *args, **kwargs):
        kwargs.setdefault("cls", HelpCommand)
        return super().command(*args, **kwargs)


class ResultGroup(HelpGroup):
    """Keep parser failures inside the JSON contract when JSON was requested."""

    def parse_args(self, ctx: Context, args: list[str]) -> list[str]:
        ctx.meta["result_json"] = "--json" in args
        ctx.meta["result_command"] = next((arg for arg in args if not arg.startswith("-")), "dotbrain")
        try:
            return super().parse_args(ctx, args)
        except UsageError as exc:
            self._json_error(ctx, exc)
            raise

    def invoke(self, ctx: Context):
        try:
            return super().invoke(ctx)
        except UsageError as exc:
            self._json_error(ctx, exc)
            raise

    @staticmethod
    def _json_error(ctx: Context, exc: UsageError) -> None:
        if ctx.meta.get("result_json"):
            render(CommandResult(str(ctx.meta.get("result_command", "dotbrain")), "failure", errors=[exc.format_message()]), json_output=True)
            raise typer.Exit(2)
