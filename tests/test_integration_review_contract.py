"""Integration acceptance and recovery contracts; no live runtime qualification."""

from pathlib import Path

import pytest


SKILLS = Path("plugin/skills")


def text(relative: str) -> str:
    return " ".join((SKILLS / relative).read_text(encoding="utf-8").split())


def test_provisional_integration_is_not_acceptance_or_dependent_release():
    execution = text("run-execution/SKILL.md")
    for rule in (
        "provisionally integrated, then reviewed as a coherent group at an exact integrated revision",
        "not launch waves or whole epics",
        "Review promptly when accepting a completed prerequisite unlocks dependent work",
        "Provisional integration closes no items and releases no dependents",
        "Combined checks, required independent review, each member's acceptance evidence, and resolved human gates at the exact integrated revision",
        "a base containing its accepted integrated result",
        "changed patch or integration context affecting acceptance or review/check coverage",
        "needs refreshed evidence before closure",
        "An earlier `APPROVE` does not cover a stale revision",
    ):
        assert rule in execution
    assert "review before integration" not in execution


def test_group_records_preserve_recoverable_member_evidence_without_new_ledger():
    record = text("run-execution/references/execution-record.md")
    for rule in (
        "no scheduler ledger or group bead",
        "On every member, record a stable group reference, all included item IDs",
        "group base/head (or HEAD and diff fingerprint)",
        "reviewer identity and report reference",
        "per-member verdict and acceptance coverage",
        "combined check commands/results with revision and environment",
        "unresolved coverage gaps",
        "durable comment reference and finding ID",
        "mark prior evidence stale",
        "charge failures to affected members",
        "not automatically to every group member or a new group counter",
        "append `Held group` on every member",
    ):
        assert rule in record


def test_provisional_groups_leave_delivery_clean_and_promote_exact_accepted_heads():
    execution = text("run-execution/SKILL.md")
    for rule in (
        "Create an isolated group candidate branch from the accepted delivery head",
        "keep the agreed delivery branch at its last accepted revision",
        "Fast-forward the agreed delivery branch with `git merge --ff-only <group-branch>`",
        "confirm its head equals the reviewed and checked revision",
        "If the delivery head advances before promotion, rebase or rebuild the group candidate",
        "refresh review and combined checks before promotion",
        "Preserve held group branches and worktrees",
        "independent groups start from the accepted delivery head and can be promoted without the held changes",
        "rather than reset or rewrite the delivery branch",
    ):
        assert rule in execution
    assert "fast-forward the target with `git merge --ff-only <item-branch>`" not in execution
    record = text("run-execution/references/execution-record.md")
    for rule in (
        "candidate branch/worktree and integrated revisions, accepted delivery branch/head",
        "After fast-forward promotion, record `Accepted` on each member",
        "its before/after heads",
        "confirm the delivery head equals the reviewed and checked revision before closure",
        "Preserve held group candidate branches/worktrees separately from the accepted delivery head",
        "never reset or rewrite the delivery branch to recover",
    ):
        assert rule in record


def test_single_item_incomplete_final_coverage_requires_whole_branch_review():
    gate = text("review-gate/SKILL.md")
    assert (
        "A single-item branch uses its item/integration review as final code review only when it "
        "covers the whole final diff; otherwise arrange a whole-branch review"
    ) in gate
    assert "review the uncovered final range" not in gate


def test_failed_groups_are_held_and_independent_continuation_requires_containment():
    execution = text("run-execution/SKILL.md")
    for rule in (
        "In both workflows, hold a failed or incompletely covered integration group and its dependents",
        "only with evidence of accepted bases and isolated integration candidates",
        "cannot silently become another item's base",
        "while retaining the held contribution and unrelated accepted work",
        "smaller groups requires a new explicit review boundary and fresh combined acceptance evidence",
        "Serialize shared repair with an explicit file/resource boundary",
        "recorded before/after revisions and checks",
        "If containment cannot be proven, stop dispatch and integration",
        "shared-state compromise or unresolved scope, safety, or acceptance decisions stop the entire execution",
        "Cancellation remains a whole-execution stop",
        "Preserve candidates, worktrees, claims, original workers, budgets, attempt counts, and review history",
        "replacements require confirmed termination and retain those limits",
        "Only the human authorizes more attempts",
    ):
        assert rule in execution
    assert "The HITL workflow instead pauses" not in execution


@pytest.mark.parametrize("path", [
    "review-gate/SKILL.md",
    "iterate-design/SKILL.md",
    "iterate-design/templates/handoff-prompt.md",
])
def test_final_review_reuse_requires_complete_revision_bound_independent_coverage(path):
    document = text(path)
    for rule in (
        "Reuse the final integration review only",
        "exact final head",
        "all scoped items",
        "interactions",
        "need not be fresh",
        "whole-branch review",
        "stale coverage",
    ):
        assert rule in document
    assert "fresh reviewer that ran none" not in document
    assert "simplify" in document
    assert "readiness" in document
    assert "human" in document


def test_lead_records_review_and_final_human_gate_is_preserved():
    gate = text("review-gate/SKILL.md")
    assert "reviewer returns a complete report to the lead without tracker writes" in gate
    assert "lead records findings and provenance on the review bead" in gate
    assert "review reuse removes no human gate" in gate
    assert "a clean agent result does not close it" in gate
    assert "A PR closed unmerged leaves the bead open" in gate
    assert "A `simplify` bead does not close on merge" in gate


def test_graph_closure_and_handoff_delivery_require_accepted_integration():
    graph = text("manage-work-graph/SKILL.md")
    assert "Provisional integration closes no items and releases no dependents" in graph
    assert "dependent bases contain accepted prerequisites" in graph
    for path in ("iterate-design/SKILL.md", "iterate-design/templates/handoff-prompt.md"):
        document = text(path)
        assert "Push after each accepted integration group" in document
        assert "hold failed or uncovered contributions" in document
        assert "accepted bases with isolated" in document
        assert "accepted delivery branch after candidate promotion; held group branches stay local" in document
        assert "2 by default" not in document
