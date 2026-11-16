"""Skill selections changed through ``skills link`` / ``unlink`` entries."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from dotbrain import skill_sources
from dotbrain.cli import app

runner = CliRunner()


@pytest.mark.parametrize("text, values, expected", [
    ("version: 4\n", ["a/b"], "version: 4\nskills:\n  - a/b\n"),
    ("version: 4", ["a/b"], "version: 4\nskills:\n  - a/b\n"),
    ("version: 3\nskills: [a/b]  # mine\nsubagents: []\n", ["a/b", "c"], "version: 3\nskills: [a/b, c]\nsubagents: []\n"),
    ("skills:\n  # pinned for work\n  - a/b\n\n# trailing\nversion: 4\n", ["a/b", "c"],
     "skills:\n  # pinned for work\n  - a/b\n  - c\n\n# trailing\nversion: 4\n"),
    ("skills:\n- a/b\n- c\nversion: 4\n", ["c"], "skills:\n- c\nversion: 4\n"),
    ("skills:\n    - a/b\nversion: 4\n", [], "skills: []\nversion: 4\n"),
    ("# skills:\n#   - x\nversion: 4\n", ["odd: name"], '# skills:\n#   - x\nversion: 4\nskills:\n  - "odd: name"\n'),
])
def test_set_list_changes_only_the_list(text: str, values: list[str], expected: str):
    assert skill_sources.set_list(text, "skills", values, "f.yaml") == expected


@pytest.mark.parametrize("text", ["skills: one\n", "skills: [a,\n  b]\n", "skills:\n  key: 1\n"])
def test_set_list_refuses_layouts_it_cannot_edit_exactly(text: str):
    with pytest.raises(ValueError, match="edit it by hand"):
        skill_sources.set_list(text, "skills", ["a", "c"], "f.yaml")


CONFIG = "# my settings\nversion: 4\n\n# delivered everywhere\nskills:\n  - custom/example-workflow  # daily\n"


@pytest.fixture
def configured(dotbrain_home: Path, claude_codex_on_path) -> Path:
    (dotbrain_home / "config.yaml").write_text(CONFIG, encoding="utf-8")
    return dotbrain_home


def link(home: Path, *args: str):
    return runner.invoke(app, ["skills", *args, "--scope", "global", "--home", str(home)])


def test_link_entries_select_then_deliver_and_unlink_prunes(configured: Path, tmp_path: Path):
    delivered = tmp_path / "user-home" / ".claude" / "skills" / "discovery-test"

    result = link(configured, "link", "misc/discovery-test")

    assert result.exit_code == 0, result.output
    assert (configured / "config.yaml").read_text(encoding="utf-8") == CONFIG + "  - misc/discovery-test\n"
    assert delivered.is_symlink()

    result = link(configured, "unlink", "misc/discovery-test")

    assert result.exit_code == 0, result.output
    assert (configured / "config.yaml").read_text(encoding="utf-8") == CONFIG
    assert not delivered.exists() and not delivered.is_symlink()


@pytest.mark.parametrize("command, entry, message", [
    ("link", "misc/missing", "skill not found: misc/missing"),
    ("unlink", "misc/discovery-test", "not selected: misc/discovery-test"),
])
def test_invalid_entries_leave_the_selection_unchanged(configured: Path, command: str, entry: str, message: str):
    result = link(configured, command, entry)

    assert result.exit_code != 0
    assert message in result.output
    assert (configured / "config.yaml").read_text(encoding="utf-8") == CONFIG


def test_link_entries_refuse_all_projects(configured: Path):
    result = runner.invoke(app, ["skills", "link", "misc/discovery-test", "--all", "--home", str(configured)])

    assert result.exit_code == 2
    assert "use --scope global for every project" in result.output
    assert yaml.safe_load((configured / "config.yaml").read_text(encoding="utf-8"))["skills"] == ["custom/example-workflow"]
