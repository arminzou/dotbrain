"""Reusable leaf-command option definitions."""
from pathlib import Path
from typing import Annotated
import typer

HomeOption = Annotated[Path | None, typer.Option("--home", help="Override the private data root.")]
RuntimeOption = Annotated[str, typer.Option("--runtime", help="Filter runtimes: claude, codex, or all.")]
JsonOption = Annotated[bool, typer.Option("--json", help="Emit one structured result.")]
