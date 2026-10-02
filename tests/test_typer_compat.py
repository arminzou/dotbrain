"""CLI startup and parser errors must use Typer's active Click implementation."""
import subprocess
import sys

import pytest


@pytest.mark.parametrize("block_click", [False, True])
def test_cli_with_bundled_click(block_click):
    pytest.importorskip("typer._click")
    script = f"""
import importlib.abc
import json
import sys

class BlockClick(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'click' or fullname.startswith('click.'):
            raise ModuleNotFoundError(fullname)

if {block_click!r}:
    sys.meta_path.insert(0, BlockClick())

from typer.testing import CliRunner
from dotbrain.cli import app

runner = CliRunner()
help_result = runner.invoke(app, ['--help'])
assert help_result.exit_code == 0, (help_result.output, help_result.exception)
error = runner.invoke(app, ['bootstrap', '--obsolete', '--json'])
assert error.exit_code == 2, (error.output, error.exception)
assert json.loads(error.stdout)['status'] == 'failure'
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
