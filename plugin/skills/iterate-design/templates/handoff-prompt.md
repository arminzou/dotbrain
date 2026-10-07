Use Goal mode when available. Otherwise, remain in this task and make bounded repeated turns.

Active design doc:
<path>

Linked bead:
<id or none>

Preflight contract (confirmed by explicit `GO`):
- Scope: <one work bead | every implementation bead under this design/epic>
- Dedicated branch and base: <branch / base>
- Writing-worker cap: <2 unless stated>
- Human-gated items in scope: <none | ids; with any, the handoff can only end BLOCKED>
- Verification: <narrow checkpoint check>, in-loop Success Criteria gate (fast tier), full suite at
  the review surface, final whole-branch code review for multi-item branches, default non-blocking
  simplify pass, readiness: <only if named in this contract>
- Delivery: draft at first push, pushes after integrated checks, one mention per blocked stop,
  ready at FINAL with human review requested; provider/auth: <available>; agent identity:
  <distinct from human>; base ruleset: <reviewed PR required, stale approvals dismissed>

Treat the active design doc as the controlling instruction document for this loop.

Before entering the loop, and after context recovery:

- Run `bd prime` for the Beads protocol; dotbrain injects none. Skip it only when the operator's own
  Beads hook already supplied it.
- If the linked bead names the current work, inspect `bd ready --json --quiet`,
  `bd human list --json --quiet`, and `bd show <id> --json --quiet`. Claim a ready work bead
  yourself only when you will work it as a team of one; otherwise `run-execution` claims it under
  each worker's own actor. Never claim an epic merely because it is linked.
- Do not start unless the preflight contract is complete and the human has said `GO`.
  Confirm provider/auth, agent identity distinct from the human reviewer, and the base-branch
  ruleset requiring a reviewed PR and dismissing stale approvals. Use that agent identity for
  every host action; never fall back to the human's credentials.

Handoff delivery:
- After the first item integrates and passes its integrated check, push the dedicated branch and
  open a draft PR at the first push. Record the URL privately and attach it where supported.
  Do not create a placeholder commit to open it at preflight.
- Push after each integrated item that passes its integrated check. Post no progress comments
  and make no body updates between the first push and FINAL; commits show progress.
- When the whole handoff ends BLOCKED, leave the PR draft and post one PR comment that @-mentions
  the human with an audience-safe reason. Each blocked stop gets one mention. Check existing
  comments and the delivery record before posting or retrying, keyed to this stop's revision and
  reason: a retry of the same stop never posts twice, and a new stop after a resume gets its own
  mention. Record the comment URL with that key. Private item IDs and attempt details stay in the
  tracker and session. Before the first push, use the runtime's own notification where available,
  otherwise the session report. Report notification failures in the session and remain BLOCKED.
- At FINAL, write the Verification section and simplify count or skip note, mark the existing
  draft PR ready, and request the human's review. Never mark it ready with a blocked scoped item.

Objective:
Complete the next bounded execution that advances this design.

Stopping condition:
Stop successfully only when every scoped item is closed and none is blocked, the scoped work
satisfies the design doc's Success Criteria, relevant checks pass, design-relevant discoveries
are reflected into the active design doc, final review has no blocking findings (required code
review APPROVE, named readiness review READY), and the agreed ready-for-review PR exists with
the human's review requested. Simplify findings or a missing simplify engine never block FINAL.

Stop scopes:
- The whole handoff ends BLOCKED for wrong or unmeetable criteria; unresolvable scope, safety,
  or design ambiguity; two cycles without a code change, new verification evidence, or resolved
  scope; an action outside GO; a missing required capability or a PR that cannot be opened;
  a failure that compromises shared state; or cancellation.
- An item blocks after 3 consecutive failed checks on one checkpoint, 3 consecutive item-review
  CHANGES, or a human gate. Only that item and its dependents stop; independent items continue.
  End the handoff BLOCKED once no unblocked work remains. Report every blocked item with its
  attempt trail and a recommended decision, including waiting dependents. Never mark a PR ready
  while any scoped item is blocked. Keep blocked items in the fixed scope; do not drop them to
  claim success.

Loop protocol (every iteration, not just the first):
1. Reread the active design doc fresh, plus AGENTS.md, CONTEXT.md if present, and the linked bead
   if present. Do not rely on an earlier iteration's memory of the design doc.
2. Select the next bounded execution: one ready work item or a finite batch from the work graph,
   within the approved scope.
3. If the path is unclear, use a read-only explorer first.
4. Run that execution through `run-execution` as its lead. Only the lead changes the work graph,
   the execution record, and the active design doc.
5. The agent that made a change runs its checkpoint's narrow check; never spawn an agent just to
   check a checkpoint. Run the once-only in-loop Success Criteria gate before final review.
6. If an item check fails, make the smallest targeted fix within its retry limit. After 3
   consecutive failed checks on one checkpoint or 3 consecutive item-review CHANGES, block
   that item and its dependents and continue independent work. Do not retry the blocked item
   without human authorization. A failure compromising shared state ends the whole handoff.
7. If design-relevant learning appears, update Known Unknowns, Implementation Notes, Deviations, or
   Human Decisions Needed in the active design doc.
   Keep linked Beads current separately: file discovered execution work with `discovered-from` and,
   before a handoff or BLOCKED, update the bead notes with what is done, next, and any open question.
8. After the integrated in-loop gate passes, run final whole-branch code review for a branch
   carrying more than one work item, against its base, by a fresh reviewer that ran none of
   the item reviews. Check interactions, consistency, and conformance to the active design doc;
   do not reopen approved item findings. Record the design-level review bead. A single-item
   branch skips it: its item review is the final code review. Run readiness only when the
   handoff contract names it, in addition to code review. Run simplify beside final code
   review, also for single-item branches; record its findings in a separate review bead under
   the epic. Never apply simplify findings in-loop; they never block the PR or FINAL. If its
   engine is unavailable, skip with a note. Add one PR-body line: "N non-blocking
   simplification suggestions", with no finding details, or a one-line skip note. Review
   supplements the verifier, never replaces it.
9. Stop if blocked by missing design guidance, unsafe scope growth, or verifier ambiguity.
10. Before calling FINAL: complete Handoff delivery above, marking the existing draft ready
    and requesting the human's review. Record its URL and verification on the design-level code
    review bead, add `human`, and leave that bead open; for a single-item branch, record them on
    its work item instead. Never merge,
    deploy, publish, change dependencies, or alter human-owned criteria.

Progress log:
- Current checkpoint
- What changed
- What was verified
- What remains
- Bead state: discovered work and handoff notes, if applicable
- Whether blocked

Rules:
- Do not expand scope beyond the design doc.
- Do not turn the design doc into a task checklist.
- Keep work-graph and execution-record state in beads.
- Keep design learning in the active design doc.
- Do not call FINAL without `verifier` evidence from the in-loop gate.
- Never edit Success Criteria or bead acceptance criteria; if they are wrong or
  unmeetable, report BLOCKED instead.
- Never retry an item past 3 consecutive failed checks on the same checkpoint; block the item
  and continue independent work. A failure compromising shared state ends the whole handoff.
- Stop BLOCKED after two cycles with no code change, verification evidence, or resolved scope.
- `GO` authorizes only the agreed Handoff delivery sequence; human review, merge,
  and every other outward action stay human-owned.
