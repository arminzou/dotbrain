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

import pytest
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
    owner = _text(SKILLS / "run-execution/SKILL.md")
    assert "the lead is the only agent that edits the active design doc" in owner
    assert "A writing worker writes only its own claim" in owner
    graph = _text(SKILLS / "manage-work-graph/SKILL.md")
    assert "the lead is the only agent that changes the work graph" in graph
    assert "only the lead changes the work graph" in _text(CONVENTION)


def test_sync_replaces_the_retired_term_hydrate():
    """"Sync" is the word for bringing tracker state or packaged assets into place; "hydrate" is retired."""
    roots = (Path("src/dotbrain"), SKILLS, Path("docs"))
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or ".vitepress" in path.parts or path.suffix not in {".py", ".md", ".toml", ".yaml"}:
                continue
            assert not re.search(r"hydrat", path.read_text(encoding="utf-8"), re.IGNORECASE), path


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


def test_iterate_design_runs_executions_through_run_execution():
    loop = _text(SKILLS / "iterate-design/SKILL.md")
    assert "through `run-execution`" in loop
    assert "the only agent that edits the active design doc" in loop


@pytest.mark.parametrize("rule", [
    "Every work item's behavior change gets an independent `code` item review",
    "Behavior includes code, tests, build or CI config, and instructions agents execute",
    "Changes confined to human-facing prose docs, comments, formatting, or generated output are exempt",
    "## Review skipped: <reason>",
    "prompt includes the diffstat, the behavior changed, and the lead's recommendation",
    "Keep the item open until the human answers",
    "## Review skipped: declined by human — <reason>",
    "Standing answers hold until the human changes them",
    "The handoff workflow never asks",
    "The lead never reviews changes it authored",
    "An item review never gets a review bead",
    "Return `CHANGES` only for an unmet acceptance criterion or a `blocker` or `high` finding in the item's own diff",
    "Return `APPROVE` with `medium` or `low` findings and findings outside the diff",
    "The same reviewer re-reviews its earlier findings and the fix diff",
    "Three consecutive `CHANGES` block the item",
    "A conflict rebase does not count toward the `CHANGES` cap",
    "Any behavior diff after the last `APPROVE`",
    "No item closes with an unreviewed behavior change",
])
def test_item_review_preserves_its_guards(rule):
    """A missing guard permits unreviewed closure or unbounded review-fix rounds."""
    assert rule in _text(SKILLS / "run-execution/SKILL.md")


def test_item_review_order_and_record():
    owner = _text(SKILLS / "run-execution/SKILL.md")
    assert "Parallel order: work and passing worker checks, candidate, item review and fix loop, integrate, integrated check, close as `verified`, clean up, release dependents" in owner
    assert "Sequential order: work, checks, item review and fix loop, close" in owner
    assert "Each `CHANGES` is a failed check on the `item-review` checkpoint in `dotbrain_attempts`" in owner
    record = _text(SKILLS / "run-execution/references/execution-record.md")
    for rule in (
        "## Review <n>: APPROVE | CHANGES @ <revision>",
        "## Review skipped: <reason>",
        "--actor <reviewer-actor>",
        "consecutive `CHANGES` verdicts with limit 3; `APPROVE` resets the streak",
        "diff fingerprint",
    ):
        assert rule in record


def test_worker_keeps_claim_through_fix_rounds_and_closure():
    owner = _text(SKILLS / "run-execution/SKILL.md")
    for rule in (
        "A writing worker keeps its claim until the item closes",
        "under its own actor while the worker remains assignee",
        "`SendMessage` to the stopped worker's agent ID",
        "The lead sets `dotbrain_phase` to `working`",
        "The resumed worker does not touch its claim",
        "a delegated sequential worker is resumed like a parallel worker",
        "Move a claim only for a replacement after the previous worker is confirmed stopped",
    ):
        assert rule in owner
    record = _text(SKILLS / "run-execution/references/execution-record.md")
    assert "@ <base> (fix round <n>)" in record
    assert "a fix round changes phase and history, not the claim" in record
    for path in SKILLS.rglob("*.md"):
        text = _text(path).lower()
        assert not re.search(
            r"handback|hand(?:ed|s|ing)? (?:its |the )?claim back|claim handed back",
            text,
        ), path


def test_review_modes_keep_distinct_verdicts_and_metadata():
    record = _text(SKILLS / "manage-work-graph/references/review-beads.md")
    for row in (
        "| `code` | `APPROVE` or `CHANGES` | `approve`, `changes` |",
        "| `readiness` | `READY` or `NOT-READY` | `ready`, `not-ready` |",
        "| `simplify` | Findings only, never blocking | none |",
    ):
        assert row in record
    assert "A simplify pass records findings without a `## Verdict:` comment or `verdict` metadata" in record
    assert "Verdict metadata alone does not distinguish the shapes" in record
    assert "A bare `GO` means only the human's handoff authorization" in _text(SKILLS / "review-gate/SKILL.md")
    for path in (SKILLS / "review-gate/SKILL.md", SKILLS / "review-gate/references/readiness.md",
                 SKILLS / "manage-work-graph/references/review-beads.md"):
        assert not re.search(r"NO-GO|no-go|request changes|verdict=go", _text(path)), path


def test_review_closure_requires_a_human_decision():
    record = _text(SKILLS / "manage-work-graph/references/review-beads.md")
    for guard in (
        "never closes it on its own judgment",
        "the lead may close a `code` review bead after observing the human's merge of the PR recorded on that bead",
        "Cite that PR and its merge commit in the closeout",
        "A PR closed unmerged leaves the bead open",
        "Approval alone is not merge evidence",
        "A `readiness` bead has no merge-based exception",
        "A `simplify` bead does not close on merge",
        "until every finding is applied, filed as its own item, or declined",
    ):
        assert guard in record
    gate = _text(SKILLS / "review-gate/SKILL.md")
    assert "disposition does not replace the human close" in gate
    graph = _text(SKILLS / "manage-work-graph/SKILL.md")
    assert "including the observed human merge exception for code review" in graph
