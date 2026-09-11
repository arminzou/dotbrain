Use Goal mode when available. Otherwise, remain in this task and make bounded repeated turns.

Active design doc:
<path>

Linked bead:
<id or none>

Preflight contract (confirmed by explicit `GO`):
- Scope: <one work bead | every implementation bead under this design/epic>
- Dedicated branch and base: <branch / base>
- Verification: <narrow check>, full Success Criteria gate, review mode: <code | simplify | readiness>
- Delivery: draft PR authorized; provider/auth available: <yes>

Treat the active design doc as the controlling instruction document for this loop.

Before entering the loop, and after context recovery:

- Use the hook-injected `bd prime` protocol; run `bd prime` only when it was not injected.
- If the linked bead names the current work, inspect `bd ready --json --quiet`,
  `bd human list --json --quiet`, and `bd show <id> --json --quiet`. Claim an unclaimed, ready
  work bead with `bd update <id> --claim --json --quiet`; do not claim an epic merely because it is linked.
- Do not start unless the preflight contract is complete and the human has said `GO`.

Objective:
Implement the smallest coherent checkpoint that advances this design.

Stopping condition:
Stop when the scoped work satisfies the design doc's Success Criteria, relevant checks pass,
design-relevant discoveries are reflected into the active design doc, final review has no blocking
findings, and the agreed draft PR exists.

Loop protocol (every iteration, not just the first):
1. Reread the active design doc fresh, plus AGENTS.md, CONTEXT.md if present, and the linked bead
   if present. Do not rely on an earlier iteration's memory of the design doc.
2. Pick the next smallest checkpoint.
3. If the path is unclear, use a read-only explorer first.
4. Implement only the checkpoint.
5. Run the smallest relevant verifier for the checkpoint. Run the full Success Criteria gate once,
   before final review.
6. If the verifier fails, make the smallest targeted fix and retry. After 3 consecutive failed
   verify cycles on the same checkpoint, stop and report BLOCKED with the attempt trail.
7. If design-relevant learning appears, update Known Unknowns, Implementation Notes, Deviations, or
   Human Decisions Needed in the active design doc.
   Keep linked Beads current separately: file discovered execution work with `discovered-from` and,
   before a handoff or BLOCKED, update the bead notes with what is done, next, and any open question.
8. After the full gate passes, run the selected `review-gate` mode. It supplements the verifier,
   never replaces it.
9. Stop if blocked by missing design guidance, unsafe scope growth, or verifier ambiguity.
10. Before calling FINAL: push only the dedicated branch and create the authorized draft PR. Record
    its URL and verification on the review bead, add `human`, and leave that bead open. Never merge,
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
- Keep execution state in beads.
- Keep design learning in the active design doc.
- Do not call FINAL without verifier evidence.
- Never edit Success Criteria or bead acceptance criteria; if they are wrong or
  unmeetable, report BLOCKED instead.
- Never iterate past 3 consecutive failed verify cycles on the same checkpoint.
- Stop BLOCKED after two cycles with no code change, verification evidence, or resolved scope.
- `GO` authorizes only the agreed draft PR; human review, merge, and every other outward action stay
  human-owned.
