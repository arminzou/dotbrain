"""Drift guard for docs/cli-reference.md.

Regenerates the reference from the live Typer app and diffs against the committed
file. Adding or changing a CLI command/flag/help string without regenerating the
page fails here. Regenerate with: uv run python -m dotbrain._cli_reference
"""

import sys

import pytest

from dotbrain import _cli_reference


@pytest.mark.skipif(
    sys.platform == "win32",
    reason=(
        "Rich's Console can never confirm VT support on a captured subprocess pipe (no real "
        "console handle exists to query), so on Windows it always renders panel borders in the "
        "legacy_windows box style (square corners, narrower width) instead of the default rounded "
        "style — a rendering-detection artifact of this generator's subprocess-capture approach, "
        "not a difference in the CLI's actual behavior. Content correctness is still covered by "
        "the ubuntu/macos legs; this drift guard is a docs-maintenance convenience, not part of "
        "the platform-support surface."
    ),
)
def test_cli_reference_matches_app():
    committed = _cli_reference.REFERENCE_PATH.read_text()
    generated = _cli_reference.render()
    assert generated == committed, (
        "docs/cli-reference.md is stale. "
        "Regenerate with: uv run python -m dotbrain._cli_reference"
    )
