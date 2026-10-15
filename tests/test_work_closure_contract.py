"""Source contracts specify closure; native execution must prove runtime compliance."""

from pathlib import Path

import pytest


def text(path):
    return " ".join(Path(path).read_text(encoding="utf-8").split())


RECORD = "plugin/skills/manage-work-graph/references/review-beads.md"


@pytest.mark.parametrize("mode, verdict", [("code", "APPROVE"), ("readiness", "READY")])
def test_clean_verdict_closes_only_with_current_evidence_and_resolved_blockers(mode, verdict):
    record = text(RECORD)
    assert f"`{mode}`" in record and f"`{verdict}`" in record
    for rule in (
        "all required acceptance evidence at the exact integrated revision",
        "Blocking findings must be resolved; filing or declining a blocker does not resolve it",
        "Other findings require recorded dispositions",
        "Confirm the current integrated head matches before native `bd close`",
        "After a changed integrated head, refresh review and checks before closure",
        "After a closed `APPROVE`/`READY` review, a later head change (repair, PR feedback, or rebase) requires a new review record or reopening before that review counts as current evidence",
        "Preserve the assignee: close under its actor, naming the lead in the reason",
    ):
        assert rule in record


@pytest.mark.parametrize("failure", ["`CHANGES`", "`NOT-READY`", "pending verdicts",
                                     "failed, missing, or stale evidence"])
def test_failing_or_uncovered_review_holds_affected_work(failure):
    record = text(RECORD)
    assert failure in record
    assert "hold affected work and reviews open" in record
    assert "Do not add the `human` label merely because a bead is a review" in record
    assert "explicit gate for a genuine unresolved decision" in record


def test_simplify_dispositions_are_complete_but_never_pr_readiness_blockers():
    record = text(RECORD)
    for rule in (
        "every finding is applied, filed as its own item, or declined with a reason",
        "Record follow-up IDs and reasons",
        "clean pass has zero findings to disposition",
        "an open simplify bead never holds the PR or `FINAL`",
    ):
        assert rule in record


@pytest.mark.parametrize("path", [RECORD,
    "plugin/skills/run-execution/references/execution-record.md"])
def test_required_uat_gaps_hold_work_without_automatic_human_testing(path):
    record = text(path)
    for rule in ("revision, environment, agreed user journeys, actual checks/results, and gaps",
                 "unexercised journey is a gap, never a pass",
                 "automatic request for the human to check", "missing UAT"):
        assert rule.lower() in record.lower()
    assert "remaining limits" in record


@pytest.mark.parametrize("path", [
    "plugin/skills/run-execution/SKILL.md",
    "plugin/skills/manage-work-graph/SKILL.md",
    "plugin/skills/review-gate/SKILL.md", RECORD,
    "src/dotbrain/resources/templates/brain/DOTBRAIN.md",
])
def test_closure_never_merges_or_automatically_closes_design(path):
    record = text(path)
    assert "never merges the target branch" in record
    assert "never automatically invokes `close-design`" in record
    assert "human-gated by definition" not in record
    assert "run `close-design` before moving on" not in record


def test_authorized_shaping_preserves_scope_criteria_and_resume_limits():
    execution = text("plugin/skills/run-execution/SKILL.md")
    graph = text("plugin/skills/manage-work-graph/SKILL.md")
    assert "shapes the item through `manage-work-graph` before execution starts" in execution
    assert "preserving approved scope, acceptance criteria, and finite limits" in execution
    assert "worker replacement and resume never reset a failure streak" in execution
    assert "A writing worker keeps its claim until the item closes" in execution
    assert "Acceptance criteria remain human-owned" in graph
    assert "adjust dependencies or acceptance when the graph is wrong" not in graph
