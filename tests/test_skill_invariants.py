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
    assert "a draft PR at the first push" in convention
    assert "one mention of the human for each blocked stop" in convention
    assert "authorizes only the agreed push of its dedicated branch, a ready-for-review PR" not in convention
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
            if not path.is_file() or {".vitepress", "node_modules"}.intersection(path.parts) or path.suffix not in {".py", ".md", ".toml", ".yaml"}:
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
        "consecutive `CHANGES` verdicts with limit 3; only `APPROVE` resets it",
        "diff fingerprint",
    ):
        assert rule in record


def test_item_review_streak_survives_worker_checks():
    """One shared checkpoint slot let a worker's passing check in a fix round overwrite the
    item-review count, so the three-CHANGES cap never fired and the loop had no hard stop."""
    owner = _text(SKILLS / "run-execution/SKILL.md")
    assert "keeps a separate streak per checkpoint" in owner
    assert "a worker's passing checks during a fix round do not reset it" in owner
    record = _text(SKILLS / "run-execution/references/execution-record.md")
    assert "for each checkpoint, keyed by checkpoint reference" in record
    assert "A passing check ends only its own checkpoint's streak" in record
    assert "every checkpoint's entry, not only the one that changed" in record
    assert '"checkpoint":' not in record


def test_only_the_lead_moves_a_claim():
    record = _text(SKILLS / "run-execution/references/execution-record.md")
    assert "a writing worker writes only its own claim and its `Attempt` comments" in record
    assert "the lead's comment headers, including `Claim moved`" in record


