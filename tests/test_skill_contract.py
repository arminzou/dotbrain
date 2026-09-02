"""Tier 1: mechanical checks over every packaged skill.

Nothing here reads prose. Every assertion is about structure that a rewrite cannot
break by accident, so refactoring a skill's wording never turns this file red. The
rules a reviewer must judge by eye — is the description a good trigger, does an
example teach anything — deliberately have no test.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILLS = Path("plugin/skills")
SKILL_FILES = sorted(SKILLS.glob("*/SKILL.md"))
SKILL_IDS = [p.parent.name for p in SKILL_FILES]

# Over this, the loader truncates and the tail of the skill silently never arrives.
MAX_SKILL_LINES = 500


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


def test_the_set_is_not_empty():
    """A glob that silently matches nothing would make every other test vacuous."""
    assert len(SKILL_FILES) >= 10


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_frontmatter_parses_and_names_its_directory(skill: Path):
    fm = _frontmatter(skill)
    assert fm["name"] == skill.parent.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm["name"])
    assert len(fm["name"]) <= 64


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_description_survives_yaml_parsing(skill: Path):
    """An unquoted scalar containing ': ' makes the whole block unparseable, and the
    loader then drops *every* field — the skill ships with no description and never
    triggers. The failure is silent, which is why it is worth a test."""
    raw = skill.read_text(encoding="utf-8").split("---")[1]
    description = _frontmatter(skill)["description"]

    assert description.strip()
    for line in raw.splitlines():
        if line.startswith("description:"):
            value = line[len("description:") :].strip()
            if value and value[0] not in "\"'>|":
                assert ": " not in value and " #" not in value


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_skill_stays_under_the_line_cap(skill: Path):
    lines = len(skill.read_text(encoding="utf-8").splitlines())
    assert lines <= MAX_SKILL_LINES, f"{skill.parent.name} is {lines} lines"


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_invocation_choice_is_declared_in_both_runtimes(skill: Path):
    """Claude Code and Codex express this with inverted keys in different files. A skill
    declared in only one still auto-fires in the other, which is invisible from
    whichever runtime you happened to test."""
    claude = "disable-model-invocation: true" in skill.read_text(encoding="utf-8").split("---")[1]

    openai_yaml = skill.parent / "agents" / "openai.yaml"
    codex_text = openai_yaml.read_text(encoding="utf-8") if openai_yaml.exists() else ""
    codex = "allow_implicit_invocation: false" in codex_text

    assert claude == codex, (
        f"{skill.parent.name}: user-invoked in "
        f"{'Claude Code' if claude else 'Codex'} only"
    )


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_user_invoked_descriptions_carry_no_trigger_list(skill: Path):
    """With no model reach, a trigger list is dead weight: the description is read by a
    human choosing from a list, so it should summarise rather than route."""
    raw = skill.read_text(encoding="utf-8").split("---")[1]
    if "disable-model-invocation: true" in raw:
        assert "Use when" not in raw


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_relative_links_resolve(skill: Path):
    """A dangling reference 404s for every user of the skill and nothing else notices."""
    for target in re.findall(r"\]\(([^)]+)\)", skill.read_text(encoding="utf-8")):
        if target.startswith(("http", "#", "{", "$")):
            continue
        assert (skill.parent / target.split("#")[0]).exists(), f"{skill.parent.name} -> {target}"


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_no_hardcoded_home_directories(skill: Path):
    for path in [skill, *sorted(skill.parent.rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"/(Users|home)/(?!armin/repos)[a-z]", text), path


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_numbered_steps_are_sequential(skill: Path):
    """A duplicated or skipped number means an edit renumbered half a procedure."""
    numbers = [int(n) for n in re.findall(r"^### (\d+)\.", skill.read_text(encoding="utf-8"), re.M)]
    assert numbers == list(range(1, len(numbers) + 1)), f"{skill.parent.name}: {numbers}"


@pytest.mark.parametrize("skill", SKILL_FILES, ids=SKILL_IDS)
def test_linear_procedures_close_every_non_terminal_step(skill: Path):
    """The section contract in write-agent-docs/references/dotbrain-skills.md: a linear
    procedure ends each non-terminal step on a completion criterion, so the agent can
    tell done from not-done instead of drifting to the next heading.

    Loops are exempt by shape — a step that repeats cannot be 'done', so they state an
    exit condition instead."""
    text = skill.read_text(encoding="utf-8")
    if re.search(r"Return to step|ITERATING", text):
        return

    blocks = re.split(r"^### \d+\. ", text, flags=re.M)[1:]
    for block in blocks[:-1]:  # the terminal step needs no criterion
        title = block.splitlines()[0]
        assert re.search(r"^Completion:", block, re.M), f"{skill.parent.name} / {title}"
