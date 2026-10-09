"""Guard dispatch boundaries; these contracts do not qualify live runtime fan-out."""

from pathlib import Path

import pytest


EXECUTION = Path("plugin/skills/run-execution")


def text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_capacity_is_finite_and_does_not_expand_authorized_scope():
    skill = text(EXECUTION / "SKILL.md")
    for rule in (
        "authorized item count and active writing-worker cap are separate",
        "Unless the human specifies the cap, select and announce a finite cap",
        "actual runtime capacity, resource isolation, and stated limits",
        "capacity consumed by the lead and required review and verification",
        "Fill available writing slots from eligible ready items inside the fixed scope",
        "refill as workers finish",
        "Reduce concurrency when integration, checks, or shared resources become bottlenecks",
        "Human gates and explicit budgets and caps remain binding",
    ):
        assert rule in skill
    assert "2 by default" not in skill
    assert "Uncapped" not in skill


def test_file_overlap_requires_behavioral_separation_and_actual_isolation():
    skill = text(EXECUTION / "SKILL.md")
    for rule in (
        "Overlapping files are allowed when behavioral responsibilities are separable in separate worktrees",
        "an unsettled shared interface is a prerequisite to settle before dispatch",
        "Give simultaneous writers separate worktrees and mutable outputs or resource instances",
        "schedule genuinely shared resources exclusively",
        "Actual worktrees, claims, resource ownership, and exclusive scheduling establish isolation",
        "Serialize integration into the target and route needed rebases to the original workers",
        "behavioral responsibility, and known file overlap",
    ):
        assert rule in skill
    assert "ownership does not overlap" not in skill


def test_candidate_completion_frees_only_writing_capacity():
    skill = text(EXECUTION / "SKILL.md")
    assert "frees a writing slot without accepting its item or releasing its claim" in skill
    assert "Resume a worker for repair only when a writing slot is available" in skill
    assert "releases writing capacity only, never dependents" in skill
    assert "A work item has at most one active worker" in skill
    assert "distinct Beads actor per worker" in skill
    assert "never weaken the contract to fit the runtime" in skill
    assert "3 consecutive failed checks on one checkpoint" in skill


@pytest.mark.parametrize("path", [
    "run-execution/SKILL.md",
    "iterate-design/SKILL.md",
    "iterate-design/templates/handoff-prompt.md",
])
def test_fixed_scope_can_include_waiting_dependents_without_bypassing_readiness(path):
    document = text(Path("plugin/skills") / path)
    for rule in (
        "The set may include waiting dependents",
        "actual ready frontier after prerequisite acceptance and closure",
        "with human gates resolved and capacity available",
    ):
        assert rule in document
    assert "finite batch of ready items" not in document
    if path.startswith("iterate-design/"):
        assert "Refill eligible slots as prerequisites close while independent siblings continue" in document
        assert "Never add items silently to an execution already under way" in document


@pytest.mark.parametrize("runtime", ["codex", "claude-code"])
def test_runtime_mechanisms_preserve_dispatch_and_recovery_boundaries(runtime: str):
    reference = text(EXECUTION / "references" / f"{runtime}.md")
    assert "capacity for the lead and required review and verification" in reference
    assert "overlapping files" in reference
    assert "shared resources exclusively" in reference
    assert "eligible ready item in the fixed scope" in reference
    assert "writing slot before resume" in reference
    assert "serialize target integration" in reference
    assert "higher-fan-out" in reference
    if runtime == "codex":
        assert "Count direct CLI writers and nested writers together" in reference
        assert "Native conversation IDs and assigned paths do not prove isolation" in reference
        assert "completion and termination are established" in reference
    else:
        assert "actual isolated worktree" in reference
        assert "confirmed completed candidate" in reference
        assert "retain its claim and agent ID" in reference
