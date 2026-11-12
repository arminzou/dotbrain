"""Drift guard for docs/cli-reference.md.

Regenerates the reference from the live Typer app and diffs against the committed
file. Adding or changing a CLI command/flag/help string without regenerating the
page fails here. Regenerate with: uv run python -m dotbrain._cli_reference
"""

import importlib.util

from typer.testing import CliRunner

from dotbrain import _cli_reference, resource_loader
from dotbrain.cli import app


def test_cli_reference_matches_app():
    committed = _cli_reference.REFERENCE_PATH.read_text(encoding="utf-8")
    generated = _cli_reference.render()
    assert generated == committed, (
        "docs/cli-reference.md is stale. "
        "Regenerate with: uv run python -m dotbrain._cli_reference"
    )


def test_retired_site_surface_is_absent():
    result = CliRunner().invoke(app, ["site", "--help"])
    assert result.exit_code == 2
    assert "No such command" in result.output
    assert importlib.util.find_spec("dotbrain.site") is None
    resources = {path.as_posix() for path, _ in resource_loader.iter_resource_files("")}
    assert not any(path.startswith(("site/", "templates/brain/site/")) for path in resources)
