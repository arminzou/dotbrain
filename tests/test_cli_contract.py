"""CLI parser and selector errors report JSON without creating a data root."""
import json

import pytest
from typer.testing import CliRunner

from dotbrain.cli import app


@pytest.mark.parametrize("args", [
    ["unknown-command"],
    ["bootstrap", "--unknown-option"],
    ["bootstrap", "--runtime", "invalid"],
    ["skills", "unlink"],
    ["doctor", "--all", "--project", "sample"],
    ["skills", "link", "--scope", "global", "--project", "sample"],
])
def test_invalid_invocation_is_one_json_error_without_writes(args, tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    result = CliRunner().invoke(app, [*args, "--json"])
    assert result.exit_code == 2, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "failure"
    assert report["errors"]
    assert not home.exists()
