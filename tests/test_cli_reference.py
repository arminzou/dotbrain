"""Drift guard for docs/cli-reference.md (ADR-0034).

Regenerates the reference from the live Typer app and diffs against the committed
file. Adding or changing a CLI command/flag/help string without regenerating the
page fails here. Regenerate with: uv run python -m dotbrain._cli_reference
"""

from dotbrain import _cli_reference


def test_cli_reference_matches_app():
    committed = _cli_reference.REFERENCE_PATH.read_text()
    generated = _cli_reference.render()
    assert generated == committed, (
        "docs/cli-reference.md is stale. "
        "Regenerate with: uv run python -m dotbrain._cli_reference"
    )