def test_worker_keeps_claim_through_fix_rounds_and_closure():
    owner = _text(SKILLS / "run-execution/SKILL.md")
    for rule in (
        "A writing worker keeps its claim until the item closes",
        # Beads 1.3 lets only the assignee close, so the lead closes as the worker and names itself.
        "closes under the worker's actor and names itself in the reason, which keeps the worker as assignee",
        "Never pass `--force` to `bd close`, which also overrides gates, and never run `bd reclaim`",
        "`bd update <id> --assignee <new-actor> --force`",
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


def test_dispatched_is_recorded_while_the_worker_runs():
    """A foreground launch returned only after the worker finished, so Dispatched landed after its
    work and a lead that stopped mid-run left no trace of where the worker was."""
    owner = _text(SKILLS / "run-execution/SKILL.md")
    for rule in (
        "Launch each delegated writing worker in the background",
        "As soon as the runtime identifies the worker, record `## Dispatched`",
        "with the runtime's agent or session ID in the comment body, before waiting on the worker",
        "If a runtime can launch only in the foreground, record `Dispatched` before launching",
    ):
        assert rule in owner, rule
    record = _text(SKILLS / "run-execution/references/execution-record.md")
    assert "Record `Dispatched` as soon as the runtime identifies the worker, before waiting on it" in record


def test_execution_routes_runtime_mechanisms_without_duplicating_shared_rules():
    owner = _text(SKILLS / "run-execution/SKILL.md")
    assert "Before worker preparation or dispatch, read the applicable runtime reference" in owner
    assert "Read it again before runtime-specific fix rounds, cancellation, or recovery" in owner
    for filename in ("claude-code.md", "codex.md"):
        assert f"references/{filename}" in owner
        text = _text(SKILLS / "run-execution/references" / filename)
        assert "[Run Execution](../SKILL.md)" in text
        assert "dotbrain_attempts" not in text
    claude = _text(SKILLS / "run-execution/references/claude-code.md")
    assert "set worktree isolation on the `Agent` call" in claude
    assert "its definition never sets isolation" in claude
    assert "`.claude/worktrees/agent-<agent-id>`" in claude
    assert "`SendMessage` to that original ID" in claude
    # The isolation guard covers only Bash; PowerShell is the only shell on Windows without Git Bash.
    assert "run Git through the Bash tool where it exists, since only Bash is guarded" in claude
    assert "run Git only inside their own worktree" in claude
    codex = _text(SKILLS / "run-execution/references/codex.md")
    for mechanism in (
        "git worktree add --detach <worktree> <base>",
        "dotbrain wire --repo <worktree>",
        "--sandbox danger-full-access --json",
        "session ID from `thread.started`",
        "codex exec resume <session-id>",
        "a shell-wrapper exit is not proof",
        # A nested writer escaped the worker's tree and kept writing after the worker was stopped.
        "Move the claim only after that.",
        "wait for the human decision",
        "actually spawning that role",
        # Workers told only to "use the project's skills" denied having a catalog and stopped.
        "name it in the assignment by its exact name (`$<skill-name>`)",
        "add the session ID to the worker's `work` entry in `dotbrain_artifacts`",
    ):
        assert mechanism in codex
    # Shared rules stay in SKILL.md; the reference points to them instead of restating them.
    for restated in ("Exit zero alone is not acceptance", "retries beyond the existing checkpoint limits",
                     "must not have authored the change"):
        assert restated not in codex
    assert "For tracker access, an unwired linked worktree needs no preparation" in owner


def test_comment_files_are_written_verbatim_on_every_os():
    """printf turned the backslashes of a Windows worktree path into control characters."""
    record = _text(SKILLS / "run-execution/references/execution-record.md")
    for rule in (
        "so its text arrives verbatim on Windows, macOS, and Linux",
        "Prefer the runtime's own file-writing tool",
        "quoted heredoc in bash or zsh, including Git Bash on Windows (`cat > <file> <<'EOF'`)",
        "single-quoted here-string in PowerShell 7",
        "Never build comment text with `printf` or `echo -e`",
    ):
        assert rule in record, rule


def test_assignment_names_the_repository_commit_convention():
    """Workers follow the repository's own commit rules; shipped skills never depend on a user's
    personal commit skill."""
    owner = _text(SKILLS / "run-execution/SKILL.md")
    assert ("the commit convention to follow: the repository's written commit rules, or else the "
            "style of its recent history") in owner
    for path in list(SKILLS.rglob("*.md")) + list(Path("src/dotbrain/resources/agents").rglob("*.*")):
        assert "conventional-commits" not in path.read_text(encoding="utf-8"), path


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


@pytest.mark.parametrize("path", [
    "review-gate/SKILL.md",
    "iterate-design/SKILL.md",
    "iterate-design/templates/handoff-prompt.md",
])
def test_final_review_keeps_branch_boundary_and_optional_passes(path):
    text = _text(SKILLS / path).replace("`", "")
    for rule in (
        "more than one work item",
        "against its base",
        "fresh reviewer that ran none of the item reviews",
        "do not reopen approved item findings" if path != "review-gate/SKILL.md"
        else "does not reopen approved item findings",
        "single-item branch skips",
        "readiness only when the handoff contract names it",
        "separate review bead under the epic",
        "non-blocking simplification suggestions",
        "no finding details",
        "skip with a note",
    ):
        assert rule.lower() in text.lower()
    assert "never apply" in text.lower() and "findings in-loop" in text
    assert re.search(r"never blocks? the PR or (?:`)?FINAL", text, re.I)


@pytest.mark.parametrize("path, record", [
    ("iterate-design/SKILL.md", "A single-item branch has no such bead: record them on its work item instead"),
    ("iterate-design/templates/handoff-prompt.md", "for a single-item branch, record them on its work item instead"),
    ("review-gate/SKILL.md", "Record the PR URL and verification on that work item"),
])
def test_single_item_branch_has_a_final_review_and_a_pr_record(path, record):
    """Without these, FINAL demands final-review evidence a single-item branch never produces,
    and the PR URL has no record to land on."""
    text = _text(SKILLS / path)
    assert "is the final code review" in text
    assert record in text


def test_final_review_does_not_turn_simplify_into_a_gate():
    gate = _text(SKILLS / "review-gate/SKILL.md")
    assert "The HITL workflow runs simplify only when requested" in gate
    assert "including when a single-item branch skips final code review" in gate
    loop = _text(SKILLS / "iterate-design/SKILL.md")
    assert "required code review is `APPROVE`" in loop
    assert "any named readiness review is `READY`" in loop
    assert "A skipped or findings-bearing simplify pass does not prevent `FINAL`" in loop


WHOLE_HANDOFF_STOPS = (
    "wrong or unmeetable criteria",
    "unresolvable scope, safety, or design ambiguity",
    "two cycles without a code change, new verification evidence, or resolved scope",
    "an action outside GO",
    "a missing required capability or a PR that cannot be opened",
    "a failure that compromises shared state",
    "cancellation",
)
HITL_PAUSE = "the hitl workflow instead pauses new dispatch and integration and asks the human"


@pytest.mark.parametrize("path", [
    "run-execution/SKILL.md",
    "iterate-design/SKILL.md",
    "iterate-design/templates/handoff-prompt.md",
])
def test_item_blocks_leave_independent_work_running(path):
    """An item failure must not idle siblings or disappear from the delivery scope."""
    text = _text(SKILLS / path).replace("`", "").lower()
    for rule in (
        "3 consecutive failed checks on one checkpoint",
        "3 consecutive item-review changes",
        "or a human gate",
        "only that item and its dependents stop; independent items continue",
        "attempt trail and a recommended decision",
        "including waiting dependents",
        "keep blocked items in the fixed scope; do not drop them to claim success",
    ):
        assert rule in text, (path, rule)


@pytest.mark.parametrize("path", [
    "iterate-design/SKILL.md",
    "iterate-design/templates/handoff-prompt.md",
])
def test_handoff_owns_whole_handoff_stops_and_the_delivery_gate(path):
    text = _text(SKILLS / path).replace("`", "")
    for rule in WHOLE_HANDOFF_STOPS + (
        "BLOCKED once no unblocked work remains",
        "Never mark a PR ready while any scoped item is blocked",
    ):
        assert rule in text, (path, rule)


def test_run_execution_leaves_whole_handoff_stops_to_iterate_design():
    """A third copy of the outer loop's limits drifts, and run-execution has no loop cycles."""
    owner = _text(SKILLS / "run-execution/SKILL.md").replace("`", "")
    assert "The conditions that end the whole handoff, and when a PR may be marked ready, belong to iterate-design" in owner
    for rule in WHOLE_HANDOFF_STOPS[2:4]:
        assert rule not in owner
    assert HITL_PAUSE in owner.lower()
    assert HITL_PAUSE in _text(SKILLS / "iterate-design/SKILL.md").lower()
    assert "HITL" not in _text(SKILLS / "iterate-design/templates/handoff-prompt.md")


def test_stop_scopes_do_not_swallow_the_loop_protocol():
    loop = (SKILLS / "iterate-design/SKILL.md").read_text(encoding="utf-8")
    protocol = loop.index("## Loop protocol")
    assert protocol < loop.index("1. PLAN:") < loop.index("## Stop scopes")
    assert "### Stop scopes" not in loop


@pytest.mark.parametrize("path", [
    "iterate-design/SKILL.md",
    "iterate-design/templates/handoff-prompt.md",
])
def test_preflight_names_human_gated_items(path):
    """A gated item in scope means the handoff can only end BLOCKED; the human sees it before GO."""
    text = _text(SKILLS / path).replace("`", "")
    assert re.search(r"[Hh]uman[- ]gate[ds]?.*can only end BLOCKED", text), path


def test_branches_and_integration_never_carry_work_item_ids():
    """Branch names and merge messages reach the public repo; a branch named after its item, and a
    merge commit naming that branch, published private tracker IDs."""
    owner = _text(SKILLS / "run-execution/SKILL.md")
    assert "rebase the item branch onto the current target, then fast-forward the target with `git merge --ff-only <item-branch>`; never create a merge commit" in owner
    assert "Name every branch with a short slug only, never a work-item ID" in owner
    assert "never a work-item ID" in _text(SKILLS / "manage-work-graph/SKILL.md")
    assert "(candidate <revision>)" in _text(SKILLS / "run-execution/references/execution-record.md")
    for path in SKILLS.rglob("*.md"):
        assert "<item-id>-<short-slug>" not in _text(path), path
