from pathlib import Path

import pytest

from dotbrain import brainspaces


@pytest.mark.parametrize("path", [
    "plugin/skills/iterate-design/SKILL.md",
    "plugin/skills/iterate-design/templates/handoff-prompt.md",
])
def test_handoff_delivery_keeps_draft_notification_and_final_gates(path):
    text = " ".join(Path(path).read_text(encoding="utf-8").split()).replace("`", "")
    for rule in (
        "agent identity distinct from the human reviewer",
        "ruleset requiring a reviewed PR and dismissing stale approvals",
        "first item integrates and passes its integrated check",
        "open a draft PR at the first push",
        "Push after each integrated item that passes its integrated check",
        "no progress comments",
        "no body updates between the first push and FINAL",
        "whole handoff ends BLOCKED",
        "one PR comment that @-mentions the human with an audience-safe reason",
        "Check existing comments and the delivery record before posting or retrying",
        # Keyed to the stop: a guard keyed to the handoff hid a second stop after a resume.
        "Each blocked stop gets one mention",
        "keyed to this stop's revision and reason",
        "a new stop after a resume gets its own mention",
        "runtime's own notification where available, otherwise the session report",
        "At FINAL, write the Verification section",
        "draft PR ready, and request the human's review",
        "Never mark it ready with a blocked scoped item",
        "Do not create a placeholder commit",
    ):
        assert rule in text, (path, rule)


def test_seeded_brain_carries_loop_invariants(dotbrain_home: Path, tmp_path: Path):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    doc = (brainspace / ".brain" / "DOTBRAIN.md").read_text(encoding="utf-8")
    doc = " ".join(doc.split())

    assert "Working in loops" in doc
    assert "criteria are human-owned" in doc
    assert "hard stop" in doc
    assert "report blocked with the attempt trail" in doc
    assert "end the loop and go to the human" in doc
    assert "PR authorization" in doc
    assert "ready-for-review PR" in doc
    assert "a draft PR at the first push" in doc
    assert "one mention of the human for each blocked stop" in doc
    assert "explicit `GO`" in doc
    assert "review gate is human-owned at close" in doc
    assert "a clean agent verdict does not close it" in doc
    assert "observing the human's merge of its recorded PR" in doc
    assert "citing that PR and merge commit" in doc
    assert "A PR closed unmerged leaves it open" in doc
    assert "A `simplify` bead does not close on merge" in doc
    assert "the active design doc is the spec" in doc
    assert "Reread the spec every iteration" in doc


def test_workflows_share_branch_and_landing_guards():
    paths = (
        Path("src/dotbrain/resources/templates/brain/DOTBRAIN.md"),
        Path("plugin/skills/dotbrain/SKILL.md"),
        Path("plugin/skills/manage-work-graph/SKILL.md"),
        Path("plugin/skills/run-execution/SKILL.md"),
    )
    for path in paths:
        text = " ".join(path.read_text(encoding="utf-8").split())
        for guard in (
            "dedicated branch and land through a review surface",
            "branch diff where the project hosts no PRs",
            "never into `main`",
            "may span several bounded executions",
            "Local HITL landing requires explicit human instruction, recorded by the lead",
            "it is never the default",
            "Merge stays human-owned",
        ):
            assert guard in text, path
        assert "before pushing or opening a PR" in text, path
        assert "needs no branch" not in text, path


def test_landing_rule_sits_with_workflow_rules_not_loop_invariants():
    """Landing binds the HITL workflow too, so it cannot live under the loop invariants, which
    bind only iterative or autonomous execution."""
    landing = "Both the HITL and handoff workflows run on a dedicated branch"
    for path in (
        Path("src/dotbrain/resources/templates/brain/DOTBRAIN.md"),
        Path("plugin/skills/dotbrain/SKILL.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert text.index("## Rules") < text.index(landing) < text.index("## Working in loops"), path
    owner = Path("plugin/skills/run-execution/SKILL.md").read_text(encoding="utf-8")
    assert (
        owner.index("## Workflow and execution mode")
        < owner.index("Both workflows run on a dedicated branch")
        < owner.index("## Agent team")
    )


def test_seeded_brain_distinguishes_main_checkout_and_worktree_wiring(
    dotbrain_home: Path, tmp_path: Path
):
    brainspace = tmp_path / "brainspace"
    brainspace.mkdir()

    brainspaces.seed_brain(brainspace, dotbrain_home)

    doc = " ".join(
        (brainspace / ".brain" / "DOTBRAIN.md").read_text(encoding="utf-8").split()
    )

    assert "main checkout" in doc
    assert "`dotbrain wire`" in doc
    assert "Git worktree" in doc
    assert "Git metadata" in doc
    assert "without changing registration or declarations" in doc
    assert "`dotbrain refresh`" in doc
    assert "`dotbrain unwire`" in doc
    assert "# dotbrain-managed-agent: v1" in doc
