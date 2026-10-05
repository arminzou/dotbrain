"""Tier 2: the few rules whose silent removal would be dangerous.

One test per invariant, asserted against the single place that owns it. Where a
dependent skill must not restate the rule, that is checked as containment — the
owner has it, the dependent points at it — rather than by pinning either wording.

The loop invariants live in test_loop_rules.py, which already owns them against the
same canonical file; they are not repeated here. Everything else about how these
skills read is reviewed by eye, not by equality check.

If you are adding a test here, the bar is: someone could delete this rule in a
plausible refactor, and the consequence would be a leak, a lost guarantee, or an
irreversible action taken without a human.
"""

from __future__ import annotations

import re
from pathlib import Path

SKILLS = Path("plugin/skills")
CONVENTION = Path("src/dotbrain/resources/templates/brain/DOTBRAIN.md")


def _text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_public_private_boundary_is_inward_only():
    """The Brain is never mirrored outward. Losing this leaks private design history
    into a public repo, which is not recoverable by editing the file afterwards."""
    convention = _text(CONVENTION)

    assert re.search(r"Brain never is", convention)
    assert re.search(r"[Nn]ever mirror Brain content", convention)


def test_no_skill_creates_a_public_issue_from_private_work():
    """Public issues are intake, never a projection of the private graph. The only
    place allowed to create one is the public triage surface itself."""
    for skill_md in sorted(SKILLS.glob("*/*.md")) + sorted(SKILLS.glob("*/*/*.md")):
        if skill_md.parts[2] == "triage-public":
            continue
        assert "gh issue create" not in skill_md.read_text(encoding="utf-8"), skill_md


def test_private_identifiers_never_reach_a_public_pr():
    """Brain paths, ADR numbers and spec-ids in a PR body leak the private layer to
    anyone reading the repo. The rule has one home; iterate-design points at it."""
    owner = _text(SKILLS / "manage-work-graph/references/public-provenance.md")
    loop = _text(SKILLS / "iterate-design/SKILL.md")

    assert "Verification" in owner
    assert re.search(r"`\.brain/` paths, ADR numbers", owner)
    assert "manage-work-graph" in loop, "iterate-design must point at the owner"
    assert not re.search(r"`\.brain/` paths, ADR numbers", loop), "second copy will drift"


def test_automation_handoff_authorizes_only_a_ready_for_review_pr():
    """Opening a PR is safe only under the human's bounded handoff contract; merging stays theirs."""
    convention = _text(CONVENTION)
    loop = _text(SKILLS / "iterate-design/SKILL.md")

    assert "explicit `GO`" in convention
    assert "PR authorization" in convention
    assert "ready-for-review PR" in convention
    assert "Preflight contract" in loop
    assert "ready-for-review PR" in loop
    assert "does not authorize merge, deploy, publish, dependency changes" in loop


def test_adr_offer_test_is_single_sourced():
    """The three-part test decides when any skill offers an ADR. Two copies means two
    different bars for writing a decision record."""
    owners = [
        p
        for p in SKILLS.rglob("*.md")
        if "hard to reverse" in p.read_text(encoding="utf-8").lower()
    ]

    assert [p.name for p in owners] == ["adr-format.md"]
    for skill in ("grill-decisions", "review-architecture"):
        assert "references/adr-format.md" in (SKILLS / skill / "SKILL.md").read_text(
            encoding="utf-8"
        )


def test_design_lifecycle_vocabulary_is_one_field_set():
    """A per-doc invented field makes a sweep across .brain/designs/ impossible to run,
    and the sweep is how a stale `active` doc is ever found."""
    convention = _text(CONVENTION)
    stamper = _text(SKILLS / "close-design/SKILL.md")

    for field in ("lifecycle:", "started:", "ended:", "extends:", "residue:"):
        assert field in convention, f"{field} missing from the convention"
        assert field in stamper, f"{field} missing from close-design"
    for state in ("draft", "active", "shipped", "abandoned", "superseded"):
        assert state in convention


def test_lead_is_the_single_writer_during_delegated_execution():
    """Every worktree reaches the same Brain and tracker. If workers may reshape the graph or
    edit the design doc, concurrent writers silently overwrite each other's shared state."""
    owner = _text(SKILLS / "execute-workflow/SKILL.md")
    assert "the lead is the only agent that edits the active design doc" in owner
    assert "A worker writes only its own claim" in owner
    graph = _text(SKILLS / "manage-work-graph/SKILL.md")
    assert "the lead is the only agent that changes the work graph" in graph
    assert "only the lead changes the work graph" in _text(CONVENTION)


def test_slice_is_not_a_noun_for_a_work_item():
    """"Work item" is the term; "vertical slice" stays the name of to-issues' technique."""
    for skill in SKILLS.rglob("*.md"):
        if "review-architecture" in skill.parts:
            continue  # "slice" there is a scale of module, not a work item
        text = re.sub(r"vertical[\s-]+slices?", "", _text(skill), flags=re.IGNORECASE)
        assert not re.search(r"\bslices?\b", text, re.IGNORECASE), skill


def test_review_gate_requires_an_independent_reviewer():
    """A lead reviewing its own changes is the author grading itself; the gate must name a
    reviewer that authored none of them, and block rather than skip when none exists."""
    gate = _text(SKILLS / "review-gate/SKILL.md")
    assert "authored none of the reviewed changes" in gate
    assert "the gate is blocked, not skipped" in gate


def test_iterate_design_runs_executions_through_execute_workflow():
    loop = _text(SKILLS / "iterate-design/SKILL.md")
    assert "through `execute-workflow`" in loop
    assert "the only agent that edits the active design doc" in loop
