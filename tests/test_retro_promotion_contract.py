"""Written promotion guarantees, not native execution or real PR delivery."""

from pathlib import Path

import pytest


ROOT = Path("plugin/skills/run-retro")


def text(name):
    return " ".join((ROOT / name).read_text(encoding="utf-8").split())


@pytest.mark.parametrize("contracts", [
    ("Three distinct supported days", "copied reports", "do not invent dates", "Personal preferences stay"),
    ("Missing settings mean disabled", "destinations", "auto-deliver: false", "No public edits"),
    ("proposal and destination", "Select the best fit", "do not expand the allowlist"),
    ("Compare accepted rules and open target-branch PRs", "Several findings can share one proposal", "Keep provenance only"),
    ("before repeating an action", "retry never adds another rule", "pending", "recorded branch"),
    ("read-only", "even when capture found nothing new", "one bounded", "no all-history scan"),
    ("actual merged PR", "matching repository/base", "merge commit and time", "rule is not adoption"),
    ("Approval, unmerged closure", "never establish acceptance", "actual merge date", "unchanged lookup"),
    ("already accepted", "no edit or PR", "Never relabel a pending or rejected proposal"),
    ("closed-unmerged", "new explicit direction", "do not automatically erase a public rule"),
])
def test_public_rule_promotion_guards(contracts):
    for contract in contracts:
        assert contract in text("references/promotion.md")


def test_promotion_runs_after_checkpoint_even_without_new_capture():
    skill = text("SKILL.md")
    assert skill.index("### 4. Save") < skill.index("### 5. Suggest") < skill.index("### 6. Report")
    assert "references/promotion.md" in skill
    assert "not the `pr` skill" in skill
    reference = text("references/pr.md")
    assert "## Proposed rules" in reference
    assert "## Review check" in reference
    assert "## Existing guidance" in reference


@pytest.mark.parametrize("path", ["docs/skills.md", "docs/zh/skills.md", "plugin/skills/README.md"])
def test_retro_catalog_mentions_public_edit_and_read_only_reconciliation(path):
    catalog = Path(path).read_text(encoding="utf-8")
    paragraph = next(part for part in catalog.split("\n- ") if "`run-retro`" in part or "[run-retro]" in part)
    assert "RULES.md" in paragraph
    assert "PR" in paragraph
    assert "read-only" in paragraph or "只读" in paragraph
