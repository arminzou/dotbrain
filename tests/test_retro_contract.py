"""The retrospective is an agent procedure; these checks protect its written guarantees.

They do not claim native runtime execution or real-project retrospective usefulness.
"""

from pathlib import Path

import pytest
import yaml

from dotbrain import skills


ROOT = Path("plugin/skills/run-retro")


def _text(name):
    return " ".join((ROOT / name).read_text(encoding="utf-8").split())


def test_retro_is_explicitly_invocable_in_both_runtimes():
    skill = _text("SKILL.md")
    assert "disable-model-invocation: true" in skill
    metadata = yaml.safe_load((ROOT / "agents/openai.yaml").read_text(encoding="utf-8"))
    assert metadata["policy"]["allow_implicit_invocation"] is False
    assert metadata["interface"]["display_name"]
    for invocation in ("/dotbrain:run-retro", "skill picker", "external nightly job"):
        assert invocation in skill
    assert "`$run-retro` is not confirmed for plugin delivery" in skill


def test_retro_is_discovered_and_delivered_with_its_reference(dotbrain_home, tmp_path):
    assert "brain/run-retro" in skills.discover_skills(dotbrain_home / "skills")
    for runtime in ("claude", "codex"):
        destination = tmp_path / runtime / "skills"
        result = skills.link_into(dotbrain_home, destination, ["brain/run-retro"])
        assert not result.warnings
        assert (destination / "run-retro/SKILL.md").read_bytes() == (ROOT / "SKILL.md").read_bytes()
        assert (destination / "run-retro/references/retro.md").is_file()
        assert (destination / "run-retro/references/promotion.md").is_file()
        assert (destination / "run-retro/agents/openai.yaml").is_file()


@pytest.mark.parametrize("contracts", [
    ("current HEAD as the baseline", "Save and report initialization, then stop",
     "explicitly selected", "contributor scope", "repository scope", "excluded older history"),
    ("skip substantive review", "leave recurrence unchanged", "Source failures remain gaps"),
    ("successful practices alongside mistakes", "Done right", "Separate observed facts from inference"),
    ("Acquire exclusive ownership", "RETRO.md.lock", "check process creation time", "Only this writer"),
    ("Save findings before advancing", "atomically replace on the same filesystem", "Never advance past unread"),
    ("Three distinct supported dates", "eligibility, not adoption", "Public auto-delivery is disabled"),
    ("no scheduler or CLI loop runner", "no human learning entries", "checkpoint hooks", "session-start injection"),
])
def test_capture_contract(contracts):
    for contract in contracts:
        assert contract in _text("SKILL.md")


@pytest.mark.parametrize("contracts", [
    ("Reviewed through:", "Other evidence reviewed:", "Unfinished:", "plain Markdown"),
    ("parent's timestamp", "not proof that all changes were found", "an older unlinked edit can be missed"),
    ("distinct evidence dates", "Several events on one day count once", "uncertain evidence", "uncounted"),
    ("author timestamp", "rebased versions", "add no occurrence or date"),
    ("verifying ancestry", "retain the old boundary", "report the gap"),
    ("No YAML findings", "mandatory IDs", "sidecar", "meaningful evidence or known gaps"),
])
def test_notebook_cursor_and_identity_contract(contracts):
    for contract in contracts:
        assert contract in _text("references/retro.md")


def test_empty_notebook_examples_are_parseable_without_live_project_evidence():
    reference = (ROOT / "references/retro.md").read_text(encoding="utf-8")
    example = reference.split("```markdown\n", 1)[1].split("```", 1)[0]
    assert example.startswith("# Retrospectives\n")
    assert "Seen 3× (2026-04-01, 2026-04-03, 2026-04-05)" in example
    assert "Accepted:" in example
    assert "```yaml" not in reference


@pytest.mark.parametrize("path", ["docs/prompts.md", "docs/zh/prompts.md"])
def test_prompt_guides_list_retro_as_explicit_only(path):
    introduction = Path(path).read_text(encoding="utf-8").split("## ", 1)[0]
    assert "`run-retro`" in introduction
    assert "never start on their own" in introduction or "从不会自动启动" in introduction


def test_chinese_retro_description_requires_preparation_and_verified_acceptance():
    description = Path("docs/zh/skills.md").read_text(encoding="utf-8").split(
        "**`run-retro`**", 1
    )[1].split("\n- ", 1)[0]
    assert "三个不同证据日期" in description
    assert "默认只查找" in description
    assert "合入目标分支" in description
    assert "可手动调用，也可由外部定时任务调用" in description
    assert "Agent 的发现" in description


def test_only_repository_scope_offers_to_create_rules_file():
    assert "contributor scope never creates a public file" in _text("SKILL.md")
    retro = _text("references/retro.md")
    for contract in ("Repository scope only", "a contributing guide alone does not count",
                     "a contributor-scope run never creates a public file",
                     "without changing `auto-deliver`", "`Rules file: declined` (never offered again)",
                     "asks again on the next interactive run"):
        assert contract in retro
    assert "contributor scope delivers only to files that already exist upstream" in _text("references/promotion.md")
