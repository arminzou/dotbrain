Use Goal mode when available. Otherwise, remain in this task and make bounded repeated turns.

Active design doc:
<path>

Linked bead:
<id or none>

Preflight contract (record the human's approval; reuse without repeat `GO` while applicable):
- Scope: <one work bead | every implementation bead under this design/epic>
- Dedicated branch and base: <branch / base>
- Limits: <finite whole-loop budget/turn limit, retry caps, consumed and remaining allowance>
- Acceptance/UAT: <agreed criteria, journeys, environment and required evidence>
- Writing-worker cap: <cap under run-execution's parallel reference>
- Human-gated items in scope: <none | ids; with any, the handoff can only end BLOCKED>
- Verification: <checkpoint check>, in-loop Success Criteria gate (fast tier), full suite
  at the review surface; final reviews under review-gate; readiness: <if named>
- Delivery: draft at first push, pushes after accepted integration groups, one mention per blocked stop,
  ready at FINAL with human review requested; provider/auth: <available>; agent identity:
  <distinct from human>; base ruleset: <reviewed PR required, stale approvals dismissed>

Treat the active design doc as the controlling instruction document for this loop.

Before entering the loop, and after context recovery:

- Run `bd prime` for the Beads protocol; dotbrain injects none. Skip it only when the operator's own
  Beads hook already supplied it.
- If the linked bead names the current work, inspect `bd ready --json --quiet`,
  `bd human list --json --quiet`, and `bd show <id> --json --quiet`.
  Apply manage-work-graph's claim and actor rules.
- Validate complete approved authority still applies: scope, branch/base, criteria, checks/UAT,
  review expectations, provider/auth and PR authority, finite limits, and narrower operator overrides.
  Reuse a complete applicable contract without repeat GO. An execution request does not silently
  authorize an unapproved contract. Ask only for missing or changed authority with evidence and
  a recommendation; stop affected work until resolved.
  Confirm provider/auth, agent identity distinct from the human reviewer, and the base-branch
  ruleset requiring a reviewed PR and dismissing stale approvals. Use that agent identity for
  every host action; never fall back to the human's credentials.
- Check actual credentials and provider permissions at execution entry without exposing secrets
  or inferring authorization from availability. On resume retain original workers, claims,
  worktrees, budgets, per-item attempts, review history and hard stops. Resume never resets an
  exhausted limit or grants new authority.

Handoff delivery:
- After the first item passes integration review, combined checks, and acceptance, push the dedicated branch and
  open a draft PR at the first push. Record the URL privately and attach it where supported.
  Do not create a placeholder commit to open it at preflight.
- Push after each accepted integration group; hold failed or uncovered contributions. Push only
  the accepted delivery branch after candidate promotion; held group branches stay local. Post no progress comments
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
satisfies the design doc's Success Criteria and agreed acceptance/UAT, relevant checks including
the full suite pass at the exact integrated revision, design-relevant discoveries
are reflected into the active design doc, final review has no blocking findings (required code
review APPROVE, named readiness review READY), and the agreed ready-for-review PR exists with
the human's review requested. Review requirements follow review-gate.

Stop scopes:
- The whole handoff ends BLOCKED for an exhausted whole-loop budget; wrong or unmeetable criteria; unresolvable scope, safety,
  or design ambiguity; two cycles without a code change, new verification evidence, or resolved
  scope; an action outside the approved contract; a missing required capability or a PR that cannot be opened;
  a failure that compromises shared state; or cancellation.
- Item retry exhaustion follows run-execution. Hold affected groups and dependents;
  continue only proven independent work under its containment rules. End BLOCKED when
  no unblocked work remains. Preserve scope and report attempts and recommended decisions.
  Never mark a PR ready with a blocked scoped item.

Goal-shortfall repairs:
Admit a goal-shortfall repair into the running loop. The lead files its fix as a work
item under the epic, records why it is needed to meet the approved
goal, and adds it to the running loop's fixed set. Meeting an approved goal adds no new
scope. The fix shares the existing finite whole-loop budget and limits; admission grants
no extra attempts. Exhausting that budget with the fix open ends BLOCKED, never FINAL.
A fix needing a new design, scope, authority, or criteria decision still stops affected
work and asks the human under the convention's decision rules. Other discoveries keep
their existing treatment.

Loop protocol (every iteration, not just the first):
1. Reread the active design doc fresh, plus AGENTS.md, CONTEXT.md if present, and the linked bead
   if present. Do not rely on an earlier iteration's memory of the design doc.
2. Select the next bounded execution: one ready work item or a fixed finite item set from the work
   graph within the approved scope. The set may include waiting dependents; dispatch only from
   the actual ready frontier after prerequisite acceptance and closure, with human gates resolved
   and capacity available. Refill eligible slots as prerequisites close while independent siblings
   continue. Never add items silently to an execution already under way.
3. If the path is unclear, use a read-only explorer first.
4. Run that execution through `run-execution` as its lead. Apply manage-work-graph's
   writer permissions to the graph, execution metadata, and active design.
5. Apply run-execution's checkpoint role routing. Run the once-only in-loop Success
   Criteria gate before final review.
6. Apply run-execution's bounded repair, retry, review and acceptance rules.
   Use its parallel reference for containment before continuing independent work.
   Apply the stop scopes above; do not retry blocked work without human authorization.
7. If design-relevant learning appears, update Known Unknowns, Implementation Notes, Deviations, or
   Human Decisions Needed in the active design doc.
   Keep linked Beads current separately: file discovered execution work with `discovered-from` and,
   before a handoff or BLOCKED, update the bead notes with what is done, next, and any open question.
   REFLECT does not invoke run-retro or add another reflection report.
8. After the integrated in-loop gate passes, apply review-gate's final whole-branch
   review rules, including reuse, named readiness review, simplify, and the PR summary.
   Admit any goal-shortfall repair through the rule above before deciding the loop outcome.
9. Stop if blocked by missing design guidance, unsafe scope growth, or verifier ambiguity.
10. Before calling FINAL: complete Handoff delivery above. Record the PR URL and
    verification on the final record selected by review-gate; apply its closing rules.
    Follow the convention's human gates and manage-work-graph's closure boundary.
    Do not poll for merge or add retrospective checkpoints.

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
- Apply the convention's human-owned criteria and hard-stop invariants.
- Stop BLOCKED after two cycles with no code change, verification evidence, or resolved scope.
- The approved contract authorizes only the agreed Handoff delivery sequence; human PR approval, merge,
  and every other outward action stay human-owned.
