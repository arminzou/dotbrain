"""Written workflow contracts; live delivery evidence belongs to the executing lead."""

from pathlib import Path

import pytest


def text(path):
    return " ".join(Path(path).read_text(encoding="utf-8").split()).replace("`", "")


ITERATION = (
    "plugin/skills/iterate-design/SKILL.md",
    "plugin/skills/iterate-design/templates/handoff-prompt.md",
)


def test_settled_all_autonomous_decomposition_needs_no_second_signoff():
    doc = text("plugin/skills/to-issues/SKILL.md")
    assert "entirely autonomous implementation graph is a valid result" in doc
    assert "create the task set without a second routine sign-off" in doc
    assert "prerequisites are investigated" in doc
    assert "a set that has not been read carefully" not in doc
    assert "user has signed off on the set" not in doc


def test_unresolved_consequential_decision_is_surfaced_before_unattended_work():
    doc = text("plugin/skills/to-issues/SKILL.md")
    assert "Before unattended work, investigate prerequisites" in doc
    assert "foreseeable human decisions with evidence and recommendations" in doc
    assert "Unresolved decisions explicitly block affected work" in doc
    assert "grill-decisions" in doc
    assert "not settled decomposition" in doc


@pytest.mark.parametrize("path", ITERATION)
def test_complete_missing_and_stale_authority_have_distinct_entry_rules(path):
    doc = text(path)
    assert "Reuse a complete applicable contract without repeat GO" in doc
    assert "execution request does not silently authorize an unapproved contract" in doc
    assert "missing or changed authority" in doc
    assert "stop affected work until resolved" in doc
    for field in (
        "scope", "branch/base", "criteria", "checks/UAT", "review expectations",
        "provider/auth and PR authority", "finite limits", "operator overrides",
    ):
        assert field in doc
    assert "execution entry" in doc.lower()
    assert "without exposing secrets" in doc
    assert "availability" in doc
    assert "never fall back to the human's credentials" in doc.lower()


@pytest.mark.parametrize("path", ITERATION)
def test_attempted_criteria_weakening_stops_with_evidence_and_recommendation(path):
    doc = text(path).lower()
    assert "never edit success criteria" in doc
    assert "stop affected work with evidence and a recommendation for grill-decisions" in doc
    assert "never weaken criteria to fit the build" in doc
    assert "new scope or authority decisions follow the same rule" in doc


@pytest.mark.parametrize("path", ITERATION)
def test_hard_stop_resume_retains_consumption_and_does_not_reauthorize(path):
    doc = text(path).lower()
    assert "resume never resets an exhausted limit or grants new authority" in doc
    for state in ("workers", "claims", "worktrees", "budgets", "per-item attempts", "review history", "hard stops"):
        assert state in doc
    assert "remaining allowance" in doc


@pytest.mark.parametrize("path", ITERATION)
def test_ready_pr_completion_preserves_human_and_reflect_boundaries(path):
    doc = text(path).lower()
    for requirement in (
        "acceptance/uat", "full suite", "exact integrated revision",
        "required code review", "readiness review", "ready-for-review pr exists",
        "human's review requested", "pr approval", "target-branch merge", "release",
        "design and epic remain active", "manually invokes terminal closeout",
        "reflect does not invoke", "another reflection report", "do not poll for merge",
    ):
        assert requirement in doc
    assert "leave that bead open" not in doc
    assert "open human-labeled review bead" not in doc


def test_shipped_closeout_requires_actual_merge_not_closed_or_ready_pr():
    doc = text("plugin/skills/close-design/SKILL.md")
    assert "disable-model-invocation: true" in doc
    assert "allow_implicit_invocation: false" in text("plugin/skills/close-design/agents/openai.yaml")
    for rule in (
        "only manually invoked by the human",
        "Closed work items alone do not establish shipment",
        "repository, delivery branch, target branch, merged state, merge commit and merge date",
        "record its URL and merge evidence",
        "A closed-unmerged PR never establishes shipment",
        "A ready or approved PR is still awaiting human merge",
        "leave the design and epic active",
        "report the gap and stop shipped closeout",
        "each needs its own supporting evidence",
    ):
        assert rule in doc
    assert "whose work items are all closed shipped" not in doc


def test_design_records_approval_separately_from_authoring_and_execution_request():
    doc = text("plugin/skills/to-design/SKILL.md")
    template = text("plugin/skills/to-design/templates/design.md")
    assert "execution authority is either recorded as approved or explicitly missing" in doc
    assert "An execution request alone does not approve a proposed contract" in doc
    assert "## Execution Contract" in template
    assert "Record human approval or explicitly mark authority unapproved" in template


@pytest.mark.parametrize("path", ITERATION)
def test_accepted_reviews_do_not_gain_routine_human_gates(path):
    doc = text(path).lower()
    for rule in ("resolved blocking findings", "recorded dispositions", "no automatic",
                 "wait for pr approval/merge"):
        assert rule in doc
    for obsolete in ("add its human label", "add human, and leave", "open human-labeled review bead"):
        assert obsolete not in doc


def test_manual_closeout_is_not_exclusive_review_closure():
    doc = text("plugin/skills/close-design/SKILL.md")
    assert "Implementation and review records may already have closed" in doc
    assert "before PR approval or merge" in doc
    assert "required verdict and evidence, resolved blocking findings, and recorded dispositions" in doc
    assert "the one close an agent may perform" not in doc


@pytest.mark.parametrize("path, required, obsolete", [
    ("docs/workflow.md", "lead closes accepted work and reviews before PR merge", "every other review waits for you"),
    ("docs/zh/workflow.md", "lead 可以在 PR 合并前关闭已验收的工作和审阅", "其他审阅都等你来关"),
    ("docs/skills.md", "lead closes accepted reviews before PR merge", "a code review closes once you merge"),
    ("docs/zh/skills.md", "lead 可在 PR 合并前关闭已通过的审阅", "其他审阅由你来关闭"),
])
def test_delivery_docs_keep_agent_closure_and_human_pr_boundary(path, required, obsolete):
    doc = text(path)
    assert required in doc
    assert obsolete not in doc
    assert "PR" in doc and ("release" in doc or "发布" in doc)
