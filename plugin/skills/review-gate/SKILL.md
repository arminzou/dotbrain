---
name: review-gate
description: Run a durable engineering review gate with focused code, simplification, or readiness review.
---

# Review Gate

Turn a review into a durable gate without claiming that all review methods answer the same question.
The review bead is the lifecycle record; read [the shared contract](../operate-execution/references/review-beads.md)
before creating or resuming one.

## Choose the mode

| Mode | Target and question | Engine |
| --- | --- | --- |
| `code` | A diff, commit, branch, PR, or working tree: is it correct and in scope? | A read-only `reviewer`, run in a separate session; native `/review` when available. |
| `simplify` | The same target: what can be deleted, collapsed, or replaced with a native capability? | `ponytail-review`. This is not a correctness review. |
| `readiness` | A subsystem before a milestone: is it sound enough to build the next thing on? | [Readiness procedure](references/readiness.md), always multi-pass. |

The requester supplies the mode, target/range, and the outcome that the review gates. Do not widen a
code review into readiness review, or report simplification findings as defects.

A review is judgment and runs in its own session, separate from the work it reviews. The `reviewer`
produces findings; the `verifier` runs the mechanical gate and returns the evidence the record
cites. The reviewer supplements the gate, never replaces it.

## Run the gate

1. Fix the review boundary before reading: target, base/range, oracle, selected mode, and whether a
   human decision follows. Read the target's relevant context and decisions. For readiness, read
   [the procedure](references/readiness.md) before pass 1.
2. Keep the reviewed tree read-only. The review bead is the only allowed mutation; findings become
   execution work only at closeout. Gather executed or traced evidence (`verifier` for the
   mechanical gate), not unlocated impressions.
3. Create or resume the review bead in the shape required by the shared contract. A readiness gate
   creates its multi-pass bead before pass 1; an epic-level gate is parented to its epic and depends
   on every scoped implementation bead. Record selected modes in the description and every pass in
   the append-only record.
4. Issue a direct verdict. `GO` means the agent review found no blocking reason to stop; it does not
   merge, release, or erase the human gate. Record findings, evidence, and any uncovered area.

A review bead is human-gated by definition: never close it, however clean the result. Once every
finding has a disposition, record the closeout, append the PR URL and verification summary when one
exists, add the `human` label, and leave the bead open with a one-line close recommendation. It
stays open until the human closes it or `close-design` discharges it with the design's terminal
transition — see the shared contract's closing rules.

## Completion

Report the mode, exact target, verdict, evidence, findings or clean result, and the review bead id.
Make the boundary explicit: `code` covers correctness/scope, `simplify` covers unnecessary
complexity, and `readiness` covers a subsystem against its written oracle.
