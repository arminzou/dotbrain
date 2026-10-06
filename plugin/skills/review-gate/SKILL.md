---
name: review-gate
description: Run a durable engineering review gate with focused code, simplification, or readiness review.
---

# Review Gate

Turn a review into a durable gate without claiming that all review methods answer the same question.
The review bead is the lifecycle record; read [the shared contract](../manage-work-graph/references/review-beads.md)
before creating or resuming one.

## Choose the mode

| Mode | Target and question | Engine |
| --- | --- | --- |
| `code` | A diff, commit, branch, PR, or working tree: is it correct and in scope? | A read-only `reviewer` agent that authored none of the changes; native `/review` when available. |
| `simplify` | The same target: what can be deleted, collapsed, or replaced with a native capability? | `ponytail-review`. This is not a correctness review. |
| `readiness` | A subsystem before a milestone: is it sound enough to build the next thing on? | [Readiness procedure](references/readiness.md), always multi-pass. |

The requester supplies the mode, target/range, and the outcome that the review gates. Do not widen a
code review into readiness review, or report simplification findings as defects.

A review is judgment and runs in an independent reviewer agent: one that authored none of the
reviewed changes. It may belong to the same agent team and use the same model. The lead arranges
the review but cannot be the independent gate for changes it authored; when no such agent is
available for required code or readiness review, the gate is blocked, not skipped. The `reviewer`
produces findings; the `verifier` runs the mechanical gate and returns the evidence the record
cites. The reviewer supplements the gate, never replaces it. An unavailable `simplify` engine
is skipped with a note; that optional pass does not block delivery.

## Final branch review

Before it is offered for merge in either workflow, a branch carrying more than one work item requires a final `code` review
of the whole branch diff against its base. Use a fresh reviewer that ran none of the item
reviews. It checks interactions between items, consistency, and conformance to the active
design doc; it does not reopen approved item findings. Record the design-level review bead.
A single-item branch skips this final code review: its item review covered the diff and is the
final code review. Record the PR URL and verification on that work item, since no design-level
code review bead exists.
Run `readiness` only when the handoff contract names it; it does not replace code review.

After the integrated gate passes, the handoff workflow also runs `simplify` beside the final
code review, including when a single-item branch skips final code review. The HITL workflow
runs simplify only when requested. Its findings go to a separate review bead under the epic
when one exists, never the code-review bead. It never blocks the PR or `FINAL`; never apply
its findings in-loop. When the simplify engine is unavailable, skip with a note.
The PR body carries one line: "N non-blocking simplification suggestions", with no finding
details. If skipped, use a one-line skip note instead of claiming that the pass found nothing.

## Run the gate

1. Fix the review boundary before reading: target, base/range, oracle, selected mode, and whether a
   human decision follows. Read the target's relevant context and decisions. For readiness, read
   [the procedure](references/readiness.md) before pass 1.
2. Keep the reviewed tree read-only. The review bead is the only allowed mutation; findings become
   execution work only at closeout. Gather executed or traced evidence (`verifier` for the
   mechanical gate), not unlocated impressions.
3. Create or resume the review bead in the shape required by the shared contract. A readiness gate
   creates its multi-pass bead before pass 1; an epic-level gate is parented to its epic and depends
   on every scoped implementation bead. Record the selected mode in the description and every pass in
   the append-only record.
4. Record the mode's result: `code` returns `APPROVE | CHANGES`, `readiness` returns
   `READY | NOT-READY`, and `simplify` reports findings only, with no verdict. Write matching
   verdict metadata as the shared contract specifies. A bare `GO` means only the human's
   handoff authorization. No review result authorizes merge or release. Record findings,
   evidence, and any uncovered area.

A review bead is human-gated by definition: a clean agent result does not close it. Once every
finding has a disposition, record the closeout, append the PR URL and verification summary when one
exists, add the `human` label, and leave the bead open with a one-line close recommendation. It
stays open until the human closes it or `close-design` discharges it with the design's terminal
transition. The lead may also close a `code` review bead after observing the human's merge of
the PR recorded on that bead, citing the PR and merge commit. A PR closed unmerged leaves the
bead open. A `simplify` bead does not close on merge and stays open until every finding is
applied, filed as its own item, or declined; disposition does not replace the human close.
See the shared contract's closing rules.

## Completion

Report the mode, exact target, verdict when applicable, evidence, findings or clean result, and the review bead id.
Make the boundary explicit: `code` covers correctness/scope, `simplify` covers unnecessary
complexity, and `readiness` covers a subsystem against its written oracle.
