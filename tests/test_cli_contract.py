"""Finite CLI invocation errors obey the clean-break result contract."""
import json

import pytest
from typer.testing import CliRunner

from dotbrain.cli import app


@pytest.mark.parametrize("args", [
    ["wire", "--name", "sample"],
    ["wire", "--all"],
    ["wire", "--beads-database", "sample"],
    ["refresh", "--name", "sample"],
    ["refresh", "--repo-base", "anywhere"],
    ["refresh", "--dry-run"],
    ["doctor", "--scope", "global"],
    ["doctor", "--all", "--project", "sample"],
    ["unwire", "--archive"],
    ["unwire", "--delete"],
    ["unwire", "--no-repo"],
    ["unwire", "--dry-run"],
    ["bootstrap", "--target", "codex"],
    ["skills", "link", "--scope", "all"],
    ["agents", "link", "--runtime", "claude-code"],
    ["skills", "link", "--scope", "global", "--project", "sample"],
    ["beads", "load"],
    ["migrate-beads"],
    ["list-beads-db"],
    ["drop-beads-db", "sample"],
    ["update"],
])
def test_retired_or_conflicting_invocation_is_one_json_error(args, tmp_path, monkeypatch):
    home = tmp_path / "data"
    monkeypatch.setenv("DOTBRAIN_HOME", str(home))
    result = CliRunner().invoke(app, [*args, "--json"])
    assert result.exit_code == 2, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "failure"
    assert report["errors"]
    assert not home.exists()
