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
| `simplify` | The same target: what can be deleted, collapsed, or replaced with a native capability? | An independent reviewer using the bundled [simplification procedure](references/simplify.md). This is not a correctness review. |
| `readiness` | A subsystem before a milestone: is it sound enough to build the next thing on? | [Readiness procedure](references/readiness.md), always multi-pass. |

The requester supplies the mode, target/range, and the outcome that the review gates. Do not widen a
code review into readiness review, or report simplification findings as defects.

A review is judgment and runs in an independent reviewer agent: one that authored none of the
reviewed changes. It may belong to the same agent team and use the same model. The lead arranges
the review but cannot be the independent gate for changes it authored; when no such agent is
available for required code or readiness review, the gate is blocked, not skipped. The `reviewer`
produces findings; the `verifier` runs the mechanical gate and returns the evidence the record
cites. The reviewer supplements the gate, never replaces it. Simplify uses the bundled procedure.
If no independent reviewer is available, skip that optional pass with a note; it does not block
delivery.

## Final branch review

Before it is offered for merge in either workflow, a branch carrying more than one work item requires a final `code` review
of the whole branch diff against its agreed base at the exact final head. Reuse the final
integration review only when its report explicitly covers that entire range, all scoped items,
interactions, consistency, and conformance to the active design doc. The reviewer must have authored
none of the reviewed changes, but need not be fresh. Approval of only the latest group is not
whole-branch coverage. Missing or stale coverage requires a whole-branch review; changed patches
or integration context affecting coverage require refreshed evidence. Record the design-level
review bead and link any reused report with reviewer provenance and exact revision references.
A single-item branch uses its item/integration review as final code review only when it covers
the whole final diff; otherwise arrange a whole-branch review. Record the PR URL and verification
on that work item, since no design-level code review bead exists. Mechanical checks and the final
human review and merge gate remain required; review reuse removes no human gate.
Run `readiness` only when the handoff contract names it; it does not replace code review.

After the integrated gate passes, the handoff workflow also runs `simplify` beside the final
code review, including when a single-item branch reuses its complete integration review. The HITL workflow
runs simplify only when requested. Its findings go to a separate review bead under the epic
when one exists, never the code-review bead. It never blocks the PR or `FINAL`; never apply
its findings in-loop. When no independent simplify reviewer is available, skip with a note.
The PR body carries one line: "N non-blocking simplification suggestions", with no finding
details. If skipped, use a one-line skip note instead of claiming that the pass found nothing.

## Run the gate

1. Fix the review boundary before reading: target, base/range, oracle, selected mode, and whether a
   human decision follows. Read the target's relevant context and decisions. For readiness, read
   [the procedure](references/readiness.md) before pass 1. For simplify, read the bundled
   [simplification procedure](references/simplify.md) before reviewing.
2. Keep the reviewed tree read-only. The reviewer returns a complete report to the lead without
   tracker writes. The lead records findings and provenance on the review bead; item/integration
   reports go to member execution records through `run-execution`. Include affected consumers and
   interactions, including unchanged files: change-caused regressions can block wherever their
   symptom appears; unrelated existing defects remain discovered work. Gather executed or traced
   evidence (`verifier` for the
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
