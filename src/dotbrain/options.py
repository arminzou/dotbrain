"""Reusable leaf-command option definitions."""
from pathlib import Path
from typing import Annotated
import typer

from dotbrain import runtimes

HomeOption = Annotated[Path | None, typer.Option("--home", help="Override the private data root.")]
RuntimeOption = Annotated[str, typer.Option("--runtime", help=f"Filter runtimes: {', '.join(runtimes.RUNTIMES)}, or all.")]
JsonOption = Annotated[bool, typer.Option("--json", help="Emit one structured result.")]
