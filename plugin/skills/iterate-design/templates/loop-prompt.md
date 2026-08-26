Use your native goal/loop mode.

Active design doc:
<path>

Linked bead:
<id or none>

Treat the active design doc as the controlling instruction document for this loop.

Objective:
Implement the smallest coherent checkpoint that advances this design.

Stopping condition:
Stop when the checkpoint satisfies the design doc's Success Criteria, relevant checks
pass, design-relevant discoveries are reflected into the active design doc, and reviewer feedback has
no blocking findings.

Loop protocol (every iteration, not just the first):
1. Reread the active design doc fresh, plus AGENTS.md, CONTEXT.md if present, and the linked bead
   if present. Do not rely on an earlier iteration's memory of the design doc.
2. Pick the next smallest checkpoint.
3. If the path is unclear, use a read-only explorer first.
4. Implement only the checkpoint.
5. Run the verifier named in the design doc.
6. If the verifier fails, make the smallest targeted fix and retry. After 3 consecutive failed
   verify cycles on the same checkpoint, stop and report BLOCKED with the attempt trail.
7. If design-relevant learning appears, update Known Unknowns, Implementation Notes, Deviations, or
   Human Decisions Needed in the active design doc.
8. If implementation and verification pass, use a reviewer/checker before FINAL when available. The
   reviewer supplements the verifier, never replaces it — a review pass without a mechanical
   pass/fail check is two optimists agreeing.
9. Stop if blocked by missing design guidance, unsafe scope growth, or verifier ambiguity.
10. Before calling FINAL: this loop is an automation handoff running on its dedicated branch
    (never `main`). The landing step is opening the review surface — a PR when the project hosts
    them, otherwise the branch diff reviewed directly and merged locally — and that landing path
    stays fixed even if a mid-loop human-in-the-loop moment pulls the human in.

Progress log:
- Current checkpoint
- What changed
- What was verified
- What remains
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
- FINAL is not landing. This automation-handoff loop lands through the review surface — a PR
  when the project hosts them, otherwise a branch diff reviewed directly and merged locally —
  and that landing path stays fixed on the branch even if the human is pulled in mid-loop.
- Never push or open a PR unprompted — opening the review surface is the human's action to take
  or authorize.
